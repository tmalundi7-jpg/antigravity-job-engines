# Codebase Survey Report: FTSE Multi-Agent Job Search & Matching Engine

**Surveyor:** Explorer 1  
**Timestamp:** 2026-09-03T01:18:00Z  
**Workspace:** `C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine`  
**Reference Document:** `ORIGINAL_REQUEST.md`

---

## 1. Executive Summary

A comprehensive architectural and functional survey of the **FTSE Multi-Agent Job Search and Matching Engine** was conducted. The codebase implements an asynchronous, distributed multi-agent system capable of running in two distinct modes:
1. **Raw Host Machine Execution**: In-process thread-safe message broker (`LocalMessageBroker`), local SQLite database (`job_engine.db`), and local embedded vector database (`PersistentClient` in `./chroma_data`).
2. **Containerized Cluster Execution**: Docker Compose orchestrating PostgreSQL, RabbitMQ, Redis, ChromaDB, and isolated agent services.

The codebase exhibits high structural modularity, clear separation of concerns, and robust adherence to the multi-agent design pattern. Existing automated tests execute with a **100% pass rate (5/5 passed)** under Python 3.12.10. However, the survey revealed several subtle logic gaps, missing pre-filtering conditions, unhandled failure modes in embedding generation, and Python 3.12 deprecation warnings that must be addressed for full specification compliance.

---

## 2. Codebase Map

### 2.1 File Tree Structure
```
job_search_engine/
├── .env                         # Environment variables (DB, Broker, Gemini API key)
├── config.py                    # Central configuration loader
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Python 3.11-slim container definition
├── docker-compose.yml           # Multi-service container orchestration
├── ORIGINAL_REQUEST.md          # Project specification and acceptance criteria
├── README.md                    # Project overview and usage guide
├── run_local_engine.py          # Native CLI pipeline entrypoint
├── job_engine.db                # SQLite database (auto-generated fallback)
├── chroma_data/                 # Local embedded ChromaDB storage
├── scripts/
│   ├── __init__.py
│   └── init_db.py               # Database table initializer script
├── core/
│   ├── __init__.py
│   ├── db.py                    # SQLAlchemy engine & models (PostgreSQL + SQLite fallback)
│   ├── llm.py                   # Google Gemini API integration (3.6-flash & embedding-2)
│   ├── messaging.py             # Message broker (RabbitMQ + Local in-process fallback)
│   └── vector_db.py             # ChromaDB client (HTTP + local PersistentClient fallback)
├── agents/
│   ├── __init__.py
│   ├── base.py                  # BaseAgent with idempotency & retry mechanics
│   ├── company_list_agent.py    # FTSE constituent lookup agent
│   ├── job_search_agent.py      # Career portal crawler & rate limiter
│   ├── job_parsing_agent.py     # HTML-to-JSON extractor via Gemini
│   ├── matching_agent.py        # Two-stage vector & structured scoring agent
│   └── master_agent.py          # DAG workflow orchestrator & state tracker
└── tests/
    ├── __init__.py
    ├── test_broker.py           # In-process pub/sub verification
    ├── test_db.py               # Database CRUD verification
    ├── test_matching.py         # Vector similarity & structured scoring unit tests
    └── test_parser.py           # HTML pagination placeholder test
```

### 2.2 Models, Classes, and Database Schemas

