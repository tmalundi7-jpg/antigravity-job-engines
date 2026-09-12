# Challenger M1-2 Handoff Report: DAG Orchestration & Raw-Machine Fallbacks

**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

Empirical testing was executed across the full project test suite using `pytest` on the host machine (`Python 3.12.10`, `pytest-9.1.1`, Windows raw environment). A total of 52 tests across 11 test modules were executed.

### Test Summary
- **Total Tests Executed**: 52
- **Passed**: 44
- **Failed**: 8
- **Execution Duration**: 102.55s

### Module Breakdown
| Test Module | Tests Run | Result | Focus Area |
|---|---|---|---|
| `tests/test_broker.py` | 1 | PASSED | Basic broker pub/sub |
| `tests/test_db.py` | 1 | PASSED | Basic DB initialization & insertion |
| `tests/test_matching.py` | 4 | PASSED | Matching agent basic tests |
| `tests/test_matching_stress.py` | 19 | PASSED | Candidate matching edge cases & scoring |
| `tests/test_parser.py` | 7 | PASSED | HTML parsing & schema extraction |
| `tests/test_pipeline_e2e.py` | 1 | PASSED | Single happy-path E2E run |
| `tests/test_stress_broker_concurrency.py` | 3 | **PASSED** | 1,000 msgs across 10 threads, multi-queue, callback error isolation |
| `tests/test_stress_sqlite_and_chroma.py` | 4 | **PASSED** | SQLite schema/CRUD, 20-thread concurrency, ChromaDB 3072-dim disk persistence |
| `tests/test_forensic_audit.py` | 5 | **1 FAILED** | Prefilter math gating failure |
| `tests/test_stage_checkpointing_sqlite.py` | 2 | **2 FAILED** | SQLite 5-stage transition audit & 0-job checkpointing |
| `tests/test_stress_dag_orchestration.py` | 5 | **5 FAILED** | DAG boundary conditions & concurrency deadlocks |

---

### Verbatim Failures & Tool Outputs

#### Failure 1: Competing Zombie Consumers & Deadlocks in DAG Orchestration
From `tests/test_stress_dag_orchestration.py`:
- `test_dag_boundary_multiple_jobs_per_company` (5 jobs/company): FAILED (timed out after 25.0s, status remained `STAGE_3_JOB_PARSING`, 0 parses completed)
- `test_dag_boundary_zero_jobs_all_companies` (0 jobs/company): FAILED (timed out after 10.0s, status remained `STAGE_1_COMPANY_LIST`)
- `test_dag_boundary_mixed_jobs`: FAILED (`assert 0 == 1`, completed searches remained 0)
- `test_dag_boundary_zero_companies`: FAILED (`assert False is True`, deadlocked on 0 companies)
- `test_dag_concurrent_workflows`: FAILED (`AssertionError: Workflow 1 failed to complete`)

Verbatim warning logs captured during execution:
```
WARNING  agents.master:master_agent.py:140 [master] Received message for untracked workflow: 90599344-349a-4eed-aa49-ca53e24f31bf
WARNING  agents.master:master_agent.py:140 [master] Received message for untracked workflow: 08cbd427-c3cb-437c-93eb-809f5f76c2ea
WARNING  agents.master:master_agent.py:140 [master] Received message for untracked workflow: 494cae7d-6783-415a-83af-bebc1aa76afe
WARNING  agents.master:master_agent.py:140 [master] Received message for untracked workflow: 05537d40-3b49-4b82-b566-3dfd5c07ec70
WARNING  agents.master:master_agent.py:140 [master] Received message for untracked workflow: 29f47758-9d66-4a81-8369-d9b617e45ee1
WARNING  agents.master:master_agent.py:140 [master] Received message for untracked workflow: 9c27a416-749a-4d1b-9b01-6abc80f19263
```

