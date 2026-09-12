# Milestone 1 Remediation Plan: Consumer Lifecycle Management in `core/messaging.py` & `agents/base.py`

**Author**: Explorer M1-Iteration 2-1  
**Target Milestone**: Milestone 1 Remediation (Iteration 2)  
**Date**: 2026-09-03  
**Status**: Ready for Implementation by Worker / Orchestrator  

---

## 1. Executive Summary

Empirical investigation of the Milestone 1 test failures reported by Challenger M1-2 identified a critical concurrency defect in `core/messaging.py` and `agents/base.py`: **competing zombie consumers caused by unmanaged background worker threads on the Singleton `LocalMessageBroker`**.

### The Problem
1. `LocalMessageBroker` is an in-process, thread-safe Singleton (`__new__` pattern).
2. Every call to `consume(queue_name, callback, block=False)` instantiates a new, unmanaged `ThreadPoolExecutor(max_workers=6)` and starts an infinite worker thread (`threading.Thread(target=_worker, daemon=True)`).
3. The broker provided **no mechanism to unsubscribe callbacks, stop consumer threads, clear consumers for a queue, or reset broker state between tests**.
4. When multiple tests run sequentially in the same Python process (e.g., in `tests/test_stress_dag_orchestration.py` or across the full test suite), each test instantiates new agents (such as `MasterAgent`) and calls `run(block=False)`.
5. Older background worker threads remain alive in the background, continuously polling shared queues (`"master_queue"`). When new messages arrive, the zombie threads dequeue them and dispatch them to older `MasterAgent` instances.
6. The older `MasterAgent` instances do not recognize the new `workflow_id` in their local `active_workflows` map, log a warning (`"Received message for untracked workflow"`), and drop the message.
7. Consequently, the active workflow deadlocks waiting for task responses, leading to 5 test timeouts and failures in `tests/test_stress_dag_orchestration.py`.

### The Solution
This remediation plan specifies the exact architectural design, data structures, and line-by-line diffs for:
1. **`core/messaging.py`**:
   - Introduce `_ConsumerHandle` to encapsulate callback, stop event, thread pool executor, and worker thread.
   - Implement `unsubscribe(queue_name, callback) -> int`.
   - Implement `clear_consumers(queue_name=None) -> int`.
   - Implement `reset() -> None` (terminating all consumers, draining queues, clearing registry, resetting running state).
   - Enhance `consume()` with fast responsiveness (`timeout=0.1`), graceful termination re-queueing, and clean handle registration.
   - Enhance `stop()` to cleanly terminate all consumer handles and thread pools.
2. **`agents/base.py`**:
   - Implement `BaseAgent.stop()` to cleanly unsubscribe the agent's consumer and shut down background resources.
   - Implement `BaseAgent.is_running` lifecycle tracking and automatic re-entry protection in `run()`.
   - Implement context manager support (`__enter__` / `__exit__`) for idiomatic `with` block resource management.
3. **`tests/conftest.py`**:
   - Introduce an automated `autouse=True` pytest fixture to invoke `broker.reset()` before and after every test function, guaranteeing pristine test isolation across the entire suite.

---

## 2. Root Cause Analysis

### 2.1 The Singleton Accumulation Pattern
In `core/messaging.py` lines 12–24:
```python
class LocalMessageBroker:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LocalMessageBroker, cls).__new__(cls)
                cls._instance._queues = {}
                cls._instance._consumers = {}
                cls._instance._threads = []
                cls._instance._running = True
            return cls._instance
```
`LocalMessageBroker` is a Singleton that persists across the entire lifespan of the Python test runner process.

In `core/messaging.py` lines 47–81:
```python
    def consume(self, queue_name: str, callback, block: bool = True):
        import concurrent.futures
        self.declare_queue(queue_name)
        q = self._queues[queue_name]
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=6, thread_name_prefix=f"Pool-{queue_name}")

        def _worker():
            while self._running:
                try:
                    msg = q.get(timeout=0.5)
                    def _dispatch(m):
                        try:
                            callback(m)
...
        if block:
            _worker()
        else:
            t = threading.Thread(target=_worker, daemon=True, name=f"Consumer-{queue_name}")
            t.start()
            self._threads.append(t)
            logger.info(f"[LocalBroker] Started background concurrent consumer on queue '{queue_name}'")
```