| Module | Class / Function | Type | Description |
| :--- | :--- | :--- | :--- |
| `core.db` | `WorkflowState` | SQLAlchemy Model | Table `workflows`: Tracks `id`, `status`, `created_at`, `data` (JSON). |
| `core.db` | `JobListing` | SQLAlchemy Model | Table `job_listings`: Tracks `id`, `company`, `title`, `location`, `description`, `requirements` (JSON), `salary_range`, `source_url`, `raw_html`, `created_at`. |
| `core.db` | `MatchResult` | SQLAlchemy Model | Table `match_results`: Tracks `id`, `workflow_id`, `job_id`, `candidate_id`, `similarity_score`, `structured_score`, `final_score`, `reasoning`, `created_at`. |
| `core.db` | `get_engine()`, `init_db()` | Function | Engine factory with 3s PostgreSQL probe; falls back to SQLite `job_engine.db`. |
| `core.messaging` | `LocalMessageBroker` | Class (Singleton) | Thread-safe in-process message broker using `queue.Queue` and `concurrent.futures.ThreadPoolExecutor(max_workers=6)`. |
| `core.messaging` | `RabbitMQBroker` | Class | AMQP message broker using `pika.BlockingConnection` with durable queues and persistent delivery. |
| `core.messaging` | `MessageBroker()` | Factory Function | Probes RabbitMQ; returns `RabbitMQBroker` or falls back to `LocalMessageBroker`. |
| `core.vector_db` | `get_chroma_client()` | Function | Probes ChromaDB HTTP server; falls back to `chromadb.PersistentClient("./chroma_data")`. |
| `core.llm` | `generate_text`, `extract_json`, `get_embedding` | Functions | Calls Gemini `gemini-3.6-flash` and `gemini-embedding-2` with `tenacity` exponential backoff retries. |
| `agents.base` | `BaseAgent` | Abstract Base Class | Provides queue subscription, envelope handling, idempotency deduplication (`processed_messages`), retry wrapper (`_process_with_retry`), and error forwarding. |
| `agents.master_agent` | `MasterAgent` | Agent Class | 5-stage DAG coordinator: initiates workflows, dispatches tasks, collects results, merges checkpoints, generates final leaderboard. |
| `agents.company_list_agent` | `CompanyListAgent` | Agent Class | Returns FTSE 100 / 250 constituent lists and corporate careers URLs. |
| `agents.job_search_agent` | `JobSearchAgent` | Agent Class | Performs requests with domain rate limiting (5 req/sec), browser User-Agent headers, and career HTML generator fallback. |
| `agents.job_parsing_agent` | `JobParsingAgent` | Agent Class | Extracts structured JSON schema from HTML via Gemini `extract_json`, commits `JobListing` records to DB. |
| `agents.matching_agent` | `MatchingAgent` | Agent Class | Computes cosine similarity via `gemini-embedding-2`, calculates 5-attribute structured score, commits `MatchResult` records to DB. |

---

## 3. Test Suite Audit

### 3.1 Test Execution Results
The test suite was executed via `pytest -v`:
```
platform win32 -- Python 3.12.10, pytest-9.1.1
collected 5 items

tests/test_broker.py::test_broker_pub_sub PASSED                         [ 20%]
tests/test_db.py::test_db_init_and_crud PASSED                           [ 40%]
tests/test_matching.py::test_cosine_similarity PASSED                    [ 60%]
tests/test_matching.py::test_structured_attribute_scoring PASSED         [ 80%]
tests/test_parser.py::test_pagination_detection PASSED                   [100%]

======================= 5 passed, 2 warnings in 15.28s ========================
```

### 3.2 Detailed Test Analysis
1. **`tests/test_broker.py::test_broker_pub_sub`**:
   - **What it tests**: Declares a test queue, initializes an asynchronous consumer thread, publishes an envelope, and verifies callback receipt, payload matching, and metadata within 0.3s.
   - **Gaps**: Does not test high-concurrency throughput, idempotency suppression of duplicate `message_id`s, or RabbitMQ fallback transitions.
2. **`tests/test_db.py::test_db_init_and_crud`**:
   - **What it tests**: Calls `init_db()`, creates and commits a `JobListing` entity, queries it back from the database session, and verifies persistence of JSON fields (`requirements`).
   - **Gaps**: Does not test `WorkflowState` or `MatchResult` schemas, concurrent sessions, or transaction rollbacks.
3. **`tests/test_matching.py::test_cosine_similarity`**:
   - **What it tests**: Mathematical correctness of numpy cosine similarity on orthogonal, identical, and 45-degree angle vectors.
4. **`tests/test_matching.py::test_structured_attribute_scoring`**:
   - **What it tests**: Tests `score_structured_attributes` on a synthetic Management Accountant profile. Validates that full experience (5 >= 3 years) yields 30.0, location match yields 10.0, and ACCA qualification yields 15.0.
   - **Gaps**: Does not test end-to-end matching message processing, ChromaDB integration, or vector pre-filtering.
5. **`tests/test_parser.py::test_pagination_detection`**:
   - **What it tests**: Checks a static string assertion `"?page=2" in html_content`.
   - **Gaps**: This is a trivial placeholder; it does not test HTML parsing, DOM extraction, or Gemini JSON extraction logic.

---

## 4. Requirements Compliance Matrix (relative to ORIGINAL_REQUEST.md)

