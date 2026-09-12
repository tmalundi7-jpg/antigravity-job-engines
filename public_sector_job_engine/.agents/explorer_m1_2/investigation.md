# Investigation Report: 5-Stage DAG State Machine, Checkpointing Strategy & Deprecation Remediation

**Explorer**: M1-2  
**Milestone**: Milestone 1 — Engine Hardening & Two-Stage Matching  
**Target Files**: `agents/master_agent.py`, `core/db.py`, `core/messaging.py`, `agents/job_parsing_agent.py`, `agents/job_search_agent.py`  
**Working Directory**: `C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine\.agents\explorer_m1_2`  
**Date**: 2026-09-03  

---

## 1. Executive Summary

This investigation resolves three critical architectural vulnerabilities in the multi-agent job search and matching engine:
1. **Completion Counting Bug in `MasterAgent`**: Investigated the premature completion and deadlock vulnerability in `agents/master_agent.py` lines 191–197 (`len(state["ranked_matches"]) >= dispatched`). Formulated an accurate 3-stage fan-out/fan-in counting architecture with a centralized evaluation method (`_check_and_finalize_if_complete`) that tracks both batch-level and item-level progress across the DAG.
2. **Intermediate Database Checkpointing Across 5 Stages**: Currently, `WorkflowState` is only persisted twice: once at initiation (`RUNNING`) and once at termination (`COMPLETED`). Designed an intermediate checkpointing strategy using a thread-safe helper `checkpoint_workflow()` in `core/db.py` and updating `WorkflowState` across all 5 stages (`STAGE_1_COMPANY_LIST`, `STAGE_2_JOB_DISCOVERY`, `STAGE_3_JOB_PARSING`, `STAGE_4_MATCHING`, and `COMPLETED`), adding an `updated_at` timestamp.
3. **Audit of Deprecated `datetime.utcnow()`**: Identified all 9 occurrences across 5 files (`core/messaging.py`, `core/db.py`, `agents/master_agent.py`, `agents/job_parsing_agent.py`, and `agents/job_search_agent.py`) causing Python 3.12 deprecation warnings during test execution. Provided exact drop-in replacements using `datetime.now(timezone.utc)` and callable lambda defaults for SQLAlchemy columns.

---

## 2. Investigation 1: Completion Counting Bug in `agents/master_agent.py`

### 2.1 Code Analysis & Observation
In `agents/master_agent.py`:
- **Line 83-84**: Initial workflow state:
  ```python
  "expected_searches": 0,
  "completed_searches": 0,
  ```
- **Line 126-127** (Stage 1 Response from `company_list_agent`):
  ```python
  companies = payload.get("companies", [])
  state["companies"] = companies
  state["expected_searches"] = len(companies)
  state["status"] = "STAGE_2_JOB_DISCOVERY"
  ```
- **Line 148-164** (Stage 2 Response from `job_search_agent`):
  ```python
  raw_jobs = payload.get("raw_jobs", [])
  state["raw_jobs_collected"].extend(raw_jobs)
  state["completed_searches"] += 1

  # Once search tasks return raw jobs, dispatch for parsing
  if raw_jobs:
      state["dispatched_parses"] = state.get("dispatched_parses", 0) + 1
      self.broker.publish(
          queue_name="job_parse_queue",
          payload={"raw_jobs": raw_jobs},
          source=self.name,
          target="job_parsing_agent",
          msg_type="task_request",
          correlation_id=workflow_id
      )
  ```
- **Line 166-182** (Stage 3 Response from `job_parsing_agent`):
  ```python
  parsed_jobs = payload.get("parsed_jobs", [])
  state["parsed_jobs"].extend(parsed_jobs)
  state["status"] = "STAGE_4_MATCHING"
  self.broker.publish(
      queue_name="matching_queue",
      payload={
          "candidate": state["candidate"],
          "parsed_jobs": parsed_jobs
      },
      source=self.name,
      target="matching_agent",
      msg_type="task_request",
      correlation_id=workflow_id
  )
  ```
- **Line 185-197** (Stage 4 Response from `matching_agent`):
  ```python
  ranked_matches = payload.get("ranked_matches", [])
  state["ranked_matches"].extend(ranked_matches)
  state["ranked_matches"].sort(key=lambda x: x["final_score"], reverse=True)

  # Check if all dispatched searches and parses have finished
  dispatched = state.get("dispatched_parses", state["expected_searches"])
  if state["completed_searches"] >= state["expected_searches"] and len(state["ranked_matches"]) >= dispatched:
      state["status"] = "COMPLETED"
      state["completed"] = True
      ...
  ```

