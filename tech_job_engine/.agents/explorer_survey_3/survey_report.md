# Comprehensive Survey Report: Architecture, 5-Stage DAG & Fallback Systems

**Project**: Multi-Agent Job Search and Matching Engine for FTSE Companies  
**Author**: Explorer Survey Agent 3  
**Date**: 2026-09-03  
**Integrity Mode**: Development / Raw Host Machine Execution  
**Target Scope**: 5-Stage DAG Architecture, Local Fallback Mechanisms, Workflow Checkpoints & Models, Gap Analysis

---

## 1. Executive Summary

The FTSE Multi-Agent Job Search and Matching Engine is architected to autonomously discover open vacancies across FTSE constituent companies, extract and structure job specifications using Google Gemini LLM models (`gemini-3.6-flash`), and rank candidate suitability through a two-stage hybrid matching algorithm (combining `gemini-embedding-2` vector similarity with structured multi-attribute scoring).

A core architectural pillar is **seamless local raw-machine execution**: the engine is designed to execute locally on a host machine without requiring external Docker Desktop, RabbitMQ, PostgreSQL, or remote ChromaDB servers. This is achieved via a **triple fallback architecture**:
1. `LocalMessageBroker`: In-process thread-safe message broker fallback when RabbitMQ is unreachable.
2. `SQLite` (`job_engine.db`): Local relational database fallback with thread-safe connection pooling when PostgreSQL is down.
3. `ChromaDB PersistentClient` (`./chroma_data`): Local embedded persistent vector storage when the Chroma HTTP server is offline.

The test suite (`pytest -v`) currently passes 100% (5/5 passing) locally on Python 3.12 without external services. However, critical gaps exist between the current prototype and the target production architecture, particularly around intermediate workflow checkpoint persistence, strict enforcement of the Stage 1 vector pre-filtering cutoff threshold ($\ge 0.65$), full FTSE constituent coverage, active multi-page pagination scraping, and dedicated executive report file generation.

---

## 2. Five-Stage DAG Architecture Survey

The Master Agent (`agents/master_agent.py`) orchestrates the pipeline through a Directed Acyclic Graph (DAG) state machine across 5 distinct stages:

```
                          [ User Search Goal ]
                                   │
                                   ▼
                       [ Master Agent (DAG Engine) ]
                        - Intent Parsing (Gemini 3.6 Flash)
                        - Workflow State Initialization
                                   │
                    ┌──────────────┴──────────────┐
                    │ (task_request)              │
                    ▼                             ▼
        [ Stage 1: Company Discovery ]            │
         (agents/company_list_agent.py)           │
                    │                             │
                    │ (companies list)            │
                    ▼                             │
        [ Stage 2: Job Discovery ]                │
         (agents/job_search_agent.py)             │
         - Rate Limiting (0.2s interval)          │
         - Anti-Bot & HTML Simulation Fallback    │
                    │                             │
                    │ (raw_jobs HTML)             │
                    ▼                             │
        [ Stage 3: Job Parsing ]                  │
         (agents/job_parsing_agent.py)            │
         - Gemini 3.6 Flash Schema Extraction     │
         - Persist JobListing to DB               │
                    │                             │
                    │ (parsed_jobs JSON)          │
                    ▼                             │
        [ Stage 4: Candidate Matching ]           │
         (agents/matching_agent.py)               │
         - Stage 1: Vector Cosine Similarity      │
         - Stage 2: 5-Attribute Weighted Scoring  │
         - Persist MatchResult to DB              │
                    │                             │
                    │ (ranked_matches)            │
                    ▼                             ▼
        [ Stage 5: Executive Reporting ] ◄────────┘
         - Leaderboard Aggregation & DB Completion
         - Console & Metric Summary Reporting
```

### Stage 1: Company Discovery
- **Agent**: `CompanyListAgent` (`agents/company_list_agent.py`)
- **Queue**: `company_list_queue` -> `master_queue`
- **Input Contract**: `{"universe": "FTSE 100" | "FTSE 250" | "all", "custom_companies": Optional[list]}`
- **Output Contract**: `{"universe": str, "companies": list[dict], "total": int}`
- **Implementation Mechanics**:
  - Contains curated seed constituent registries:
    - `FTSE_250_CONSTITUENTS` (e.g., Balfour Beatty, Greggs, Tate & Lyle, ITV, Marks & Spencer, Aston Martin Lagonda, Direct Line Group, Bellway).
    - `FTSE_100_CONSTITUENTS` (e.g., AstraZeneca, BP, HSBC, Unilever).
  - Normalizes requested universe string (`universe.upper().replace(" ", "")`) and selects the target subset.
  - Supports dynamic overrides via `custom_companies` in the task payload.