| Req ID | Requirement Description | Implementation Status | Analysis & Observed Findings |
| :--- | :--- | :--- | :--- |
| **R1.1** | In-process thread-safe message broker fallback when RabbitMQ absent | **Fully Implemented** | `LocalMessageBroker` is thread-safe with `threading.Lock()` singleton, `queue.Queue()`, and `ThreadPoolExecutor(max_workers=6)`. Factory `MessageBroker()` seamlessly falls back when RabbitMQ is unreachable. |
| **R1.2** | Auto-fallback to local SQLite (`job_engine.db`) when PostgreSQL absent | **Fully Implemented** | `core/db.py:get_engine()` checks PostgreSQL connection with a 3-second timeout; upon failure, creates and binds `job_engine.db` with thread-safety (`check_same_thread=False`). |
| **R1.3** | Auto-fallback to embedded persistent ChromaDB (`./chroma_data`) when ChromaDB server absent | **Fully Implemented** | `core/vector_db.py:get_chroma_client()` probes remote ChromaDB HTTP heartbeat; upon failure, falls back to `chromadb.PersistentClient(path="./chroma_data")`. Verified operational. |
| **R2.1** | Extract search parameters from user goals using `gemini-3.6-flash` and JSON structured schema | **Fully Implemented** | `MasterAgent.start_workflow()` uses `INTENT_SCHEMA` and `extract_json()` targeting `gemini-3.6-flash`. Includes fallback defaults for offline resiliency. |
| **R2.2** | Extract structured job metadata (title, requirements, salary, location) from HTML listings | **Fully Implemented** | `JobParsingAgent.parse_job()` uses `JOB_SCHEMA` with required fields `title`, `description`, `requirements` and optional `salary_range`, `location`, `posted_date`. |
| **R2.3** | High-dimensional vector embeddings using `gemini-embedding-2` | **Fully Implemented** | `core/llm.py:get_embedding()` configured with `DEFAULT_EMBEDDING_MODEL = "gemini-embedding-2"` and calls `client.models.embed_content()`. |
| **R2.4** | Resilient fault tolerance using `tenacity` exponential backoff retries for 503/429 spikes | **Fully Implemented** | `@retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3), reraise=True)` decorates all LLM functions and agent message execution. |
| **R3.1** | Master Agent decomposes goals into 5-stage DAG (Company Discovery, Job Discovery, Job Parsing, Candidate Matching, Executive Reporting) | **Partially Implemented** | 5 stages exist in message flow, but completion detection logic in `MasterAgent.process_message()` contains a counting discrepancy between `dispatched_parses` and `len(ranked_matches)`. |
| **R3.2** | Job Search Agent handles rate limiting (max requests/second) | **Fully Implemented** | `_respect_rate_limit(domain, min_interval=0.2)` enforces a strict maximum of 5 req/sec per target domain. |
| **R3.3** | Job Search Agent handles anti-bot mitigation and fallback | **Fully Implemented** | Custom User-Agent header and resilient synthetic FTSE vacancy generator `get_simulated_career_html()` ensure uninterrupted execution even when blocked by Cloudflare or anti-bot defenses. |
| **R3.4** | Job Search Agent handles pagination detection | **Partially Implemented / Missing** | While simulated HTML includes pagination tags and a unit test checks string presence, `JobSearchAgent.scrape_company_jobs()` does NOT parse pagination links or traverse multiple pages. |
| **R4.1** | Stage 1: Fast vector cosine similarity pre-filtering (threshold >= 0.65) | **Broken / Missing Pre-filter** | `MatchingAgent` computes cosine similarity (`cos_sim`), but does **NOT** discard or filter out listings below `0.65`. All jobs proceed unconditionally to Stage 2 scoring. |
| **R4.2** | Stage 2: Multi-attribute structured weighted scoring (Skills 40%, Exp 30%, Edu 15%, Loc 10%, Keyword 5%) | **Fully Implemented** | Implemented with exact mathematical weights in `score_structured_attributes()`: Skills (40), Experience (30), Education/ACCA (15), Location (10), Keywords (5). |
| **R4.3** | Persist structured results, workflow checkpoints, and ranked recommendations to database | **Fully Implemented** | Persists to `workflows` (`WorkflowState`), `job_listings` (`JobListing`), and `match_results` (`MatchResult`). Top recommendations aggregated in final report. |

---

## 5. Identified Bugs, Deficiencies, and Deprecations

### 5.1 Critical Logic Deficiencies
1. **Missing Vector Similarity Pre-Filtering in `MatchingAgent`**:
   - **Location**: `agents/matching_agent.py:107-115`
   - **Observation**:
     ```python
     # Stage 1: Vector Similarity (Cosine threshold 0.65)
     cos_sim = cosine_similarity(candidate_emb, job_emb)
     # Stage 2: Structured Scoring (0 - 100)
     struct_score, breakdown = self.score_structured_attributes(job, candidate)
     ```
   - **Impact**: Non-matching jobs (e.g. `cos_sim < 0.65`) are never filtered out. The system computes Stage 2 for everything and averages them `(cos_sim * 40 + struct_score * 0.6)`, violating Requirement R4.1.
   - **Remedy**: Add an explicit check: if `cos_sim < 0.65`, exclude the job from recommendations or mark as disqualified.