#### Failure 2: Stage Checkpointing Bypass in SQLite
From `tests/test_stage_checkpointing_sqlite.py::test_stage_checkpointing_under_zero_jobs`:
```python
>       assert "STAGE_2_JOB_DISCOVERY" in statuses
E       AssertionError: assert 'STAGE_2_JOB_DISCOVERY' in ['STAGE_1_COMPANY_LIST', 'COMPLETED']
```
And in `test_workflow_state_transitions_through_all_five_stages_in_sqlite`:
```python
>       assert state.get("completed") is True, f"Workflow did not complete: {state}"
E       AssertionError: Workflow did not complete: {'workflow_id': '90599344-349a-4eed-aa49-ca53e24f31bf', 'status': 'STAGE_3_JOB_PARSING', ... 'completed_searches': 1, 'dispatched_parses': 1, 'completed_parses': 0, ... 'completed': False}
```

#### Failure 3: Vector Math Prefilter Gating Test Failure
From `tests/test_forensic_audit.py::test_forensic_check_2_stage_1_prefilter_math_and_gating`:
```python
>       assert len(ranked) == 1
E       AssertionError: assert 2 == 1
E        +  where 2 = len([{'job_id': 'job_forensic_pass_02', ...}, {'job_id': 'job_forensic_fail_01', ...}])
```

---

## 2. Logic Chain

### 2.1 Competing Zombie Consumers on Singleton LocalMessageBroker (Root Cause of DAG Deadlocks)
1. **Observation**: `LocalMessageBroker` is implemented as a Singleton (`core/messaging.py:12-24`). When `broker.consume(queue_name, callback, block=False)` is invoked, it declares the queue and launches a background daemon thread with a dedicated `ThreadPoolExecutor(max_workers=6)` that continuously runs `_worker()` polling `q.get(timeout=0.5)` (`core/messaging.py:53-80`).
2. **Observation**: `LocalMessageBroker` provides no `unsubscribe()`, `remove_consumer()`, or `reset()` mechanism (`core/messaging.py:82-86`).
3. **Observation**: `MasterAgent.__init__` creates `self.active_workflows = {}` as an instance attribute (`agents/master_agent.py:41`).
4. **Logic Step**: When an agent calls `agent.run(block=False)` in a test (e.g. `test_pipeline_e2e.py`), that specific `MasterAgent` instance's `handle_message` callback is permanently subscribed to `"master_queue"`.
5. **Logic Step**: When a subsequent test runs (e.g., `test_stress_dag_orchestration.py`), a new `MasterAgent` instance is instantiated and registered on `"master_queue"`.
6. **Logic Step**: Because `"master_queue"` is a shared `queue.Queue` in the singleton broker, both the old `MasterAgent` instance and the new `MasterAgent` instance compete as consumers on `"master_queue"`.
7. **Logic Step**: Messages intended for the new workflow are picked up by the old `MasterAgent` instance's worker thread.
8. **Logic Step**: In `agents/master_agent.py:138-141`:
   ```python
   state = self.active_workflows.get(workflow_id)
   if not state:
       logger.warning(f"[{self.name}] Received message for untracked workflow: {workflow_id}")
       return
   ```
   The old instance does not have the new `workflow_id` in its local `self.active_workflows` dict. It logs a warning and silently discards the message.
9. **Conclusion**: The active workflow never receives the task response. Its internal counters (`completed_searches`, `completed_parses`, `completed_matches`) are never incremented, `_check_and_finalize_if_complete` never triggers, and the workflow deadlocks until the test timeout expires.

### 2.2 Stage Checkpointing Skipping under 0-Job Boundary Condition
1. **Observation**: In `agents/master_agent.py:194-216`:
   ```python
   if raw_jobs:
       state["dispatched_parses"] += 1
       state["status"] = "STAGE_3_JOB_PARSING"
       checkpoint_workflow(workflow_id=workflow_id, status="STAGE_3_JOB_PARSING", ...)
       self.broker.publish("job_parse_queue", ...)
   self._check_and_finalize_if_complete(workflow_id)
   ```