Critical architectural flaws observed in this code:
1. **Unmanaged Threads**: `self._threads` only appends; it never removes finished threads, nor does it provide any handle to stop a thread.
2. **Unmanaged ThreadPoolExecutors**: `pool` is instantiated as a local variable inside `consume()`. There is no reference retained to shut it down.
3. **Unused Registry**: `cls._instance._consumers` is initialized in `__new__` but never populated or referenced anywhere in the class.
4. **Coarse-Grained Flag**: `self._running` is a single boolean for the entire broker. Setting `self._running = False` terminates everything permanently with no restart capability.

### 2.2 Queue Sharing & Competing Consumer Starvation
Python's standard library `queue.Queue` manages concurrent access using an internal `threading.Condition` (`not_empty.wait()`).
When multiple threads call `q.get(timeout=0.5)` on `"master_queue"`, they all wait on this condition.
When a message is published via `q.put(envelope)`:
- Exactly **one** waiting thread is notified and retrieves the message.
- The queue does not perform content-based routing, agent identity checks, or correlation ID matching.
- In a multi-test run:
  - Test 1 starts `MasterAgent` (Worker Thread 1).
  - Test 2 starts a new `MasterAgent` (Worker Thread 2).
  - Both Worker 1 and Worker 2 are actively polling `_queues["master_queue"]`.
  - By Test 5, 5 or more worker threads compete for each message. The probability that the active test's agent receives its own response is only $\frac{1}{N} \le 20\%$.