### 2.2 Root Cause & Failure Modes

#### Failure Mode 1: Premature Completion & Job Loss (Multiple Jobs per Company)
- **Unit Mismatch**: `dispatched` is the number of parse batch messages dispatched (at most equal to the number of companies, e.g. 8). Meanwhile, `len(state["ranked_matches"])` is the total number of **individual matched job positions** returned by `matching_agent`.
- **Scenario**:
  1. `company_list_agent` returns 8 companies (`expected_searches = 8`).
  2. All 8 searches return raw jobs. Hence, 8 parse batches are dispatched (`dispatched_parses = 8`, so `dispatched = 8`).
  3. Company 1 yields 5 job listings; Company 2 yields 4 job listings.
  4. The background `ThreadPoolExecutor` processes Company 1 and Company 2 parsing and matching quickly.
  5. When Company 1 and Company 2 finish matching, `state["ranked_matches"]` contains $5 + 4 = 9$ jobs.
  6. The condition `state["completed_searches"] >= 8` (True) and `len(state["ranked_matches"]) >= 8` ($9 \ge 8$, True) evaluates to **TRUE**!
  7. Master declares `state["status"] = "COMPLETED"`, sets `state["completed"] = True`, and saves to the database.
  8. **Impact**: Companies 3, 4, 5, 6, 7, and 8 are still in flight or in queues. When their results arrive, the workflow is already closed out! Top jobs from those 6 companies are discarded, resulting in incomplete search coverage and invalid ranking.

#### Failure Mode 2: Deadlock / Permanent Hang (Zero Jobs Found)
- **Scenario**:
  1. A search query for a niche role across the 8 companies returns 0 raw jobs for every company (`raw_jobs == []`).
  2. Because `raw_jobs` is empty, line 154 (`if raw_jobs:`) is never entered.
  3. `state["dispatched_parses"]` is never created in `state`.
  4. In line 192, `dispatched = state.get("dispatched_parses", state["expected_searches"])` evaluates to `state["expected_searches"] = 8`.
  5. But because 0 jobs were found, no matching was ever dispatched; `len(state["ranked_matches"])` is 0.
  6. Line 193: `0 >= 8` is **False**.
  7. The workflow never completes. It hangs indefinitely until `run_local_engine.py` hits the timeout (45s or 60s) and fails.

#### Failure Mode 3: Missing Inter-Stage Synchronization Counters
- `dispatched_parses` was tracked, but `completed_parses` was never tracked.
- `dispatched_matches` and `completed_matches` were never tracked at all.
- As a result, the master agent cannot determine whether parsing tasks are still running before dispatching matching, or whether matching tasks are still in flight.

### 2.3 Proposed Fix: 3-Stage Balanced Counter Pair Architecture

To guarantee exact completion detection under all conditions (single job, multiple jobs per company, zero jobs, varying thread latencies), the workflow state must track three balanced counter pairs corresponding to each asynchronous DAG stage:

| Stage | Dispatched / Expected Counter | Completed Counter | Completion Condition |
|---|---|---|---|
| **Stage 2: Job Search** | `state["expected_searches"]` (int) | `state["completed_searches"]` (int) | `completed_searches >= expected_searches` |
| **Stage 3: Job Parsing** | `state["dispatched_parses"]` (int) | `state["completed_parses"]` (int) | `completed_parses >= dispatched_parses` |
| **Stage 4: Matching** | `state["dispatched_matches"]` (int) | `state["completed_matches"]` (int) | `completed_matches >= dispatched_matches` |

Additionally, track item counts for telemetry and reporting:
- `state["total_raw_jobs"] = len(state["raw_jobs_collected"])`
- `state["total_parsed_jobs"] = len(state["parsed_jobs"])`
- `state["total_matched_jobs"] = len(state["ranked_matches"])`

#### Centralized Completion Evaluator: `_check_and_finalize_if_complete`
Instead of only checking completion inside the `matching_agent` response handler, implement a centralized evaluator method:

```python
def _check_and_finalize_if_complete(self, workflow_id: str):
    state = self.active_workflows.get(workflow_id)
    if not state or state.get("completed"):
        return

    searches_done = state["completed_searches"] >= state["expected_searches"]
    parses_done = state["completed_parses"] >= state["dispatched_parses"]
    matches_done = state["completed_matches"] >= state["dispatched_matches"]

    if searches_done and parses_done and matches_done:
        self._finalize_workflow(workflow_id)
```

This evaluator is invoked:
1. After handling a `job_search_agent` response (handles the zero-jobs scenario immediately when `expected_searches` are satisfied and `dispatched_parses == 0`).
2. After handling a `job_parsing_agent` response (handles cases where parsing produced 0 valid listings and no matches are dispatched).
3. After handling a `matching_agent` response (handles standard match batch completion).

---

## 3. Investigation 2: Intermediate Database Checkpointing Strategy

### 3.1 Code Analysis & Observation
In `core/db.py`:
```python
class WorkflowState(Base):
    __tablename__ = 'workflows'
    id = Column(String, primary_key=True)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    data = Column(JSON)
```
In `agents/master_agent.py`:
- Line 93: `db.merge(WorkflowState(id=workflow_id, status="RUNNING", data={"goal": goal, "params": params}))`
- Line 202: `db.merge(WorkflowState(id=workflow_id, status="COMPLETED", data={...}))`
- **Deficiency**: During the intermediate stages (`STAGE_1_COMPANY_LIST`, `STAGE_2_JOB_DISCOVERY`, `STAGE_3_JOB_PARSING`, `STAGE_4_MATCHING`), the database is **never updated**.
- An external inspector, health check, or UI reading `job_engine.db` cannot determine which stage the workflow is in, how many companies or jobs have been collected, or whether the workflow is stalled.

### 3.2 Enhanced Database Helper in `core/db.py`
Add `checkpoint_workflow` in `core/db.py` to ensure thread-safe, consistent updates and error resilience without repetitive boilerplate:

```python
def checkpoint_workflow(workflow_id: str, status: str, data: dict = None) -> bool:
    """
    Persist or update intermediate workflow state in the database.
    Thread-safe and exception-resilient for SQLite and PostgreSQL.
    """
    try:
        with SessionLocal() as db:
            record = db.query(WorkflowState).filter(WorkflowState.id == workflow_id).first()
            now_utc = datetime.now(timezone.utc)
            if record:
                record.status = status
                if data is not None:
                    existing_data = dict(record.data or {})
                    existing_data.update(data)
                    record.data = existing_data
                if hasattr(record, "updated_at"):
                    record.updated_at = now_utc
            else:
                record = WorkflowState(
                    id=workflow_id,
                    status=status,
                    data=data or {},
                    created_at=now_utc,
                    updated_at=now_utc if hasattr(WorkflowState, "updated_at") else None
                )
                db.add(record)
            db.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to checkpoint workflow [{workflow_id}] status='{status}': {e}")
        return False
```

Also add `updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)` to `WorkflowState`.

### 3.3 Stage-by-Stage Checkpoint Payloads

#### Stage 1: Company Discovery (`STAGE_1_COMPANY_LIST`)
- **Trigger**: `master_agent.start_workflow(goal, candidate_profile)`
- **Status Column**: `"STAGE_1_COMPANY_LIST"`
- **Data Payload**:
  ```python
  {
      "workflow_id": workflow_id,
      "stage": "STAGE_1_COMPANY_LIST",
      "stage_name": "Company Discovery",
      "goal": goal,
      "params": params,
      "candidate_id": state["candidate"].get("id"),
      "candidate_name": state["candidate"].get("name"),
      "started_at": state["start_time"]
  }
  ```

#### Stage 2: Job Discovery (`STAGE_2_JOB_DISCOVERY`)
- **Trigger**: `master_agent` receives `task_response` from `company_list_agent`
- **Status Column**: `"STAGE_2_JOB_DISCOVERY"`
- **Data Payload**:
  ```python
  {
      "stage": "STAGE_2_JOB_DISCOVERY",
      "stage_name": "Job Discovery",
      "companies_count": len(companies),
      "companies": [c.get("name") for c in companies],
      "expected_searches": len(companies),
      "completed_searches": 0,
      "updated_at": datetime.now(timezone.utc).isoformat()
  }
  ```