- **Architectural Observations**:
  - Fast, deterministic seed list guarantees reliability on local machines without web dependencies.
  - Full FTSE 100 (100 companies) and FTSE 250 (250 companies) registries are not yet fully populated in the static data file.

### Stage 2: Job Discovery
- **Agent**: `JobSearchAgent` (`agents/job_search_agent.py`)
- **Queue**: `job_search_queue` -> `master_queue`
- **Input Contract**: `{"company": dict, "search_parameters": {"keywords": list, "location": str}}`
- **Output Contract**: `{"company_id": str, "company_name": str, "raw_jobs": list[dict], "count": int}`
- **Implementation Mechanics**:
  - **Rate Limiting**: Domain-level tracking via `_respect_rate_limit(domain, min_interval=0.2)`. Uses `time.sleep(min_interval - elapsed)` if successive requests to the same domain arrive within 200ms.
  - **HTTP Fetching**: Uses `requests.Session` with modern desktop browser `User-Agent` (`Mozilla/5.0 ... Chrome/120.0.0.0`).
  - **Anti-Bot Mitigation & Resilient Simulation**: When external sites return 403/429, timeout, or lack live postings matching the target role, the agent engages `get_simulated_career_html(company_name, primary_keyword, location)` to synthesize realistic career page HTML containing `<article class="job-card">` nodes and `<nav class="pagination">` navigation links.
- **Architectural Observations**:
  - `requirements.txt` specifies `playwright` and `playwright-stealth`, but the agent currently uses `requests` and resilient HTML simulation. This deliberate design prevents headless browser launch failures on bare-metal environments lacking browser binaries.

### Stage 3: Job Parsing
- **Agent**: `JobParsingAgent` (`agents/job_parsing_agent.py`)
- **Queue**: `job_parse_queue` -> `master_queue`
- **Input Contract**: `{"raw_jobs": list[dict]}`
- **Output Contract**: `{"parsed_jobs": list[dict], "count": int}`
- **Implementation Mechanics**:
  - **Schema Definition**: `JOB_SCHEMA` mandates `title`, `description`, `requirements` (array of strings), with optional `company`, `location`, `salary_range`, and `posted_date`.
  - **Extraction**: Truncates HTML to 3000 characters and invokes `core.llm.extract_json` (Gemini 3.6 Flash with `response_mime_type="application/json"` and `temperature=0.1`).
  - **Fault-Tolerant Fallback**: If Gemini API encounters an error (e.g. quota, key missing, network failure), catches `Exception` and returns a structured default dictionary.
  - **Database Persistence**: Directly writes each parsed job into the `job_listings` table via SQLAlchemy `JobListing` model.

### Stage 4: Candidate Matching
- **Agent**: `MatchingAgent` (`agents/matching_agent.py`)
- **Queue**: `matching_queue` -> `master_queue`
- **Input Contract**: `{"candidate": dict, "parsed_jobs": list[dict]}`
- **Output Contract**: `{"workflow_id": str, "ranked_matches": list[dict], "top_recommendations": list[dict]}`
- **Implementation Mechanics**:
  - **Embedding Generation**: Calls `core.llm.get_embedding()` (`gemini-embedding-2`, 3072-dimensional vectors) for both candidate profile and job listing content.
  - **Vector Storage**: Indexes job vectors into ChromaDB collection `ftse_job_listings` (`collection.upsert(...)`).
  - **Two-Stage Scoring Pipeline**:
    1. **Stage 1 (Vector Cosine Similarity)**: Computes dot product normalized by vector Euclidean norms:
       $$\text{Cosine Similarity} = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2}$$
    2. **Stage 2 (Structured Multi-Attribute Scoring, 100 points total)**:
       - **Skills Overlap (40%)**: Ratio of matched candidate skills against job requirements:
         $$\text{Score}_{\text{skill}} = \min\left(1.0, \frac{\text{matched\_reqs}}{\max(\text{len}(\text{job\_reqs}), 1)} \times 1.2\right) \times 40.0$$
       - **Experience Match (30%)**: Proportional scaling based on years of experience:
         $$\text{Score}_{\text{exp}} = \begin{cases} 30.0 & \text{if } \text{cand\_exp} \ge \text{req\_exp} \\ \left(\frac{\text{cand\_exp}}{\text{req\_exp}}\right) \times 30.0 & \text{otherwise} \end{cases}$$
       - **Education & Certifications (15%)**: Hard check for qualification credentials (ACCA, CIMA, ACA): 15.0 if matched, 7.5 partial otherwise.
       - **Location Match (10%)**: Exact or substring city match / "remote": 10.0 if matched, 3.0 otherwise.
       - **Keywords & Domain Fit (5%)**: Industry alignment points (5.0 points default).
    3. **Composite Scoring**:
       $$\text{Final Score} = \left(\text{Cosine Similarity} \times 100 \times 0.40\right) + \left(\text{Structured Score} \times 0.60\right)$$
  - **Database Persistence**: Persists a `MatchResult` record in the relational database for every evaluated match.