2. **Unhandled Exception in `MatchingAgent` on LLM Embedding Failure**:
   - **Location**: `agents/matching_agent.py:87, 94`
   - **Observation**: Unlike `master_agent.py` and `job_parsing_agent.py` which catch LLM errors and supply structured fallbacks, `MatchingAgent` calls `get_embedding()` without a try/except fallback.
   - **Impact**: If the user runs the engine offline or without a live Gemini API quota, `get_embedding()` raises an error after 3 retries. `MatchingAgent` sends an error message to `master_queue`. However, `MasterAgent` does not handle `msg_type == "error"`, leaving the pipeline permanently frozen in `STAGE_4_MATCHING` until `run_local_engine.py` times out.
   - **Remedy**: Provide a deterministic semantic/keyword embedding fallback in `core/llm.py` or `MatchingAgent` when the external embedding API is unreachable.

3. **Master Agent Workflow Completion Counting Bug**:
   - **Location**: `agents/master_agent.py:192-194`
   - **Observation**:
     ```python
     dispatched = state.get("dispatched_parses", state["expected_searches"])
     if state["completed_searches"] >= state["expected_searches"] and len(state["ranked_matches"]) >= dispatched:
     ```
     `dispatched` counts the number of parse batches (e.g., 8 companies = 8 batches). `len(state["ranked_matches"])` counts total individual jobs scored (which could be 16 if each company has 2 jobs). If a company returns 2 jobs early, `len(state["ranked_matches"])` can exceed `dispatched` before other companies have finished matching, triggering premature completion.
   - **Remedy**: Track completion by tracking completed matching batches (`state["completed_matches"] == state["dispatched_matches"]`).

4. **Missing Pagination Traversal in `JobSearchAgent`**:
   - **Location**: `agents/job_search_agent.py:91-120`
   - **Observation**: The crawler performs a single GET request per company. Although `get_simulated_career_html` produces `<nav class="pagination"><a href="?page=2">Next Page</a></nav>`, the agent does not parse `<nav class="pagination">` nor does it fetch page 2.
   - **Remedy**: Parse HTML for pagination links (`rel="next"` or `class="pagination"`) with a configurable max page depth (e.g., 2-3 pages).

### 5.2 Deprecation Warnings
1. **`datetime.utcnow()` Deprecation in Python 3.12**:
   - Python 3.12 marks `datetime.utcnow()` as deprecated in favor of `datetime.now(datetime.UTC)`.
   - Occurrences:
     - `core/messaging.py:37`
     - `core/db.py:37, 51, 63`
     - `agents/job_search_agent.py:113`
     - `agents/job_parsing_agent.py:54`
     - `agents/master_agent.py:85, 196`

### 5.3 Dependencies & Packaging
- `playwright` and `playwright-stealth` are declared in `requirements.txt` and `Dockerfile`, but are not imported anywhere in `agents/job_search_agent.py`. While benign for execution, they inflate Docker build times (`playwright install --with-deps`). Either integrate Playwright for dynamic JavaScript rendering or remove them if lightweight HTTP scraping with synthetic fallback is preferred.

---

## 6. Recommendations for Next Phases

1. **Implement Cosine Pre-Filter (Priority 1)**:
   In `agents/matching_agent.py`, enforce `cos_sim >= 0.65`. Discard or flag jobs failing this threshold prior to final ranking.
2. **Add Offline Embedding Fallback (Priority 1)**:
   In `core/llm.py` or `matching_agent.py`, provide a deterministic mock/TF-IDF embedding fallback so end-to-end local runs never stall if Gemini API quotas are exhausted.
3. **Fix Master Agent DAG Completion Counter (Priority 2)**:
   Refactor batch tracking in `MasterAgent` to guarantee all dispatched matching tasks complete before marking the workflow `COMPLETED`.
4. **Implement Actual Pagination Parsing (Priority 2)**:
   In `JobSearchAgent`, parse pagination controls via BeautifulSoup and collect listings across pages up to a limit.
5. **Modernize Datetime Calls (Priority 3)**:
   Replace `datetime.utcnow()` with `datetime.now(datetime.UTC)` to eliminate deprecation warnings on Python 3.12+.
6. **Expand Unit & Integration Tests (Priority 3)**:
   Add tests for `CompanyListAgent`, `JobSearchAgent`, `JobParsingAgent`, and an end-to-end integration test (`test_pipeline_e2e.py`).