#### Stage 3: Job Parsing (`STAGE_3_JOB_PARSING`)
- **Trigger**: `master_agent` receives first `raw_jobs` from `job_search_agent` and dispatches to `job_parsing_agent`
- **Status Column**: `"STAGE_3_JOB_PARSING"`
- **Data Payload**:
  ```python
  {
      "stage": "STAGE_3_JOB_PARSING",
      "stage_name": "Job Parsing & Schema Extraction",
      "total_raw_jobs": len(state["raw_jobs_collected"]),
      "completed_searches": state["completed_searches"],
      "expected_searches": state["expected_searches"],
      "dispatched_parses": state["dispatched_parses"],
      "completed_parses": state["completed_parses"],
      "updated_at": datetime.now(timezone.utc).isoformat()
  }
  ```

#### Stage 4: Candidate Matching (`STAGE_4_MATCHING`)
- **Trigger**: `master_agent` receives `task_response` from `job_parsing_agent` and dispatches to `matching_agent`
- **Status Column**: `"STAGE_4_MATCHING"`
- **Data Payload**:
  ```python
  {
      "stage": "STAGE_4_MATCHING",
      "stage_name": "Two-Stage Candidate Matching",
      "total_parsed_jobs": len(state["parsed_jobs"]),
      "completed_parses": state["completed_parses"],
      "dispatched_matches": state["dispatched_matches"],
      "completed_matches": state["completed_matches"],
      "updated_at": datetime.now(timezone.utc).isoformat()
  }
  ```

#### Stage 5: Executive Reporting / Completed (`COMPLETED`)
- **Trigger**: All searches, parses, and matchings satisfy completion criteria
- **Status Column**: `"COMPLETED"`
- **Data Payload**:
  ```python
  {
      "stage": "COMPLETED",
      "stage_name": "Executive Reporting & Recommendation",
      "total_companies": len(state["companies"]),
      "total_raw_jobs": len(state["raw_jobs_collected"]),
      "total_parsed_jobs": len(state["parsed_jobs"]),
      "total_matched": len(state["ranked_matches"]),
      "top_match": state["ranked_matches"][0] if state["ranked_matches"] else None,
      "top_recommendations": state["ranked_matches"][:5],
      "completed_at": state["completed_at"],
      "duration_seconds": round(duration, 2)
  }
  ```

---

## 4. Investigation 3: Python 3.12 `datetime.utcnow()` Deprecation Audit

### 4.1 Background
In Python 3.12, `datetime.datetime.utcnow()` was officially deprecated (PEP 614/Python 3.12 release notes):
> *`datetime.datetime.utcnow()` and `datetime.datetime.utcfromtimestamp()` are deprecated and scheduled for removal. Use timezone-aware objects to represent datetimes in UTC: `datetime.datetime.now(datetime.timezone.utc)` or `datetime.datetime.now(datetime.UTC)`.*

During pytest execution (`pytest tests/test_broker.py tests/test_db.py`), 2 `DeprecationWarning`s were directly observed:
```
tests/test_broker.py::test_broker_pub_sub
  core/messaging.py:37: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    "timestamp": datetime.utcnow().isoformat(),

tests/test_db.py::test_db_init_and_crud
  .../sqlalchemy/sql/schema.py:3627: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version.
```

### 4.2 Comprehensive Inventory of All 9 Occurrences

| # | File | Line # | Current Deprecated Code | Modern Replacement |
|---|---|---|---|---|
| 1 | `agents/job_parsing_agent.py` | Line 54 | `"posted_date": datetime.utcnow().date().isoformat()` | `"posted_date": datetime.now(timezone.utc).date().isoformat()` |
| 2 | `agents/job_search_agent.py` | Line 113 | `"scraped_at": datetime.utcnow().isoformat(),` | `"scraped_at": datetime.now(timezone.utc).isoformat(),` |
| 3 | `agents/master_agent.py` | Line 85 | `"start_time": datetime.utcnow().isoformat(),` | `"start_time": datetime.now(timezone.utc).isoformat(),` |
| 4 | `agents/master_agent.py` | Line 196 | `state["completed_at"] = datetime.utcnow().isoformat()` | `state["completed_at"] = datetime.now(timezone.utc).isoformat()` |
| 5 | `core/db.py` | Line 37 | `created_at = Column(DateTime, default=datetime.utcnow)` | `created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))` |
| 6 | `core/db.py` | Line 51 | `created_at = Column(DateTime, default=datetime.utcnow)` | `created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))` |
| 7 | `core/db.py` | Line 63 | `created_at = Column(DateTime, default=datetime.utcnow)` | `created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))` |
| 8 | `core/messaging.py` | Line 37 | `"timestamp": datetime.utcnow().isoformat(),` | `"timestamp": datetime.now(timezone.utc).isoformat(),` |
| 9 | `core/messaging.py` | Line 96 | `"timestamp": datetime.utcnow().isoformat(),` | `"timestamp": datetime.now(timezone.utc).isoformat(),` |