### Stage 5: Executive Reporting
- **Implementation**: Handled jointly by `MasterAgent` (`agents/master_agent.py` lines 185-215) and `run_local_engine.py` (lines 78-98).
- **Functionality**:
  - Master Agent monitors when `completed_searches >= expected_searches` and all dispatched parse batches have returned.
  - Sorts matches descending by `final_score`.
  - Sets `state["status"] = "COMPLETED"`, updates `WorkflowState` in DB to `COMPLETED` with `total_matched` and `top_match`.
  - Runner displays a formatted executive leaderboard:
    - Search Goal, Target Universe, Target Role
    - Metrics: Total Companies Scanned, Total Jobs Discovered, Total Matches Scored
    - Ranked Recommendations: Rank, Score, Title, Company, Location, Salary, Full Score Breakdown, Reasoning text, Link.

---

## 3. Local Raw-Machine Execution & Triple Fallback Systems Survey

The system provides complete isolation from external services through three robust fallback mechanisms:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     TRIPLE FALLBACK ARCHITECTURE                         │
├─────────────────────────┬───────────────────────┬───────────────────────┤
│ Component               │ Primary (Remote/Docker)│ Fallback (Local Host) │
├─────────────────────────┼───────────────────────┼───────────────────────┤
│ 1. Message Broker       │ RabbitMQ (AMQP:5672)  │ LocalMessageBroker    │
│                         │ (pika client)         │ (In-process Queue)    │
├─────────────────────────┼───────────────────────┼───────────────────────┤
│ 2. Relational Database  │ PostgreSQL (:5432)    │ SQLite                │
│                         │ (psycopg2)            │ (job_engine.db)       │
├─────────────────────────┼───────────────────────┼───────────────────────┤
│ 3. Vector Database      │ ChromaDB HTTP (:8000) │ ChromaDB Persistent   │
│                         │ (HttpClient)          │ (./chroma_data)       │
└─────────────────────────┴───────────────────────┴───────────────────────┘
```

### 3.1. In-Process Thread-Safe Message Broker (`LocalMessageBroker`)
- **File**: `core/messaging.py` (lines 11-80, 134-148)
- **Design Pattern**: Thread-safe Singleton (`__new__` guarded by `threading.Lock()`).
- **Internal Storage**: `self._queues` dictionary mapping queue names to `queue.Queue()` instances.
- **Thread Safety**:
  - Python's `queue.Queue` provides thread safety with built-in reentrant locks and condition variables (`not_empty`, `not_full`).
  - Producers and consumers on different threads can safely publish and consume without race conditions or memory corruption.
- **Concurrency & Dispatch**:
  - `consume()` creates a daemon thread running `_worker()`.
  - Inside `_worker()`, each incoming message is dispatched to a `concurrent.futures.ThreadPoolExecutor(max_workers=6)`.
  - This prevents long-running callbacks (such as LLM requests or web scraping) from stalling the consumer thread.
- **Standard Envelope**:
  ```json
  {
    "message_id": "uuid4",
    "correlation_id": "workflow_id",
    "timestamp": "2026-09-03T01:16:08Z",
    "source_agent": "company_list_agent",
    "target_agent": "master_queue",
    "type": "task_response",
    "payload": { ... }
  }
  ```
- **Fallback Activation**:
  ```python
  def MessageBroker():
      uri = getattr(config, "RABBITMQ_URI", "")
      if uri:
          try:
              import pika
              return RabbitMQBroker(uri)
          except Exception as e:
              logger.info(f"RabbitMQ unavailable ({e}). Using in-process LocalMessageBroker.")
      return LocalMessageBroker()
  ```
  If RabbitMQ is not running or `pika` fails to connect, `MessageBroker()` automatically catches the exception and returns the singleton `LocalMessageBroker`.

### 3.2. Local Relational Database Fallback (`job_engine.db`)
- **File**: `core/db.py` (lines 12-31)
- **Engine Factory**:
  - Checks if `config.POSTGRES_URI` starts with `postgresql`.
  - Attempts a test connection with `connect_timeout=3`.
  - If connection fails or `psycopg2` raises an exception, catches it and falls back to:
    ```python
    sqlite_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "job_engine.db")
    return create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})
    ```
- **Thread Safety in SQLite**:
  - Standard SQLite connections in Python raise an exception if accessed across threads. Setting `connect_args={"check_same_thread": False}` allows multiple threads spawned by `LocalMessageBroker` to query and commit through their own `SessionLocal()` scopes safely.
  - WAL mode (Write-Ahead Logging) is recommended for high-concurrency scenarios to prevent write locks.

### 3.3. Embedded Persistent ChromaDB Fallback (`./chroma_data`)
- **File**: `core/vector_db.py` (lines 9-28)
- **Client Factory**:
  - Attempts `chromadb.HttpClient(host=..., port=...)` and tests connectivity via `http_client.heartbeat()`.
  - If the remote server is unreachable, catches `Exception` and initializes:
    ```python
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_data")
    os.makedirs(db_path, exist_ok=True)
    return chromadb.PersistentClient(path=db_path, settings=Settings(anonymized_telemetry=False))
    ```
- **Persistence Storage**:
  - Creates the `./chroma_data` directory.
  - Maintains `chroma.sqlite3` for document and collection metadata.
  - Stores binary index files (`data_level0.bin`, `header.bin`, `link_lists.bin`) for HNSW cosine/l2 nearest neighbor search.
  - Survives process restarts without losing indexed jobs.

---

## 4. Workflow State Checkpoints & Database Model Persistence

### 4.1. Relational Database Schema (`core/db.py`)

Three primary models are declared using SQLAlchemy ORM:

| Table Name | Model Class | Key Columns | Description |
| :--- | :--- | :--- | :--- |
| `workflows` | `WorkflowState` | `id` (PK, String), `status` (String), `created_at` (DateTime), `data` (JSON) | Tracks workflow lifecycle, input goal, parameters, and completion metadata. |
| `job_listings` | `JobListing` | `id` (PK, String), `company` (String), `title` (String), `location` (String), `description` (Text), `requirements` (JSON), `salary_range` (String), `source_url` (String), `raw_html` (Text), `created_at` (DateTime) | Stores structured job postings extracted from company career sites. |
| `match_results` | `MatchResult` | `id` (PK, String), `workflow_id` (String), `job_id` (String), `candidate_id` (String), `similarity_score` (Float), `structured_score` (Float), `final_score` (Float), `reasoning` (Text), `created_at` (DateTime) | Records quantitative scores, breakdowns, and reasoning for candidate-job pairings. |

### 4.2. State Transition & Checkpoint Lifecycle

```
[Workflow Start] ──> DB: WorkflowState(status="RUNNING", data={goal, params})
       │
       ▼
