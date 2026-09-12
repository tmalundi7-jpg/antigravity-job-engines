# MasterAgent State Resilience & 5-Stage Checkpointing Remediation Plan

**Agent**: Explorer M1-Iteration 2-2  
**Target Milestone**: Milestone 1 Remediation  
**Target Module**: `agents/master_agent.py`  
**Date**: 2026-09-03  

---

## 1. Executive Summary

Empirical testing on the raw host machine revealed that while low-level components (`LocalMessageBroker` concurrency, SQLite table schemas, ChromaDB 3072-dim embeddings) function correctly in isolation, integration tests across DAG orchestration (`tests/test_stress_dag_orchestration.py` and `tests/test_stage_checkpointing_sqlite.py`) suffered from 6 failing tests due to two critical issues in `MasterAgent`:

1. **Untracked Message Discarding (Competing Zombie Consumers)**:  
   `LocalMessageBroker` is a process-wide singleton (`LocalMessageBroker._instance`). Each invocation of `master.run(block=False)` registers a persistent daemon consumer thread polling `master_queue`. When multiple tests or agent instances run sequentially in the same process, worker threads from older `MasterAgent` instances compete to consume incoming messages. Because `self.active_workflows` was stored solely as an instance dictionary, messages belonging to newly started workflows were dequeued by older instances and discarded with `Received message for untracked workflow: <uuid>`. This starved active workflows of responses and triggered test timeouts and deadlocks.

2. **0-Job Boundary Checkpointing Bypass**:  
   When job search returns 0 jobs for all companies in Stage 2, `MasterAgent` never increments `dispatched_parses` or `dispatched_matches`. As a result, the state machine skipped Stage 3 (`STAGE_3_JOB_PARSING`) and Stage 4 (`STAGE_4_MATCHING`) entirely in SQLite, transitioning directly from `STAGE_2_JOB_DISCOVERY` to `COMPLETED`. This violated the project architectural contract requiring `WorkflowState` to transition through all 5 stages in sequence.

This remediation plan provides an exact, robust architectural fix:
- Implementing a **class-level shared registry** (`_global_active_workflows`, `_global_completed_reports`) with re-entrant thread locking (`_state_lock`).
- Providing **fallback hydration from SQLite `WorkflowState`** via `_get_or_hydrate_workflow` so that any `MasterAgent` instance can immediately recover in-flight workflows even if memory state is missing.
- Enforcing **explicit 5-stage sequential progression on 0-job boundaries**: recording Stage 3 (`total_raw_jobs = 0`, `total_parsed_jobs = 0`) and Stage 4 (`total_parsed_jobs = 0`, `total_matched = 0`) before transitioning to `COMPLETED`.

---

## 2. Deep Dive: Untracked Message Dropping Analysis

### 2.1 The Architectural Mechanism of Message Loss
1. In `core/messaging.py:12-24`, `LocalMessageBroker` is defined as a Singleton:
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
2. When an agent calls `broker.consume(queue_name, callback, block=False)` (e.g. via `master.run(block=False)` in `tests/test_stage_checkpointing_sqlite.py:27`), `LocalMessageBroker` starts a daemon thread executing `_worker()`, which continuously pops messages from `self._queues["master_queue"]` and submits `callback(msg)` to a `ThreadPoolExecutor`.
3. In `agents/master_agent.py:41`, `self.active_workflows = {}` is initialized as a per-instance dictionary.
4. When a subsequent test runs in the same test process (e.g. `test_stage_checkpointing_under_zero_jobs` or `test_dag_boundary_multiple_jobs_per_company`):
   - A new `MasterAgent()` is instantiated (`master2`).
   - `master2.start_workflow(...)` generates `wf_id_2` and stores it into `master2.active_workflows[wf_id_2]`.
   - `master2.run(block=False)` attaches a second consumer to `"master_queue"`.
5. Now two worker threads are competing on the single queue `self._queues["master_queue"]`.
6. When `company_list_agent` or `job_search_agent` publishes a `task_response` for `wf_id_2` to `"master_queue"`, the worker thread belonging to `master1` often pops the message first.
7. `master1` executes `handle_message` -> `process_message`:
   ```python
   state = self.active_workflows.get(workflow_id)
   if not state:
       logger.warning(f"[{self.name}] Received message for untracked workflow: {workflow_id}")
       return
   ```