### 4.3 Technical Rule for SQLAlchemy Column Defaults
In SQLAlchemy, passing `default=datetime.now(timezone.utc)` without a callable executes `now()` **once at module load time**, causing all records created later to share an identical, stale creation timestamp.  
Using a callable:
```python
default=lambda: datetime.now(timezone.utc)
```
or a function definition:
```python
def utc_now():
    return datetime.now(timezone.utc)
...
created_at = Column(DateTime, default=utc_now)
```
guarantees that a fresh, timezone-aware UTC datetime is calculated on each insert and resolves the SQLAlchemy `DeprecationWarning` completely.

---

## 5. Detailed Code Modifications & Line-by-Line Diffs

### 5.1 Modifications to `core/messaging.py`
**File**: `core/messaging.py`  
**Lines 6, 37, 96**:
- Add `timezone` to `from datetime import datetime, timezone`.
- Line 37: change `datetime.utcnow().isoformat()` to `datetime.now(timezone.utc).isoformat()`.
- Line 96: change `datetime.utcnow().isoformat()` to `datetime.now(timezone.utc).isoformat()`.

```diff
--- a/core/messaging.py
+++ b/core/messaging.py
@@ -6,1 +6,1 @@
-from datetime import datetime
+from datetime import datetime, timezone
@@ -37,1 +37,1 @@
-            "timestamp": datetime.utcnow().isoformat(),
+            "timestamp": datetime.now(timezone.utc).isoformat(),
@@ -96,1 +96,1 @@
-            "timestamp": datetime.utcnow().isoformat(),
+            "timestamp": datetime.now(timezone.utc).isoformat(),
```

---

### 5.2 Modifications to `core/db.py`
**File**: `core/db.py`  
**Changes**:
1. Line 3: import `timezone`: `from datetime import datetime, timezone`.
2. Lines 37, 51, 63: replace `default=datetime.utcnow` with `default=lambda: datetime.now(timezone.utc)`.
3. Line 38: add `updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)` to `WorkflowState`.
4. Add function `checkpoint_workflow(workflow_id: str, status: str, data: dict = None) -> bool`.

```diff
--- a/core/db.py
+++ b/core/db.py
@@ -3,1 +3,1 @@
-from datetime import datetime
+from datetime import datetime, timezone
@@ -37,1 +37,2 @@
-    created_at = Column(DateTime, default=datetime.utcnow)
+    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
+    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)
@@ -51,1 +52,1 @@
-    created_at = Column(DateTime, default=datetime.utcnow)
+    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
@@ -63,1 +64,1 @@
-    created_at = Column(DateTime, default=datetime.utcnow)
+    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
@@ -67,2 +68,29 @@
     Base.metadata.create_all(bind=engine)
     logger.info("Database schema initialized.")
+
+def checkpoint_workflow(workflow_id: str, status: str, data: dict = None) -> bool:
+    """
+    Persist or update intermediate workflow state in the database.
+    Thread-safe and exception-resilient for SQLite and PostgreSQL.
+    """
+    try:
+        with SessionLocal() as db:
+            record = db.query(WorkflowState).filter(WorkflowState.id == workflow_id).first()
+            now_utc = datetime.now(timezone.utc)
+            if record:
+                record.status = status
+                if data is not None:
+                    existing_data = dict(record.data or {})
+                    existing_data.update(data)
+                    record.data = existing_data
+                record.updated_at = now_utc
+            else:
+                record = WorkflowState(
+                    id=workflow_id,
+                    status=status,
+                    data=data or {},
+                    created_at=now_utc,
+                    updated_at=now_utc
+                )
+                db.add(record)
+            db.commit()
+            return True
+    except Exception as e:
+        logger.error(f"Failed to checkpoint workflow [{workflow_id}] status='{status}': {e}")
+        return False
```