[Stage 1: Company Discovery] ──> In-Memory: state["companies"]  [⚠️ NO DB CHECKPOINT]
       │
       ▼
[Stage 2: Job Discovery]     ──> In-Memory: state["raw_jobs_collected"]  [⚠️ NO DB CHECKPOINT]
       │
       ▼
[Stage 3: Job Parsing]       ──> DB: JobListing (Persisted for each parsed job) ✅
                             ──> In-Memory: state["parsed_jobs"]  [⚠️ NO WORKFLOW CHECKPOINT]
       │
       ▼
[Stage 4: Candidate Matching]──> DB: MatchResult (Persisted for each evaluated match) ✅
                             ──> In-Memory: state["ranked_matches"]
       │
       ▼
[Stage 5: Completion]        ──> DB: WorkflowState(status="COMPLETED", data={total_matched, top_match}) ✅
```

### 4.3. Critical Checkpoint Limitations Identified
1. **Missing Intermediate Stage Checkpoints**: In `MasterAgent`, only stage initialization (`RUNNING`) and completion (`COMPLETED`) write to `WorkflowState`. Intermediate status changes (`STAGE_1_COMPANY_LIST`, `STAGE_2_JOB_DISCOVERY`, `STAGE_3_JOB_PARSING`, `STAGE_4_MATCHING`) exist solely in the ephemeral Python dictionary `active_workflows[workflow_id]`.
2. **Crash Resilience**: If a machine crashes or worker terminates during Stage 2 or 3, the database retains `status="RUNNING"`. An external observer or recovery supervisor cannot inspect which stage failed or resume from the last completed checkpoint.

---

## 5. Gap Analysis: Current Implementation vs. Target Architecture

The following matrix compares the current codebase against `ORIGINAL_REQUEST.md` (R1-R4 and Acceptance Criteria):

| Requirement | Target Specification | Current Codebase Status | Gap Severity | Gap Description & Location |
| :--- | :--- | :--- | :--- | :--- |
| **R1: Message Broker Fallback** | In-process `LocalMessageBroker` when RabbitMQ absent | Fully Implemented ✅ | None | `core/messaging.py`: Thread-safe singleton with `queue.Queue` and `ThreadPoolExecutor`. Passes `tests/test_broker.py`. |
| **R1: SQLite Fallback** | Auto-fallback to local `job_engine.db` | Fully Implemented ✅ | Low | `core/db.py`: Connect timeout of 3s to Postgres, seamless fallback to SQLite. Deprecation warning on `datetime.utcnow()`. |
| **R1: ChromaDB Fallback** | Auto-fallback to embedded `./chroma_data` | Fully Implemented ✅ | None | `core/vector_db.py`: Remote heartbeat check, falls back to `PersistentClient(path="./chroma_data")`. |
| **R2: LLM Models** | `gemini-3.6-flash` and `gemini-embedding-2` | Fully Configured ✅ | Low | Configured in `core/llm.py` with `tenacity` retry wrappers. |
| **R3: 5-Stage DAG** | Master Agent orchestrates 5 stages | Functionally Working ⚠️ | Medium | Stages 1-4 execute in sequence; Stage 5 reporting is embedded in MasterAgent/runner rather than a dedicated reporting artifact/module. |
| **R3: FTSE Constituents** | Full FTSE 100/250 universe | Partial Seed Data ⚠️ | Medium | `agents/company_list_agent.py` only contains 8 FTSE 250 and 4 FTSE 100 companies. Needs complete constituent registry. |
| **R3: Web Crawling & Anti-bot** | Scraping, pagination, rate limiting, anti-bot | Partial Implementation ⚠️ | Medium | `agents/job_search_agent.py` uses `requests` and simulated HTML fallback. Rate limiting (0.2s) works, but active multi-page pagination traversal is not performed. |
| **R4: Vector Pre-Filtering** | Fast cosine similarity cutoff $\ge 0.65$ | Missing Filter Enforcement ❌ | **High** | `agents/matching_agent.py` calculates `cos_sim`, but does **not** drop jobs with $\text{cos\_sim} < 0.65$. All jobs proceed to Stage 2 structured scoring. |
| **R4: Structured Scoring** | 40% Skills, 30% Exp, 15% Edu, 10% Loc, 5% Keyword | Fully Implemented ✅ | None | `agents/matching_agent.py`: `score_structured_attributes` exactly matches specified weights and passes `test_matching.py`. |
| **R4: Database Checkpointing** | Persist workflow checkpoints & models | Partial Implementation ⚠️ | **High** | `JobListing` and `MatchResult` are persisted. `WorkflowState` is only updated at start and end; intermediate stage checkpoints are missing. |
| **Stage 5: Reporting Artifact** | Executive Summary, Ranked matches, Metrics | Console Log Only ⚠️ | Medium | Output printed to stdout/logging. No structured markdown or JSON report file generated in a `reports/` folder. |

---

## 6. Detailed Findings on Specific Technical Areas

### 6.1. Two-Stage Candidate Matching Cutoff Gap (Detailed Trace)
In `ORIGINAL_REQUEST.md`:
> *"Stage 1: Fast vector cosine similarity pre-filtering (threshold >= 0.65).*  
> *Stage 2: Multi-attribute structured weighted scoring..."*

In `agents/matching_agent.py` (lines 107-135):
```python
# Stage 1: Vector Similarity (Cosine threshold 0.65)
cos_sim = cosine_similarity(candidate_emb, job_emb)