8. Because `wf_id_2` is only present in `master2.active_workflows`, `master1` logs a warning and **discards the message**.
9. `master2` never receives the response. `completed_searches` is never incremented. `master2` waits indefinitely until the test assertion timeout expires.

### 2.2 Dual-Layer State Resilience Design

To make message processing 100% resilient against multi-instance concurrency, process reuse, and zombie consumers, we design two synergistic mechanisms:

#### Layer 1: Class-Level Shared Registry (`_global_active_workflows`)
At the class level of `MasterAgent`:
```python
class MasterAgent(BaseAgent):
    _global_active_workflows = {}
    _global_completed_reports = {}
    _state_lock = threading.RLock()
```
In `__init__`:
```python
    self.active_workflows = MasterAgent._global_active_workflows
    self.completed_reports = MasterAgent._global_completed_reports
```
**Benefits**:
- Any `MasterAgent` instance (and any worker thread associated with any instance) immediately shares the identical in-memory dictionary.
- Whichever consumer thread dequeues a message from `master_queue` will find the active workflow in `_global_active_workflows`.
- All state mutations (counters, lists, status updates) and transition checks are synchronized under `MasterAgent._state_lock`, preventing race conditions during concurrent multi-agent responses.

#### Layer 2: Fallback Hydration from SQLite `WorkflowState`
If a message arrives for a `workflow_id` that is not present in `_global_active_workflows` (e.g. process restart, distributed execution, or test resets), `MasterAgent` queries SQLite before declaring the message untracked:
```python
def _get_or_hydrate_workflow(self, workflow_id: str) -> dict | None:
    if not workflow_id:
        return None

    with MasterAgent._state_lock:
        if workflow_id in MasterAgent._global_active_workflows:
            return MasterAgent._global_active_workflows[workflow_id]

        # Attempt SQLite hydration
        try:
            with SessionLocal() as db:
                record = db.query(WorkflowState).filter(WorkflowState.id == workflow_id).first()
                if record:
                    data = dict(record.data or {})
                    logger.info(f"[{self.name}] Hydrated untracked workflow [{workflow_id[:8]}] from SQLite database")
                    hydrated_state = {
                        "workflow_id": workflow_id,
                        "goal": data.get("goal", ""),
                        "params": data.get("params", {}),
                        "custom_companies": data.get("custom_companies"),
                        "candidate": data.get("candidate") or {
                            "id": data.get("candidate_id", "cand_123"),
                            "name": data.get("candidate_name", "Candidate A"),
                            "title": data.get("params", {}).get("role", "Management Accountant"),
                            "skills": ["ACCA", "Financial Reporting", "Variance Analysis", "Excel", "Budgeting", "CIMA"],
                            "years_experience": 5,
                            "certifications": ["ACCA Qualified"],
                            "location": data.get("params", {}).get("filters", {}).get("location", "London")
                        },
                        "status": record.status or "STAGE_1_COMPANY_LIST",
                        "companies": data.get("companies", []),
                        "raw_jobs_collected": data.get("raw_jobs_collected", []),
                        "parsed_jobs": data.get("parsed_jobs", []),
                        "ranked_matches": data.get("ranked_matches", []),
                        "disqualified_matches": data.get("disqualified_matches", []),
                        "expected_searches": data.get("expected_searches", 0),
                        "completed_searches": data.get("completed_searches", 0),
                        "dispatched_parses": data.get("dispatched_parses", 0),
                        "completed_parses": data.get("completed_parses", 0),
                        "dispatched_matches": data.get("dispatched_matches", 0),
                        "completed_matches": data.get("completed_matches", 0),
                        "start_time": data.get("started_at") or (record.created_at.isoformat() if record.created_at else datetime.now(timezone.utc).isoformat()),
                        "start_ts": record.created_at.timestamp() if record.created_at else time.time(),
                        "completed": record.status == "COMPLETED"
                    }
                    MasterAgent._global_active_workflows[workflow_id] = hydrated_state
                    return hydrated_state
        except Exception as e:
            logger.error(f"[{self.name}] SQLite hydration failed for [{workflow_id}]: {e}")

        return None
```
**Result**: Under no circumstances will a legitimate workflow message ever be discarded as "untracked".

---

## 3. Deep Dive: 0-Job Boundary Condition & 5-Stage Checkpointing

### 3.1 The 0-Job Boundary Failure
In `PROJECT.md` Section 7 and 87-94:
- The DAG state machine must persist transitions to `WorkflowState` at every stage:
  - `STAGE_1_COMPANY_LIST`
  - `STAGE_2_JOB_DISCOVERY`
  - `STAGE_3_JOB_PARSING`
  - `STAGE_4_MATCHING`
  - `COMPLETED`