---

### 5.3 Modifications to `agents/master_agent.py`
**File**: `agents/master_agent.py`  
**Changes**:
1. Line 5: import `timezone`: `from datetime import datetime, timezone`.
2. Line 8: import `checkpoint_workflow`: `from core.db import SessionLocal, WorkflowState, checkpoint_workflow`.
3. Lines 83-86: Initialize the balanced counter pairs in `workflow_state`:
   - `"expected_searches": 0`
   - `"completed_searches": 0`
   - `"dispatched_parses": 0`
   - `"completed_parses": 0`
   - `"dispatched_matches": 0`
   - `"completed_matches": 0`
   - `"start_time": datetime.now(timezone.utc).isoformat()`
4. Lines 90-97: Stage 1 DB Checkpoint:
   - Call `checkpoint_workflow(workflow_id, "STAGE_1_COMPANY_LIST", ...)`
5. Lines 126-130: Stage 2 Transition & DB Checkpoint:
   - Set `state["status"] = "STAGE_2_JOB_DISCOVERY"`
   - Call `checkpoint_workflow(workflow_id, "STAGE_2_JOB_DISCOVERY", ...)`
6. Lines 148-164: Stage 3 Parsing Dispatch & Checkpoint:
   - Increment `state["dispatched_parses"] += 1`
   - Update `state["status"] = "STAGE_3_JOB_PARSING"`
   - Call `checkpoint_workflow(workflow_id, "STAGE_3_JOB_PARSING", ...)`
   - Call `self._check_and_finalize_if_complete(workflow_id)` at end of search response
7. Lines 166-183: Stage 4 Matching Dispatch & Checkpoint:
   - Increment `state["completed_parses"] += 1`
   - If `parsed_jobs`: increment `state["dispatched_matches"] += 1`, update `state["status"] = "STAGE_4_MATCHING"`, call `checkpoint_workflow`, publish to `matching_queue`
   - Call `self._check_and_finalize_if_complete(workflow_id)`
8. Lines 185-214: Stage 4 Response & Completion Evaluation:
   - Increment `state["completed_matches"] += 1`
   - Extend `state["ranked_matches"]`
   - Call `self._check_and_finalize_if_complete(workflow_id)`
9. Implement helper methods:
   - `_finalize_workflow(self, workflow_id: str)`: marks `COMPLETED`, records `completed_at`, computes duration, checkpoints to DB, stores in `self.completed_reports`.
   - `_check_and_finalize_if_complete(self, workflow_id: str)`: verifies all three counter pairs (`completed_searches >= expected_searches`, `completed_parses >= dispatched_parses`, `completed_matches >= dispatched_matches`).

