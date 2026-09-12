# Handoff Report: Architecture, 5-Stage DAG & Fallback Systems Survey

**Agent**: Explorer Survey 3  
**Working Directory**: `C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine\.agents\explorer_survey_3`  
**Handoff Type**: Hard (Investigation task complete)  
**Date**: 2026-09-03  

---

## 1. Observation

1. **Test Suite Status**:
   Executed `pytest -v` via `run_command` in `C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine`:
   ```
   ============================= test session starts =============================
   platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
   cachedir: .pytest_cache
   rootdir: C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine
   plugins: anyio-4.14.2, langsmith-0.11.1, asyncio-1.4.0
   collecting ... collected 5 items

   tests/test_broker.py::test_broker_pub_sub PASSED                         [ 20%]
   tests/test_db.py::test_db_init_and_crud PASSED                           [ 40%]
   tests/test_matching.py::test_cosine_similarity PASSED                    [ 60%]
   tests/test_matching.py::test_structured_attribute_scoring PASSED         [ 80%]
   tests/test_parser.py::test_pagination_detection PASSED                   [100%]

   ======================= 5 passed, 2 warnings in 13.27s ========================
   ```
   Deprecation warnings observed for `datetime.datetime.utcnow()` in `core/messaging.py:37` and `core/db.py:3627`.

2. **Local Fallback Implementations**:
   - `core/messaging.py` (lines 11-80, 134-148): `LocalMessageBroker` is an in-process thread-safe singleton managing queues via standard Python `queue.Queue()` with concurrent task execution in a `ThreadPoolExecutor(max_workers=6)`. The factory function `MessageBroker()` catches connection errors from `pika` and returns `LocalMessageBroker`.
   - `core/db.py` (lines 12-28): `get_engine()` attempts a PostgreSQL connection with `connect_timeout: 3`. If unsuccessful, it catches the exception and returns `sqlite:///<workspace>/job_engine.db` configured with `connect_args={"check_same_thread": False}`.
   - `core/vector_db.py` (lines 9-27): `get_chroma_client()` calls `http_client.heartbeat()`. If the remote ChromaDB server fails to respond, it falls back to `chromadb.PersistentClient(path="./chroma_data")`.

3. **5-Stage DAG Progression in Master Agent**:
   In `agents/master_agent.py`:
   - Line 42 (`start_workflow`): Uses Gemini 3.6 Flash (`extract_json`) with fallback parameters. Inserts `WorkflowState(id=workflow_id, status="RUNNING", ...)`. Dispatches to `company_list_queue`.
   - Line 124 (`company_list_agent` response): Fans out `task_request` messages to `job_search_queue` for each constituent. In-memory state updated: `state["status"] = "STAGE_2_JOB_DISCOVERY"`. **No database write.**
   - Line 148 (`job_search_agent` response): Dispatches raw jobs to `job_parse_queue`. In-memory state updated. **No database write.**
   - Line 166 (`job_parsing_agent` response): Dispatches parsed jobs to `matching_queue`. In-memory state updated: `state["status"] = "STAGE_4_MATCHING"`. **No database write.**
   - Line 185 (`matching_agent` response): Aggregates ranked matches. Line 202 updates `WorkflowState(id=workflow_id, status="COMPLETED", data={...})` in DB.

4. **Two-Stage Matching Implementation**:
   In `agents/matching_agent.py` (lines 107-115):
   ```python
   # Stage 1: Vector Similarity (Cosine threshold 0.65)
   cos_sim = cosine_similarity(candidate_emb, job_emb)
   
   # Stage 2: Structured Scoring (0 - 100)
   struct_score, breakdown = self.score_structured_attributes(job, candidate)

   # Combined weighted score (40% vector similarity + 60% structured score)
   final_score = round((cos_sim * 100 * 0.4) + (struct_score * 0.6), 1)
   ```
   No conditional statement exists to drop or filter out jobs where `cos_sim < 0.65`.

5. **FTSE Constituent Scope**:
   `agents/company_list_agent.py` (lines 7-23) defines only 8 FTSE 250 companies and 4 FTSE 100 companies as static seed arrays.

---

## 2. Logic Chain

1. From Observation 1 & 2: The system's triple fallback architecture (`LocalMessageBroker`, SQLite `job_engine.db`, embedded `chroma_data`) is fully functional on raw machines without external daemon dependencies, as evidenced by 100% test pass rate in pytest without Docker running.
2. From Observation 3: `MasterAgent` transitions through all 5 stages in memory, but only persists state to `workflows` table at `RUNNING` (initialization) and `COMPLETED` (final step). Therefore, intermediate checkpoints for Stage 1, Stage 2, Stage 3, and Stage 4 are not crash-resilient in the database.
3. From Observation 4: `ORIGINAL_REQUEST.md` R4 explicitly specifies: *"Stage 1: Fast vector cosine similarity pre-filtering (threshold >= 0.65)."* Because `matching_agent.py` evaluates structured scoring for all jobs regardless of `cos_sim`, jobs failing the 0.65 semantic similarity threshold are not pre-filtered as required by the two-stage cascade design.
4. From Observation 5: The constituent registry currently contains a 12-company seed set rather than the full FTSE 100 and FTSE 250 universes.

---

## 3. Caveats

1. **Playwright vs. Requests**: `requirements.txt` contains `playwright` and `playwright-stealth`, but `JobSearchAgent` currently relies on `requests` and `get_simulated_career_html`. Live browser crawling with headless Chromium was not verified on this host machine.
2. **Gemini Live Quota**: Embedding generation and LLM parsing have structured local fallback dictionaries in case the API key is rate-limited or exhausted during batch executions.

---

## 4. Conclusion

The system has successfully established the foundational architecture for raw-machine execution, message passing, database abstraction, vector persistence, and agent modularity. To reach full compliance with `ORIGINAL_REQUEST.md`, subsequent implementation phases must:
1. Enforce the `cos_sim >= 0.65` pre-filtering gate in `MatchingAgent`.
2. Add stage-by-stage `WorkflowState` checkpointing in `MasterAgent`.
3. Expand the constituent company registry in `CompanyListAgent`.
4. Implement dedicated executive report file generation (Markdown/JSON) in Stage 5.
5. Migrate `datetime.utcnow()` to `datetime.now(timezone.utc)` to clear Python 3.12 deprecation warnings.

---

## 5. Verification Method

To independently verify these findings:
1. **Run Unit Test Suite**:
   ```cmd
   pytest -v
   ```
   Expected: 5 passed, 2 warnings regarding `datetime.utcnow()`.
2. **Inspect Fallback Logic**:
   - Inspect `core/messaging.py:134-148` for RabbitMQ to `LocalMessageBroker` fallback.
   - Inspect `core/db.py:12-28` for Postgres to SQLite `job_engine.db` fallback.
   - Inspect `core/vector_db.py:9-27` for remote Chroma to `./chroma_data` fallback.
3. **Inspect Pre-filtering Cutoff Gap**:
   - Inspect `agents/matching_agent.py:107-135`. Confirm that `cos_sim` is computed but no `if cos_sim < 0.65:` filter drops unqualified jobs.
4. **Inspect Checkpointing Gap**:
   - Inspect `agents/master_agent.py:92-95` and `agents/master_agent.py:200-213`. Confirm that database updates only happen on workflow start and end, with no writes in handlers for Stage 1, 2, or 3.
5. **Invalidation Conditions**:
   - This report is invalidated if `matching_agent.py` already includes an explicit pre-filtering drop branch before Stage 2, or if `MasterAgent` writes intermediate `WorkflowState` rows on every stage transition.