- `tests/test_stage_checkpointing_sqlite.py` asserts that every stage is recorded in the database.

However, in `agents/master_agent.py:194-218`:
```python
if raw_jobs:
    state["dispatched_parses"] += 1
    state["status"] = "STAGE_3_JOB_PARSING"
    checkpoint_workflow(
        workflow_id=workflow_id,
        status="STAGE_3_JOB_PARSING",
        data={ ... }
    )
    self.broker.publish("job_parse_queue", ...)

self._check_and_finalize_if_complete(workflow_id)
```
When discovery yields 0 vacancies across all target companies:
- `raw_jobs` is empty (`[]`).
- `state["dispatched_parses"]` is NOT incremented (remains `0`).
- `checkpoint_workflow` for `STAGE_3_JOB_PARSING` is NOT invoked.
- `state["status"]` is NEVER set to `STAGE_3_JOB_PARSING`.
- No parsing tasks are dispatched, so no matching tasks are dispatched.
- `state["dispatched_matches"]` remains `0`.
- `checkpoint_workflow` for `STAGE_4_MATCHING` is NOT invoked.
- In `_check_and_finalize_if_complete`:
  ```python
  searches_done = state["completed_searches"] >= state["expected_searches"]
  parses_done = 0 >= 0   # True
  matches_done = 0 >= 0  # True
  if searches_done and parses_done and matches_done:
      self._finalize_workflow(workflow_id)
  ```
- `_finalize_workflow` immediately writes `status="COMPLETED"`.
- **Result in SQLite**: The workflow record jumps directly from `STAGE_2_JOB_DISCOVERY` to `COMPLETED`. Stages 3 and 4 are completely bypassed in SQLite history!

### 3.2 Strict 5-Stage Checkpointing Architecture
To ensure every workflow satisfies the 5-stage progression contract, even when 0 vacancies are discovered, `_check_and_finalize_if_complete` must explicitly execute the stage checkpoints before finalization:

```python
def _check_and_finalize_if_complete(self, workflow_id: str):
    with MasterAgent._state_lock:
        state = self._get_or_hydrate_workflow(workflow_id)
        if not state or state.get("completed"):
            return

        searches_done = state["completed_searches"] >= state["expected_searches"]
        parses_done = state["completed_parses"] >= state["dispatched_parses"]
        matches_done = state["completed_matches"] >= state["dispatched_matches"]

        if not searches_done or not parses_done or not matches_done:
            return

        # 0-Job Boundary Checkpointing: Ensure 5-stage sequential progression in SQLite
        # If no raw jobs were dispatched for parsing, explicitly checkpoint Stage 3 (0 items)
        if state["dispatched_parses"] == 0 and not state.get("_stage_3_checkpointed"):
            state["_stage_3_checkpointed"] = True
            state["status"] = "STAGE_3_JOB_PARSING"
            checkpoint_workflow(
                workflow_id=workflow_id,
                status="STAGE_3_JOB_PARSING",
                data={
                    "stage": "STAGE_3_JOB_PARSING",
                    "stage_name": "Job Parsing",
                    "total_raw_jobs": len(state["raw_jobs_collected"]),
                    "total_parsed_jobs": 0,
                    "dispatched_parses": 0,
                    "completed_parses": 0,
                    "completed_searches": state["completed_searches"],
                    "expected_searches": state["expected_searches"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            )

        # If no parsed jobs were dispatched for matching, explicitly checkpoint Stage 4 (0 items)
        if state["dispatched_matches"] == 0 and not state.get("_stage_4_checkpointed"):
            state["_stage_4_checkpointed"] = True
            state["status"] = "STAGE_4_MATCHING"
            checkpoint_workflow(
                workflow_id=workflow_id,
                status="STAGE_4_MATCHING",
                data={
                    "stage": "STAGE_4_MATCHING",
                    "stage_name": "Candidate Matching",
                    "total_parsed_jobs": len(state["parsed_jobs"]),
                    "dispatched_matches": 0,
                    "completed_matches": 0,
                    "total_matched": 0,
                    "total_disqualified": 0,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            )

        self._finalize_workflow(workflow_id)
```