### 2.3 Silent Message Dropping in MasterAgent
In `agents/master_agent.py` lines 138–142:
```python
        workflow_id = msg.get("correlation_id")

        state = self.active_workflows.get(workflow_id)
        if not state:
            logger.warning(f"[{self.name}] Received message for untracked workflow: {workflow_id}")
            return
```
When Worker Thread 1 (belonging to Test 1's `MasterAgent`) dequeues a response intended for Test 2 (`workflow_id` generated in Test 2):
1. Worker Thread 1 dispatches to `master_1.handle_message(msg)`.
2. `master_1.process_message()` looks for `workflow_id` in `master_1.active_workflows`.
3. The lookup fails (`state is None`).
4. `master_1` logs the warning:
   `WARNING agents.master:master_agent.py:140 [master] Received message for untracked workflow: <uuid>`
5. `master_1` returns early without updating counters or transitioning stages.
6. The message was already popped from the queue and marked `q.task_done()`. It is permanently lost.
7. `master_2` (the active agent in Test 2) never receives the response, its `completed_searches` / `completed_parses` counters never increment, and Test 2 hangs until the 25-second test timeout expires.

### 2.4 Empirical Verification of the Root Cause
To verify this root cause hypothesis independently:
1. Running a single test in complete isolation:
   ```bash
   pytest tests/test_stress_dag_orchestration.py -k test_dag_boundary_zero_companies
   ```
   **Result: PASSED (7.19s)**. When no prior tests have run, no zombie threads exist, and the message is delivered directly to the active agent.
2. Running the full module sequentially:
   ```bash
   pytest tests/test_stress_dag_orchestration.py
   ```
   **Result: 5 FAILED / TIMED OUT**. As tests accumulate, zombie threads swallow task responses, verbatim warnings flood the console, and workflows deadlock.

---

## 3. Detailed Architectural Design

### 3.1 Consumer Descriptor: `_ConsumerHandle`
To manage background workers cleanly, we introduce an internal `_ConsumerHandle` class:

```python
class _ConsumerHandle:
    """Encapsulates a registered consumer's execution context for lifecycle control."""
    def __init__(self, consumer_id: str, queue_name: str, callback, stop_event: threading.Event, pool, thread: threading.Thread = None):
        self.consumer_id = consumer_id
        self.queue_name = queue_name
        self.callback = callback
        self.stop_event = stop_event
        self.pool = pool
        self.thread = thread

    def stop(self, timeout: float = 1.0):
        """Signals stop event, cancels pending pool tasks, and joins worker thread safely."""
        self.stop_event.set()
        if self.pool:
            try:
                self.pool.shutdown(wait=False, cancel_futures=True)
            except Exception:
                try:
                    self.pool.shutdown(wait=False)
                except Exception:
                    pass
        if self.thread and self.thread.is_alive():
            # Prevent thread from attempting to join itself if called from callback
            if threading.current_thread() != self.thread:
                self.thread.join(timeout=timeout)
```

Key attributes:
- `stop_event`: A `threading.Event` checked on every iteration of the worker polling loop.
- `pool`: The `ThreadPoolExecutor` dedicated to this consumer. When stopped, `cancel_futures=True` ensures no pending callbacks run.
- `thread`: The background daemon thread. When stopped, `.join(timeout=timeout)` ensures it has exited before continuing.
- Self-join protection: Prevents `RuntimeError: cannot join current thread` if `stop()` is called from within a callback.

### 3.2 Method Specifications for `LocalMessageBroker`

#### 1. `unsubscribe(queue_name: str, callback) -> int`
- **Purpose**: Unsubscribes a specific callback from a specific queue, stopping its worker thread and thread pool.
- **Algorithm**:
  1. Acquire `self._lock`.
  2. Locate all `_ConsumerHandle`s in `self._consumers.get(queue_name, [])` matching `h.callback == callback`.
  3. Filter out matching handles from `self._consumers[queue_name]`.
  4. Release `self._lock` (vital: release lock before joining threads to avoid deadlocks).
  5. Signal `stop_event.set()` on all matching handles.
  6. Shut down their thread pools.
  7. Join their threads with a 1.0s timeout.
  8. Remove dead threads from `self._threads`.
  9. Return count of unsubscribed consumers.

#### 2. `clear_consumers(queue_name: str = None) -> int`
- **Purpose**: Stops and clears all consumers for a given queue, or all consumers across all queues if `queue_name is None`.
- **Parallel Shutdown Optimization**:
  Instead of stopping and joining threads sequentially (which would take $O(M \times T)$ where $M$ is thread count), `clear_consumers` uses a **two-pass parallel shutdown**:
  - **Pass 1**: Signal `stop_event.set()` and initiate `pool.shutdown()` on **all** handles simultaneously. All worker threads wake up from their 100ms `q.get()` timeout concurrently.
  - **Pass 2**: Join all threads. Because they all began exiting at the same moment, the total wall-clock join time across 10+ threads is only ~100ms instead of 10 seconds.
  - Remove dead threads from `self._threads`.
  - Return total count of cleared consumers.

#### 3. `reset() -> None`
- **Purpose**: Fully resets the broker to an uninitialized, pristine state. Essential for test teardown/setup fixtures.
- **Algorithm**:
  1. Invoke `self.clear_consumers(None)` to terminate all background consumer threads and thread pools.
  2. Acquire `self._lock`.
  3. For every queue in `self._queues.values()`, drain all unconsumed messages using `q.get_nowait()` and `q.task_done()` inside a loop until `q.empty()`.
  4. Clear `self._queues.clear()`.
  5. Clear `self._threads.clear()`.
  6. Reset `self._running = True`.
  7. Release `self._lock`.

#### 4. `stop() -> None`
- **Purpose**: Clean shutdown of broker.
- **Algorithm**:
  1. Under `self._lock`, set `self._running = False`.
  2. Call `self.clear_consumers(None)`.
  3. Join any remaining threads in `self._threads`.

#### 5. Enhanced `consume(queue_name, callback, block=True)`
- **Responsive Polling**: Change `q.get(timeout=0.5)` to `q.get(timeout=0.1)`. Reduces worker stop latency from 500ms to 100ms.
- **Message Preservation**: If `stop_event.is_set()` or `not self._running` immediately after `q.get()`, put the message back on the queue (`q.put(msg)`) before breaking.
- **Registration**: Store `_ConsumerHandle` in `self._consumers[queue_name]`.

### 3.3 Lifecycle Management in `agents/base.py`

#### 1. `BaseAgent.stop()`
```python
    def stop(self):
        """
        Stops the agent's consumer on its input queue cleanly.
        Unsubscribes handle_message from input_queue and releases broker resources.
        """
        if self.is_running:
            logger.info(f"[{self.name}] Stopping consumer on queue '{self.input_queue}'")
            if hasattr(self.broker, "unsubscribe"):
                self.broker.unsubscribe(self.input_queue, self.handle_message)
            elif hasattr(self.broker, "clear_consumers"):
                self.broker.clear_consumers(self.input_queue)
            self.is_running = False
```

#### 2. Re-entry Protection in `BaseAgent.run()`
```python
    def run(self, block: bool = True):
        if self.is_running:
            logger.info(f"[{self.name}] Agent already running on '{self.input_queue}'. Restarting cleanly...")
            self.stop()
        logger.info(f"[{self.name}] Listening on queue '{self.input_queue}' (block={block})")
        self.is_running = True
        self.broker.consume(self.input_queue, self.handle_message, block=block)
```

#### 3. Context Manager Support
```python
    def __enter__(self):
        self.run(block=False)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
```
Allows clean test syntax:
```python
with MasterAgent() as master, JobParsingAgent() as parser, MatchingAgent() as matcher:
    actual_wf_id = master.start_workflow(...)
    ...
# All consumer threads and thread pools automatically shut down on block exit!
```

### 3.4 Automated Test Isolation (`tests/conftest.py`)
To prevent test pollution across all current and future test modules without requiring boilerplate in every test file:
```python
import pytest
from core.messaging import MessageBroker

@pytest.fixture(autouse=True)
def reset_message_broker_fixture():
    """Guarantee a clean broker before and after every test function."""
    broker = MessageBroker()
    if hasattr(broker, "reset"):
        broker.reset()
    yield
    if hasattr(broker, "reset"):
        broker.reset()
```

---

## 4. Line-by-Line Diffs

### 4.1 Diff for `core/messaging.py`

```diff
--- a/core/messaging.py
+++ b/core/messaging.py
@@ -1,6 +1,7 @@
 import json
 import uuid
 import queue
+import concurrent.futures
 import threading
 import logging
 from datetime import datetime, timezone
@@ -9,6 +10,32 @@
 logger = logging.getLogger("core.messaging")
 
 
+class _ConsumerHandle:
+    """Encapsulates a registered consumer's execution context for lifecycle control."""
+
+    def __init__(self, consumer_id: str, queue_name: str, callback, stop_event: threading.Event, pool, thread: threading.Thread = None):
+        self.consumer_id = consumer_id
+        self.queue_name = queue_name
+        self.callback = callback
+        self.stop_event = stop_event
+        self.pool = pool
+        self.thread = thread
+
+    def stop(self, timeout: float = 1.0):
+        self.stop_event.set()
+        if self.pool:
+            try:
+                self.pool.shutdown(wait=False, cancel_futures=True)
+            except Exception:
+                try:
+                    self.pool.shutdown(wait=False)
+                except Exception:
+                    pass
+        if self.thread and self.thread.is_alive():
+            if threading.current_thread() != self.thread:
+                self.thread.join(timeout=timeout)
+
+
 class LocalMessageBroker:
     _instance = None
     _lock = threading.Lock()
@@ -25,9 +52,10 @@
             return cls._instance
 
     def declare_queue(self, queue_name: str):
-        if queue_name not in self._queues:
-            self._queues[queue_name] = queue.Queue()
-            logger.debug(f"[LocalBroker] Declared queue '{queue_name}'")
+        with self._lock:
+            if queue_name not in self._queues:
+                self._queues[queue_name] = queue.Queue()
+                logger.debug(f"[LocalBroker] Declared queue '{queue_name}'")
 
     def publish(self, queue_name: str, payload: dict, source: str, target: str, msg_type: str, correlation_id=None):
         if queue_name not in self._queues:
@@ -46,45 +74,166 @@
         self._queues[queue_name].put(envelope)
 
     def consume(self, queue_name: str, callback, block: bool = True):
-        import concurrent.futures
         self.declare_queue(queue_name)
         q = self._queues[queue_name]
         pool = concurrent.futures.ThreadPoolExecutor(max_workers=6, thread_name_prefix=f"Pool-{queue_name}")
+        stop_event = threading.Event()
 
         def _worker():
-            while self._running:
+            while self._running and not stop_event.is_set():
                 try:
-                    msg = q.get(timeout=0.5)
+                    msg = q.get(timeout=0.1)
+                except queue.Empty:
+                    continue
 
-                    def _dispatch(m):
-                        try:
-                            callback(m)
-                        except Exception as e:
-                            logger.error(f"[LocalBroker] Error in callback for {queue_name}: {e}", exc_info=True)
-                        finally:
+                if stop_event.is_set() or not self._running:
+                    try:
+                        q.put(msg)
+                    except Exception:
+                        pass
+                    break
+
+                def _dispatch(m):
+                    try:
+                        callback(m)
+                    except Exception as e:
+                        logger.error(f"[LocalBroker] Error in callback for {queue_name}: {e}", exc_info=True)
+                    finally:
+                        try:
                             q.task_done()
+                        except Exception:
+                            pass
 
-                    try:
-                        pool.submit(_dispatch, msg)
-                    except (RuntimeError, Exception):
-                        # Pool has been shut down
-                        break
-                except queue.Empty:
-                    continue
+                try:
+                    pool.submit(_dispatch, msg)
+                except (RuntimeError, Exception):
+                    try:
+                        q.put(msg)
+                    except Exception:
+                        pass
+                    break
 
         if block:
-            _worker()
+            handle = _ConsumerHandle(
+                consumer_id=str(uuid.uuid4()),
+                queue_name=queue_name,
+                callback=callback,
+                stop_event=stop_event,
+                pool=pool,
+                thread=None
+            )
+            with self._lock:
+                self._consumers.setdefault(queue_name, []).append(handle)
+            try:
+                _worker()
+            finally:
+                self.unsubscribe(queue_name, callback)
         else:
             t = threading.Thread(target=_worker, daemon=True, name=f"Consumer-{queue_name}")
+            handle = _ConsumerHandle(
+                consumer_id=str(uuid.uuid4()),
+                queue_name=queue_name,
+                callback=callback,
+                stop_event=stop_event,
+                pool=pool,
+                thread=t
+            )
+            with self._lock:
+                self._consumers.setdefault(queue_name, []).append(handle)
+                self._threads.append(t)
             t.start()
             logger.info(f"[LocalBroker] Started background concurrent consumer on queue '{queue_name}'")
 
+    def unsubscribe(self, queue_name: str, callback) -> int:
+        """
+        Unsubscribes a specific callback from queue_name, stopping its worker thread
+        and thread pool. Returns the number of consumers unsubscribed.
+        """
+        with self._lock:
+            if queue_name not in self._consumers:
+                return 0
+            to_remove = [h for h in self._consumers[queue_name] if h.callback == callback]
+            self._consumers[queue_name] = [h for h in self._consumers[queue_name] if h.callback != callback]
+
+        # Parallel shutdown: signal stop first
+        for handle in to_remove:
+            handle.stop_event.set()
+            if handle.pool:
+                try:
+                    handle.pool.shutdown(wait=False, cancel_futures=True)
+                except Exception:
+                    pass
+
+        # Join threads
+        for handle in to_remove:
+            if handle.thread and handle.thread.is_alive() and threading.current_thread() != handle.thread:
+                handle.thread.join(timeout=1.0)
+            with self._lock:
+                if handle.thread in self._threads:
+                    self._threads.remove(handle.thread)
+
+        logger.info(f"[LocalBroker] Unsubscribed {len(to_remove)} consumer(s) from '{queue_name}'")
+        return len(to_remove)
+
+    def clear_consumers(self, queue_name: str = None) -> int:
+        """
+        Stops and clears consumers.
+        If queue_name is provided, stops all consumers for that specific queue.
+        If queue_name is None, stops all consumers across all queues.
+        Returns the number of consumers cleared.
+        """
+        with self._lock:
+            if queue_name is not None:
+                to_stop = self._consumers.pop(queue_name, [])
+            else:
+                to_stop = []
+                for q_consumers in self._consumers.values():
+                    to_stop.extend(q_consumers)
+                self._consumers.clear()
+
+        # Parallel stop signaling
+        for handle in to_stop:
+            handle.stop_event.set()
+            if handle.pool:
+                try:
+                    handle.pool.shutdown(wait=False, cancel_futures=True)
+                except Exception:
+                    pass
+
+        # Join threads
+        for handle in to_stop:
+            if handle.thread and handle.thread.is_alive() and threading.current_thread() != handle.thread:
+                handle.thread.join(timeout=1.0)
+            with self._lock:
+                if handle.thread in self._threads:
+                    self._threads.remove(handle.thread)
+
+        logger.info(f"[LocalBroker] Cleared {len(to_stop)} consumer(s) (queue={queue_name})")
+        return len(to_stop)
+
+    def reset(self):
+        """
+        Full reset of broker state: stops and joins all consumer threads, drains all queues,
+        clears queues and thread references, and resets running flag to True.
+        """
+        logger.info("[LocalBroker] Resetting message broker state...")
+        self.clear_consumers(None)
+
+        with self._lock:
+            for q_name, q in self._queues.items():
+                while not q.empty():
+                    try:
+                        q.get_nowait()
+                        q.task_done()
+                    except (queue.Empty, ValueError):
+                        break
+
+            self._queues.clear()
+            self._threads.clear()
+            self._running = True
+        logger.info("[LocalBroker] Message broker reset complete.")
+
     def stop(self):
-        self._running = False
-        for t in self._threads:
-            t.join(timeout=1.0)
+        with self._lock:
+            self._running = False
+        self.clear_consumers(None)
+        with self._lock:
+            remaining = list(self._threads)
+        for t in remaining:
+            if t.is_alive() and threading.current_thread() != t:
+                t.join(timeout=1.0)
```

---

### 4.2 Diff for `agents/base.py`

```diff
--- a/agents/base.py
+++ b/agents/base.py
@@ -14,10 +14,35 @@
         self.broker.declare_queue(input_queue)
         self.broker.declare_queue("master_queue")
         self.processed_messages = set()
+        self.is_running = False
 
     def run(self, block: bool = True):
+        if self.is_running:
+            logger.info(f"[{self.name}] Agent already running on '{self.input_queue}'. Restarting cleanly...")
+            self.stop()
         logger.info(f"[{self.name}] Listening on queue '{self.input_queue}' (block={block})")
+        self.is_running = True
         self.broker.consume(self.input_queue, self.handle_message, block=block)
 
+    def stop(self):
+        """
+        Stops the agent's consumer on its input queue cleanly.
+        Unsubscribes handle_message from input_queue and releases broker resources.
+        """
+        if self.is_running:
+            logger.info(f"[{self.name}] Stopping consumer on queue '{self.input_queue}'")
+            if hasattr(self.broker, "unsubscribe"):
+                self.broker.unsubscribe(self.input_queue, self.handle_message)
+            elif hasattr(self.broker, "clear_consumers"):
+                self.broker.clear_consumers(self.input_queue)
+            self.is_running = False
+
+    def __enter__(self):
+        self.run(block=False)
+        return self
+
+    def __exit__(self, exc_type, exc_val, exc_tb):
+        self.stop()
+
     def handle_message(self, msg: dict):
```

---

### 4.3 Proposed File: `tests/conftest.py`

```python
"""
Pytest global fixtures for test isolation and resource cleanup.
"""
import pytest
from core.messaging import MessageBroker


@pytest.fixture(autouse=True)
def reset_message_broker_fixture():
    """
    Auto-use fixture that runs before and after each test function.
    Guarantees that LocalMessageBroker has zero lingering consumer threads
    or residual queue messages from previous tests.
    """
    broker = MessageBroker()
    if hasattr(broker, "reset"):
        broker.reset()
    yield
    if hasattr(broker, "reset"):
        broker.reset()
```

---

## 5. Verification Protocol & Acceptance Matrix

### 5.1 Independent Verification Commands

To independently verify that the proposed remediation resolves the competing zombie consumer issue without breaking existing capabilities:

```bash
# 1. Run the targeted DAG boundary conditions test file
pytest tests/test_stress_dag_orchestration.py -v

# 2. Run the broker concurrency stress suite
pytest tests/test_stress_broker_concurrency.py -v

# 3. Run the SQLite stage checkpointing suite
pytest tests/test_stage_checkpointing_sqlite.py -v

# 4. Run the end-to-end integration test
pytest tests/test_pipeline_e2e.py -v

# 5. Run the entire test suite across all 11 modules
pytest tests/ -v
```

### 5.2 Expected Results
- `tests/test_stress_dag_orchestration.py`: **5 passed / 0 failed** (all 5 boundary conditions and concurrent workflows succeed within timeouts).
- `tests/test_stress_broker_concurrency.py`: **3 passed / 0 failed** (1,000 messages across 10 threads pass with 0 loss).
- Zero warnings regarding `"Received message for untracked workflow"`.
- Clean termination of all background threads at the conclusion of each test.