2. **Observation**: In `agents/master_agent.py:226-254`:
   ```python
   if parsed_jobs:
       state["dispatched_matches"] += 1
       state["status"] = "STAGE_4_MATCHING"
       checkpoint_workflow(workflow_id=workflow_id, status="STAGE_4_MATCHING", ...)
       self.broker.publish("matching_queue", ...)
   self._check_and_finalize_if_complete(workflow_id)
   ```
3. **Observation**: In `agents/master_agent.py:280-285`:
   ```python
   searches_done = state["completed_searches"] >= state["expected_searches"]
   parses_done = state["completed_parses"] >= state["dispatched_parses"]
   matches_done = state["completed_matches"] >= state["dispatched_matches"]

   if searches_done and parses_done and matches_done:
       self._finalize_workflow(workflow_id)
   ```
4. **Logic Step**: When all crawled companies return 0 vacancies (`raw_jobs = []`), `state["dispatched_parses"]` remains `0`, and `state["status"]` is never updated to `STAGE_3_JOB_PARSING`. `checkpoint_workflow` is never called for Stage 3.
5. **Logic Step**: No messages are sent to `job_parse_queue` or `matching_queue`. `state["dispatched_matches"]` remains `0`. `STAGE_4_MATCHING` is never set or checkpointed.
6. **Logic Step**: In `_check_and_finalize_if_complete`, `completed_searches >= expected_searches` is True, `0 >= 0` is True for parses, and `0 >= 0` is True for matches.
7. **Logic Step**: `_finalize_workflow` is invoked immediately, writing `COMPLETED` to SQLite.
8. **Conclusion**: When 0 jobs exist, the pipeline bypasses Stage 3 and Stage 4 completely in SQLite, transitioning directly from Stage 2 (`STAGE_2_JOB_DISCOVERY`) to `COMPLETED`. This violates the strict acceptance requirement to verify that `WorkflowState` transitions through all 5 stages.

### 2.3 Verification of Passing Fallbacks
1. **LocalMessageBroker Concurrency**: `tests/test_stress_broker_concurrency.py` proved that when testing the broker in isolation without competing `MasterAgent` instances, 10 concurrent threads publishing 100 messages each (1,000 total messages) across 1 queue achieved 100% consumption with 0 message loss, valid UUID message IDs, and proper envelope formatting. Multi-queue concurrency (5 queues, 50 messages each) also passed cleanly.
2. **SQLite Table Creation & Concurrency**: `tests/test_stress_sqlite_and_chroma.py` proved that `init_db()` correctly creates all tables (`workflows`, `job_listings`, `match_results`) with columns `updated_at` and `passed_prefilter`. 20 concurrent threads inserting 10 records each (200 records) completed with 0 database lock errors under SQLite WAL mode/in-process execution.
3. **ChromaDB Disk Persistence**: `tests/test_stress_sqlite_and_chroma.py` proved that 3072-dimensional embeddings inserted via `get_or_create_collection` persisted to disk in `./chroma_data/chroma.sqlite3`. A separate, newly instantiated `chromadb.PersistentClient(path="./chroma_data")` successfully retrieved the vector, documents, and metadatas, confirming persistent local disk storage.

---

## 3. Caveats

1. **Test Environment**: Verification was executed entirely on the local host machine using SQLite, LocalMessageBroker, and ChromaDB embedded client. Pre-existing external RabbitMQ and PostgreSQL containers were deliberately not running, matching the mandate to test local raw-machine fallbacks.
2. **Gemini API Key Absence**: LLM calls fell back to deterministic mock generators as expected in offline development mode (`GEMINI_API_KEY is not configured or quota is exhausted`).
3. **No Direct Production Code Modifications**: In strict adherence to the Review-Only constraint, Challenger M1-2 did NOT modify implementation files (`core/*.py` or `agents/*.py`). All failures are reported as findings.

---

## 4. Conclusion

While the low-level raw-machine fallbacks (`LocalMessageBroker` concurrency, SQLite table creation & concurrent CRUD, and ChromaDB 3072-dim disk persistence) are functionally solid in isolated unit tests, the **Master Agent 5-stage DAG Orchestrator fails critical empirical stress tests**:

1. **Deadlock / Message Loss Vulnerability**: `LocalMessageBroker` does not manage consumer lifecycles. Multiple `MasterAgent` instances create zombie consumer threads on `master_queue` that silently swallow messages intended for other workflow IDs, causing workflows to deadlock.
2. **Workflow State Isolation**: `MasterAgent` relies strictly on in-memory `self.active_workflows` without SQLite state fallback, making it incapable of handling distributed or multi-instance message delivery.
3. **Stage Checkpointing Violation**: Under 0-job boundary conditions, Stages 3 (`STAGE_3_JOB_PARSING`) and 4 (`STAGE_4_MATCHING`) are skipped entirely in SQLite rather than checkpointed as completed with 0 items.
4. **Pre-filter Gating Math Failure**: `test_forensic_audit.py` failed due to direct module-level imports of `get_embedding` in `MatchingAgent`, which prevented test harness overrides and led to disqualified jobs passing the pre-filter.

**Verdict: REQUEST_CHANGES**

### Required Action Items for Worker / Orchestrator:
1. **LocalMessageBroker Lifecycle Management**:
   - Add an `unsubscribe(queue_name, callback)` or `clear_consumers(queue_name)` method to `LocalMessageBroker`.
   - Ensure that calling `agent.stop()` or re-running agents cleans up previous consumer threads.
2. **MasterAgent Untracked Message Handling & State Sharing**:
   - When `MasterAgent` receives a message for an untracked `workflow_id` on `master_queue`, it should NOT simply discard it if other consumers might handle it, or better: make `MasterAgent.active_workflows` a class-level shared dictionary or query/hydrate state from SQLite `WorkflowState`.
   - Better yet, support unique response routing keys (e.g. `master_queue_<workflow_id>`) or consumer correlation filtering.
3. **Consistent 5-Stage Checkpointing under 0-Job Boundary Conditions**:
   - In `MasterAgent.process_message`, when `raw_jobs` is empty, explicitly transition to `STAGE_3_JOB_PARSING` with `count=0`, checkpoint to SQLite, then transition to `STAGE_4_MATCHING` with `count=0`, checkpoint to SQLite, and finally transition to `COMPLETED`. This guarantees that SQLite records all 5 stages in sequence regardless of job count.
4. **MatchingAgent Mockability & Pre-filter Strictness**:
   - Allow dependency injection of embedding function in `MatchingAgent` or import `llm` module dynamically so testing pre-filter gating is reliable and does not trigger fallback embeddings unexpectedly.

---

## 5. Verification Method

To independently verify these findings, run:
```bash
pytest tests/test_stress_broker_concurrency.py tests/test_stress_sqlite_and_chroma.py tests/test_stress_dag_orchestration.py tests/test_stage_checkpointing_sqlite.py tests/test_forensic_audit.py
```

### Expected Results:
- `tests/test_stress_broker_concurrency.py`: 3 passed.
- `tests/test_stress_sqlite_and_chroma.py`: 4 passed.
- `tests/test_stress_dag_orchestration.py`: 5 failed (timeouts / deadlocks due to competing consumers).
- `tests/test_stage_checkpointing_sqlite.py`: 2 failed (stage skip and deadlock).
- `tests/test_forensic_audit.py`: 1 failed (`test_forensic_check_2_stage_1_prefilter_math_and_gating`).

### Invalidation Conditions:
This report and its `REQUEST_CHANGES` verdict will be invalidated only when:
1. `LocalMessageBroker` consumer cleanup is implemented and `test_stress_dag_orchestration.py` passes 5/5 without deadlocks.
2. `test_stage_checkpointing_sqlite.py` passes 2/2 verifying all 5 stages are checkpointed to SQLite even when 0 jobs are found.
3. All 52 tests in the suite pass with 100% pass rate (`0 failed, 52 passed`).