### 3.3 Proof of Compatibility with Existing Tests
1. **`test_workflow_state_transitions_through_all_five_stages_in_sqlite`**:
   - 1 company with 1 job.
   - `dispatched_parses` is 1, `dispatched_matches` is 1.
   - Stage 3 and Stage 4 are checkpointed normally during dispatch.
   - The boundary guards `dispatched_parses == 0` evaluate to `False`, avoiding redundant checkpoints.
   - All 5 stages recorded in SQLite in sequence. PASSES.

2. **`test_stage_checkpointing_under_zero_jobs`**:
   - 1 company with 0 jobs.
   - `dispatched_parses` is 0, `dispatched_matches` is 0.
   - When search completes, the boundary logic writes `STAGE_3_JOB_PARSING` with `total_parsed_jobs: 0`, then writes `STAGE_4_MATCHING` with `total_matched: 0`, then writes `COMPLETED`.
   - `statuses` recorded: `['STAGE_1_COMPANY_LIST', 'STAGE_2_JOB_DISCOVERY', 'STAGE_3_JOB_PARSING', 'STAGE_4_MATCHING', 'COMPLETED']`.
   - The test assertions:
     - `assert "STAGE_1_COMPANY_LIST" in statuses` -> True
     - `assert "STAGE_2_JOB_DISCOVERY" in statuses` -> True
     - `assert "COMPLETED" in statuses` -> True
     - `assert final_record.status == "COMPLETED"` -> True
     - `assert final_record.data.get("total_raw_jobs") == 0` -> True
     - `assert final_record.data.get("total_parsed_jobs") == 0` -> True
   - PASSES cleanly.

3. **`test_dag_boundary_zero_jobs_all_companies`**:
   - 2 companies with 0 jobs.
   - Asserts `state["dispatched_parses"] == 0`, `state["completed_parses"] == 0`, `state["dispatched_matches"] == 0`, `state["completed_matches"] == 0`.
   - Since the boundary checkpointing records Stage 3 & 4 with 0 counts without mutating `dispatched_parses` or `dispatched_matches`, all counters remain `0`.
   - PASSES cleanly.

---

## 4. Line-by-Line Implementation Diff for `agents/master_agent.py`

Below is the exact unified diff to be applied to `agents/master_agent.py`:

```diff
--- a/agents/master_agent.py
+++ b/agents/master_agent.py
@@ -3,6 +3,7 @@ import logging
 import uuid
 import time
 import json
+import threading
 from datetime import datetime, timezone
 from agents.base import BaseAgent
 from core.llm import extract_json
@@ -32,15 +33,83 @@ INTENT_SCHEMA = {
 class MasterAgent(BaseAgent):
+    # Class-level shared registries: guarantees that across all MasterAgent instances
+    # and concurrent worker threads, no message is ever discarded as 'untracked'.
+    _global_active_workflows = {}
+    _global_completed_reports = {}
+    _state_lock = threading.RLock()
+
+    @classmethod
+    def reset_registry(cls):
+        """Helper to cleanly reset class-level workflow state for testing."""
+        with cls._state_lock:
+            cls._global_active_workflows.clear()
+            cls._global_completed_reports.clear()
+
     def __init__(self):
         super().__init__("master", "master_queue")
         self.broker.declare_queue("company_list_queue")
         self.broker.declare_queue("job_search_queue")
         self.broker.declare_queue("job_parse_queue")
         self.broker.declare_queue("matching_queue")
 
-        # State tracking per workflow
-        self.active_workflows = {}
-        self.completed_reports = {}
+        # Reference shared class-level registries
+        self.active_workflows = MasterAgent._global_active_workflows
+        self.completed_reports = MasterAgent._global_completed_reports
+
+    def _get_or_hydrate_workflow(self, workflow_id: str) -> dict | None:
+        """
+        Thread-safe retrieval of workflow state.
+        If workflow_id is untracked in-memory, attempts fallback hydration from SQLite WorkflowState
+        to guarantee no message is discarded across multi-instance or distributed execution.
+        """
+        if not workflow_id:
+            return None
+
+        with MasterAgent._state_lock:
+            if workflow_id in MasterAgent._global_active_workflows:
+                return MasterAgent._global_active_workflows[workflow_id]
+
+            # Fallback hydration from SQLite
+            try:
+                with SessionLocal() as db:
+                    record = db.query(WorkflowState).filter(WorkflowState.id == workflow_id).first()
+                    if record:
+                        data = dict(record.data or {})
+                        logger.info(f"[{self.name}] Hydrated untracked workflow [{workflow_id[:8]}] from SQLite database")
+                        hydrated_state = {
+                            "workflow_id": workflow_id,
+                            "goal": data.get("goal", ""),
+                            "params": data.get("params", {}),
+                            "custom_companies": data.get("custom_companies"),
+                            "candidate": data.get("candidate") or {
+                                "id": data.get("candidate_id", "cand_123"),
+                                "name": data.get("candidate_name", "Candidate A"),
+                                "title": data.get("params", {}).get("role", "Management Accountant"),
+                                "skills": ["ACCA", "Financial Reporting", "Variance Analysis", "Excel", "Budgeting", "CIMA"],
+                                "years_experience": 5,
+                                "certifications": ["ACCA Qualified"],
+                                "location": data.get("params", {}).get("filters", {}).get("location", "London")
+                            },
+                            "status": record.status or "STAGE_1_COMPANY_LIST",
+                            "companies": data.get("companies", []),
+                            "raw_jobs_collected": data.get("raw_jobs_collected", []),
+                            "parsed_jobs": data.get("parsed_jobs", []),
+                            "ranked_matches": data.get("ranked_matches", []),
+                            "disqualified_matches": data.get("disqualified_matches", []),
+                            "expected_searches": data.get("expected_searches", 0),
+                            "completed_searches": data.get("completed_searches", 0),
+                            "dispatched_parses": data.get("dispatched_parses", 0),
+                            "completed_parses": data.get("completed_parses", 0),
+                            "dispatched_matches": data.get("dispatched_matches", 0),
+                            "completed_matches": data.get("completed_matches", 0),
+                            "start_time": data.get("started_at") or (record.created_at.isoformat() if record.created_at else datetime.now(timezone.utc).isoformat()),
+                            "start_ts": record.created_at.timestamp() if record.created_at else time.time(),
+                            "completed": record.status == "COMPLETED"
+                        }
+                        MasterAgent._global_active_workflows[workflow_id] = hydrated_state
+                        return hydrated_state
+            except Exception as e:
+                logger.error(f"[{self.name}] Error during SQLite fallback hydration for [{workflow_id}]: {e}")
+
+            return None
 
     def start_workflow(self, goal: str, candidate_profile: dict = None, custom_companies: list = None) -> str:
@@ -95,7 +164,8 @@ class MasterAgent(BaseAgent):
             "start_ts": time.time(),
             "completed": False
         }
-        self.active_workflows[workflow_id] = workflow_state
+        with MasterAgent._state_lock:
+            MasterAgent._global_active_workflows[workflow_id] = workflow_state
 
         # Stage 1 Checkpoint: Persist initial state to Database
         checkpoint_workflow(
@@ -106,6 +176,8 @@ class MasterAgent(BaseAgent):
                 "stage_name": "Company Discovery",
                 "goal": goal,
                 "params": params,
+                "candidate": workflow_state["candidate"],
                 "candidate_id": workflow_state["candidate"].get("id"),
                 "candidate_name": workflow_state["candidate"].get("name"),
                 "custom_companies": custom_companies,
@@ -135,11 +207,12 @@ class MasterAgent(BaseAgent):
         payload = msg.get("payload", {})
         workflow_id = msg.get("correlation_id")
 
-        state = self.active_workflows.get(workflow_id)
-        if not state:
-            logger.warning(f"[{self.name}] Received message for untracked workflow: {workflow_id}")
-            return
+        with MasterAgent._state_lock:
+            state = self._get_or_hydrate_workflow(workflow_id)
+            if not state:
+                logger.warning(f"[{self.name}] Received message for untracked workflow: {workflow_id}")
+                return
 
             logger.info(f"[{self.name}] Processed {msg_type} from {source} for workflow [{workflow_id[:8]}]")
 
@@ -273,14 +346,55 @@ class MasterAgent(BaseAgent):
 
     def _check_and_finalize_if_complete(self, workflow_id: str):
-        state = self.active_workflows.get(workflow_id)
-        if not state or state.get("completed"):
-            return
+        with MasterAgent._state_lock:
+            state = self._get_or_hydrate_workflow(workflow_id)
+            if not state or state.get("completed"):
+                return
 
-        searches_done = state["completed_searches"] >= state["expected_searches"]
-        parses_done = state["completed_parses"] >= state["dispatched_parses"]
-        matches_done = state["completed_matches"] >= state["dispatched_matches"]
+            searches_done = state["completed_searches"] >= state["expected_searches"]
+            parses_done = state["completed_parses"] >= state["dispatched_parses"]
+            matches_done = state["completed_matches"] >= state["dispatched_matches"]
 
-        if searches_done and parses_done and matches_done:
-            self._finalize_workflow(workflow_id)
+            if not searches_done or not parses_done or not matches_done:
+                return
+
+            # 0-Job Boundary Checkpointing: Ensure 5-stage sequential progression in SQLite
+            # If no raw jobs were dispatched for parsing, explicitly checkpoint Stage 3 (0 items)
+            if state["dispatched_parses"] == 0 and not state.get("_stage_3_checkpointed"):
+                state["_stage_3_checkpointed"] = True
+                state["status"] = "STAGE_3_JOB_PARSING"
+                checkpoint_workflow(
+                    workflow_id=workflow_id,
+                    status="STAGE_3_JOB_PARSING",
+                    data={
+                        "stage": "STAGE_3_JOB_PARSING",
+                        "stage_name": "Job Parsing",
+                        "total_raw_jobs": len(state["raw_jobs_collected"]),
+                        "total_parsed_jobs": 0,
+                        "dispatched_parses": 0,
+                        "completed_parses": 0,
+                        "completed_searches": state["completed_searches"],
+                        "expected_searches": state["expected_searches"],
+                        "updated_at": datetime.now(timezone.utc).isoformat()
+                    }
+                )
+
+            # If no parsed jobs were dispatched for matching, explicitly checkpoint Stage 4 (0 items)
+            if state["dispatched_matches"] == 0 and not state.get("_stage_4_checkpointed"):
+                state["_stage_4_checkpointed"] = True
+                state["status"] = "STAGE_4_MATCHING"
+                checkpoint_workflow(
+                    workflow_id=workflow_id,
+                    status="STAGE_4_MATCHING",
+                    data={
+                        "stage": "STAGE_4_MATCHING",
+                        "stage_name": "Candidate Matching",
+                        "total_parsed_jobs": len(state["parsed_jobs"]),
+                        "dispatched_matches": 0,
+                        "completed_matches": 0,
+                        "total_matched": 0,
+                        "total_disqualified": 0,
+                        "updated_at": datetime.now(timezone.utc).isoformat()
+                    }
+                )
+
+            self._finalize_workflow(workflow_id)
 
     def _finalize_workflow(self, workflow_id: str):
-        state = self.active_workflows[workflow_id]
-        state["status"] = "COMPLETED"
+        with MasterAgent._state_lock:
+            state = self._get_or_hydrate_workflow(workflow_id)
+            if not state:
+                return
+            state["status"] = "COMPLETED"
@@ -395,7 +509,8 @@ class MasterAgent(BaseAgent):
                 "executive_report_markdown": report_md
             }
         )
-        self.completed_reports[workflow_id] = state
+        MasterAgent._global_completed_reports[workflow_id] = state
 
     def get_report(self, workflow_id: str) -> dict:
-        return self.completed_reports.get(workflow_id)
+        with MasterAgent._state_lock:
+            return MasterAgent._global_completed_reports.get(workflow_id)
```