# Stage 2: Structured Scoring (0 - 100)
struct_score, breakdown = self.score_structured_attributes(job, candidate)

# Combined weighted score (40% vector similarity + 60% structured score)
final_score = round((cos_sim * 100 * 0.4) + (struct_score * 0.6), 1)
```
**Observation**: The code comments mention `threshold 0.65`, but there is no `if cos_sim < 0.65: continue` or filtering mechanism. Every job is scored for structured attributes and blended into `final_score`.
**Impact**: Irrelevant jobs (e.g., software engineering roles when searching for accounting) with cosine similarity of 0.30 may still receive points for generic attributes (e.g., London location, 5 years experience) and appear in the ranking.
**Remedy**:
```python
if cos_sim < 0.65:
    logger.info(f"Job {job_id} ({job.get('title')}) filtered out by Stage 1 vector cutoff ({cos_sim:.3f} < 0.65)")
    continue
```

### 6.2. Workflow Checkpointing Gap (Detailed Trace)
In `agents/master_agent.py`:
- `start_workflow` (line 92):
  `db.merge(WorkflowState(id=workflow_id, status="RUNNING", data={"goal": goal, "params": params}))`
- `process_message` Stage 1 Response (line 124):
  Updates `state["status"] = "STAGE_2_JOB_DISCOVERY"` in Python dictionary only. **No DB call.**
- `process_message` Stage 2 Response (line 148):
  Updates `state["raw_jobs_collected"]` in memory only. **No DB call.**
- `process_message` Stage 3 Response (line 166):
  Updates `state["status"] = "STAGE_4_MATCHING"` in memory only. **No DB call.**
- `process_message` Stage 4 Response (line 194):
  `db.merge(WorkflowState(id=workflow_id, status="COMPLETED", data={...}))`

**Remedy**: Implement a dedicated checkpoint helper in `MasterAgent`:
```python
def _checkpoint_state(self, workflow_id: str, stage: str, metadata: dict = None):
    try:
        with SessionLocal() as db:
            wf = db.query(WorkflowState).filter(WorkflowState.id == workflow_id).first()
            if wf:
                wf.status = stage
                current_data = wf.data or {}
                if metadata:
                    current_data.update(metadata)
                wf.data = current_data
                db.commit()
    except Exception as e:
        logger.error(f"Failed to checkpoint workflow {workflow_id} to {stage}: {e}")