```diff
--- a/agents/master_agent.py
+++ b/agents/master_agent.py
@@ -5,2 +5,2 @@
-from datetime import datetime
+from datetime import datetime, timezone
 from agents.base import BaseAgent
 from core.llm import extract_json
-from core.db import SessionLocal, WorkflowState
+from core.db import SessionLocal, WorkflowState, checkpoint_workflow
@@ -83,4 +83,8 @@
             "expected_searches": 0,
             "completed_searches": 0,
-            "start_time": datetime.utcnow().isoformat(),
+            "dispatched_parses": 0,
+            "completed_parses": 0,
+            "dispatched_matches": 0,
+            "completed_matches": 0,
+            "start_time": datetime.now(timezone.utc).isoformat(),
             "completed": False
@@ -90,8 +94,15 @@
-        # Persist initial state to Database
-        try:
-            with SessionLocal() as db:
-                db.merge(WorkflowState(id=workflow_id, status="RUNNING", data={"goal": goal, "params": params}))
-                db.commit()
-        except Exception as e:
-            logger.error(f"[{self.name}] Failed to save WorkflowState to DB: {e}")
+        # Stage 1 Checkpoint: Persist initial state to Database
+        checkpoint_workflow(
+            workflow_id=workflow_id,
+            status="STAGE_1_COMPANY_LIST",
+            data={
+                "workflow_id": workflow_id,
+                "stage": "STAGE_1_COMPANY_LIST",
+                "stage_name": "Company Discovery",
+                "goal": goal,
+                "params": params,
+                "candidate_id": workflow_state["candidate"].get("id"),
+                "started_at": workflow_state["start_time"]
+            }
+        )
@@ -128,2 +139,12 @@
             state["status"] = "STAGE_2_JOB_DISCOVERY"
             logger.info(f"[{self.name}] Discovered {len(companies)} companies. Dispatching search tasks...")
+
+            # Stage 2 Checkpoint: Persist discovered companies
+            checkpoint_workflow(
+                workflow_id=workflow_id,
+                status="STAGE_2_JOB_DISCOVERY",
+                data={
+                    "stage": "STAGE_2_JOB_DISCOVERY",
+                    "companies_count": len(companies),
+                    "companies": [c.get("name") for c in companies],
+                    "expected_searches": len(companies),
+                    "updated_at": datetime.now(timezone.utc).isoformat()
+                }
+            )
@@ -154,3 +175,14 @@
             if raw_jobs:
-                state["dispatched_parses"] = state.get("dispatched_parses", 0) + 1
+                state["dispatched_parses"] += 1
+                state["status"] = "STAGE_3_JOB_PARSING"
+                checkpoint_workflow(
+                    workflow_id=workflow_id,
+                    status="STAGE_3_JOB_PARSING",
+                    data={
+                        "stage": "STAGE_3_JOB_PARSING",
+                        "total_raw_jobs": len(state["raw_jobs_collected"]),
+                        "dispatched_parses": state["dispatched_parses"],
+                        "completed_searches": state["completed_searches"],
+                        "updated_at": datetime.now(timezone.utc).isoformat()
+                    }
+                )
@@ -164,1 +196,3 @@
                     correlation_id=workflow_id
                 )
+
+            self._check_and_finalize_if_complete(workflow_id)
@@ -168,3 +202,15 @@
             parsed_jobs = payload.get("parsed_jobs", [])
             state["parsed_jobs"].extend(parsed_jobs)
+            state["completed_parses"] += 1
+
+            if parsed_jobs:
+                state["dispatched_matches"] += 1
+                state["status"] = "STAGE_4_MATCHING"
+                checkpoint_workflow(
+                    workflow_id=workflow_id,
+                    status="STAGE_4_MATCHING",
+                    data={
+                        "stage": "STAGE_4_MATCHING",
+                        "total_parsed_jobs": len(state["parsed_jobs"]),
+                        "dispatched_matches": state["dispatched_matches"],
+                        "completed_parses": state["completed_parses"],
+                        "updated_at": datetime.now(timezone.utc).isoformat()
+                    }
+                )
@@ -183,1 +229,3 @@
                 )
+
+            self._check_and_finalize_if_complete(workflow_id)
@@ -187,28 +235,46 @@
             ranked_matches = payload.get("ranked_matches", [])
             state["ranked_matches"].extend(ranked_matches)
             state["ranked_matches"].sort(key=lambda x: x["final_score"], reverse=True)
+            state["completed_matches"] += 1
             logger.info(f"[{self.name}] Aggregated {len(ranked_matches)} matches (Total so far: {len(state['ranked_matches'])})")
 
-            # Check if all dispatched searches and parses have finished
-            dispatched = state.get("dispatched_parses", state["expected_searches"])
-            if state["completed_searches"] >= state["expected_searches"] and len(state["ranked_matches"]) >= dispatched:
-                state["status"] = "COMPLETED"
-                state["completed"] = True
-                state["completed_at"] = datetime.utcnow().isoformat()
-                logger.info(f"[{self.name}] *** WORKFLOW COMPLETED *** All {len(state['ranked_matches'])} matches scored and aggregated.")
-                
-                # Persist completion to Database
-                try:
-                    with SessionLocal() as db:
-                        db.merge(WorkflowState(
-                            id=workflow_id,
-                            status="COMPLETED",
-                            data={
-                                "total_matched": len(state["ranked_matches"]),
-                                "top_match": state["ranked_matches"][0] if state["ranked_matches"] else None
-                            }
-                        ))
-                        db.commit()
-                except Exception as e:
-                    logger.error(f"[{self.name}] DB completion update error: {e}")
-
-                self.completed_reports[workflow_id] = state
+            self._check_and_finalize_if_complete(workflow_id)
+
+    def _check_and_finalize_if_complete(self, workflow_id: str):
+        state = self.active_workflows.get(workflow_id)
+        if not state or state.get("completed"):
+            return
+
+        searches_done = state["completed_searches"] >= state["expected_searches"]
+        parses_done = state["completed_parses"] >= state["dispatched_parses"]
+        matches_done = state["completed_matches"] >= state["dispatched_matches"]
+
+        if searches_done and parses_done and matches_done:
+            self._finalize_workflow(workflow_id)
+
+    def _finalize_workflow(self, workflow_id: str):
+        state = self.active_workflows[workflow_id]
+        state["status"] = "COMPLETED"
+        state["completed"] = True
+        now_utc = datetime.now(timezone.utc)
+        state["completed_at"] = now_utc.isoformat()
+        logger.info(f"[{self.name}] *** WORKFLOW COMPLETED *** All {len(state['ranked_matches'])} matches scored and aggregated.")
+
+        # Stage 5 Checkpoint: Persist completion to Database
+        checkpoint_workflow(
+            workflow_id=workflow_id,
+            status="COMPLETED",
+            data={
+                "stage": "COMPLETED",
+                "total_companies": len(state["companies"]),
+                "total_raw_jobs": len(state["raw_jobs_collected"]),
+                "total_parsed_jobs": len(state["parsed_jobs"]),
+                "total_matched": len(state["ranked_matches"]),
+                "top_match": state["ranked_matches"][0] if state["ranked_matches"] else None,
+                "top_recommendations": state["ranked_matches"][:5],
+                "completed_at": state["completed_at"]
+            }
+        )
+
+        self.completed_reports[workflow_id] = state
```