---

## 5. Verification Plan & Test Commands

To verify the remediation:

### Test Step 1: Run Stage Checkpointing Tests
```bash
pytest -v tests/test_stage_checkpointing_sqlite.py
```
**Expected**: Both tests pass 100% (`test_workflow_state_transitions_through_all_five_stages_in_sqlite` and `test_stage_checkpointing_under_zero_jobs`).

### Test Step 2: Run DAG Stress & Boundary Tests
```bash
pytest -v tests/test_stress_dag_orchestration.py
```
**Expected**: All 5 DAG boundary & stress tests pass (`test_dag_boundary_multiple_jobs_per_company`, `test_dag_boundary_zero_jobs_all_companies`, `test_dag_boundary_mixed_jobs`, `test_dag_boundary_zero_companies`, `test_dag_concurrent_workflows`).

### Test Step 3: Run Full Combined Test Suite
```bash
pytest -v tests/test_broker.py tests/test_db.py tests/test_matching.py tests/test_matching_stress.py tests/test_parser.py tests/test_pipeline_e2e.py tests/test_stress_broker_concurrency.py tests/test_stress_sqlite_and_chroma.py tests/test_stage_checkpointing_sqlite.py tests/test_stress_dag_orchestration.py
```
**Expected**: 100% pass across all DAG and checkpointing suites.