```

### 6.3. Deprecation Warnings in Python 3.12
Running `pytest -v` produces:
```
DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
```
- In `core/messaging.py:37`: `datetime.utcnow().isoformat()`
- In `core/db.py:37,51,63`: `default=datetime.utcnow`
- In `agents/job_search_agent.py:113`: `datetime.utcnow().isoformat()`
- In `agents/job_parsing_agent.py:54`: `datetime.utcnow().date().isoformat()`
- In `agents/master_agent.py:85,196`: `datetime.utcnow().isoformat()`

**Remedy**: Update imports to `from datetime import datetime, timezone` and use `datetime.now(timezone.utc)`.

---

## 7. Actionable Implementation Recommendations for Subsequent Phases

1. **Enforce Two-Stage Filter in `MatchingAgent`**:
   Insert the pre-filtering cutoff `if cos_sim < 0.65: continue` so that only candidate-job pairs passing semantic vector similarity proceed to Stage 2 multi-attribute scoring.

2. **Instrument Continuous Database Checkpoints in `MasterAgent`**:
   Add atomic database updates whenever `state["status"]` changes (`STAGE_1_COMPANY_LIST`, `STAGE_2_JOB_DISCOVERY`, `STAGE_3_JOB_PARSING`, `STAGE_4_MATCHING`, `STAGE_5_REPORTING`, `COMPLETED`).

3. **Expand FTSE Constituent Registry**:
   Expand `agents/company_list_agent.py` or load a complete JSON registry containing all FTSE 100 and FTSE 250 constituent companies, tickers, sectors, and career URLs.

4. **Implement Dedicated Executive Report Generation**:
   Add an export method in `MasterAgent` or a dedicated reporter module that generates a structured markdown report (e.g., `reports/executive_report_<workflow_id>.md`) and persists it to disk and the database.

5. **Upgrade DateTime Calls**:
   Replace all deprecated `datetime.utcnow()` references with `datetime.now(timezone.utc)` across the codebase.

6. **Add Comprehensive Unit Tests**:
   - `tests/test_dag_checkpointing.py`: Test state transitions and verify that `WorkflowState` rows accurately reflect each stage.
   - `tests/test_matching_filter.py`: Verify that jobs with vector similarity $< 0.65$ are dropped during Stage 1 pre-filtering.
   - `tests/test_fallback_resilience.py`: Explicitly verify that database and broker factories fallback to SQLite and LocalMessageBroker when simulated errors are injected.