---

### 5.4 Modifications to `agents/job_parsing_agent.py`
**File**: `agents/job_parsing_agent.py`  
**Lines 3, 54**:
```diff
--- a/agents/job_parsing_agent.py
+++ b/agents/job_parsing_agent.py
@@ -3,1 +3,1 @@
-from datetime import datetime
+from datetime import datetime, timezone
@@ -54,1 +54,1 @@
-                "posted_date": datetime.utcnow().date().isoformat()
+                "posted_date": datetime.now(timezone.utc).date().isoformat()
```

---

### 5.5 Modifications to `agents/job_search_agent.py`
**File**: `agents/job_search_agent.py`  
**Lines 3, 113**:
```diff
--- a/agents/job_search_agent.py
+++ b/agents/job_search_agent.py
@@ -3,1 +3,1 @@
-from datetime import datetime
+from datetime import datetime, timezone
@@ -113,1 +113,1 @@
-                "scraped_at": datetime.utcnow().isoformat(),
+                "scraped_at": datetime.now(timezone.utc).isoformat(),
```

---

## 6. Verification Strategy & Independent Test Plan

1. **Deprecation Warning Verification**:
   - Run `pytest -W error::DeprecationWarning` or inspect test summary:
   - Ensure `DeprecationWarning: datetime.datetime.utcnow() is deprecated` is 0 across all unit and integration tests.
2. **Database Checkpointing Unit Test**:
   - In `tests/test_db.py`, add `test_checkpoint_workflow()`:
     - Invoke `checkpoint_workflow("wf-test-1", "STAGE_1_COMPANY_LIST", {"goal": "test"})`.
     - Query `WorkflowState` from DB and assert `record.status == "STAGE_1_COMPANY_LIST"`.
     - Transition through `STAGE_2_JOB_DISCOVERY`, `STAGE_3_JOB_PARSING`, `STAGE_4_MATCHING`, and `COMPLETED`.
     - Assert that `record.status` reflects the latest stage and `record.data` contains intermediate telemetry.
3. **DAG Completion Unit & Property Tests**:
   - **Multi-Job Test**: Create simulated search responses where 2 companies return 4 jobs each (8 jobs total, 2 parse batches). Verify all 8 jobs are parsed and matched, and completion occurs only after both match batches finish.
   - **Zero-Job Test**: Create simulated search response where all companies return 0 raw jobs. Verify master marks workflow completed immediately without timeout or hanging.
4. **End-to-End Pipeline Verification**:
   - Execute `run_local_engine.py --goal "Find a Management Accountant in the FTSE 250 in London"`.
   - Verify SQLite table `workflows` contains final status `COMPLETED` and full stage audit trail in `data`.
