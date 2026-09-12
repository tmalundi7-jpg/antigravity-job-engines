# Project: Multi-Agent Job Search & Matching Engine for FTSE Companies

## Architecture
The engine is a multi-agent distributed system running locally on the raw host machine with full fallback support:
- **Transport / Messaging**: `LocalMessageBroker` (in-process, thread-safe, queue-based) with fallback from RabbitMQ.
- **Relational Storage**: SQLAlchemy with SQLite (`job_engine.db`) auto-fallback from PostgreSQL.
- **Vector Storage**: ChromaDB `PersistentClient` (`./chroma_data`) auto-fallback from remote ChromaDB server.
- **LLM Services**: Google Gemini API via `gemini-3.6-flash` (search parameters & HTML job extraction with JSON structured schema) and `gemini-embedding-2` (3072-dimensional vector embeddings), with tenacity exponential backoff retries and deterministic offline fallbacks.
- **Agent Mesh**:
  - `MasterAgent`: Orchestrates the 5-stage Directed Acyclic Graph (DAG) state machine, persisting workflow states at every stage transition, generating executive reports.
  - `CompanyListAgent`: Returns comprehensive FTSE 100 and FTSE 250 constituent companies and career portals.
  - `JobSearchAgent`: Crawls career portals with domain rate limiting (5 req/sec, >=0.2s delay), pagination detection & traversal, and anti-bot mitigation.
  - `JobParsingAgent`: Extracts structured job metadata from HTML using `gemini-3.6-flash` and persists `JobListing` records.
  - `MatchingAgent`: Executes two-stage matching:
    * Stage 1: Vector cosine similarity pre-filtering with strict threshold gating ($\ge 0.65$).
    * Stage 2: Multi-attribute structured weighted scoring (Skills 40%, Experience 30%, Education 15%, Location 10%, Domain Fit 5%).
    * Blends composite score and persists `MatchResult` records.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | LocalMessageBroker In-Process Messaging | Thread-safe in-process message broker with ThreadPoolExecutor and envelope structure | M1 | R1.1 |
| 2 | SQLite Auto-Fallback & Checkpointing | Relational DB fallback to SQLite `job_engine.db` with thread safety; intermediate workflow state persistence | M1 | R1.2, R4.3 |
| 3 | ChromaDB PersistentClient Fallback | Embedded local vector database storage at `./chroma_data` with 3072-dim collection | M1 | R1.3, R2.3 |
| 4 | Gemini 3.6 Flash Structured Intent Extraction | Parameter extraction from user goals via JSON schema and tenacity retries | M1 | R2.1, R2.4 |
| 5 | Gemini 3.6 Flash HTML Job Parsing | Metadata extraction from job HTML into `JOB_SCHEMA` and persistence to `job_listings` | M1 | R2.2 |
| 6 | Gemini Embedding 2 (3072-dim) with Offline Fallback | 3072-dimensional embedding generation with tenacity retries and deterministic offline fallback | M1 | R2.3, R2.4 |
| 7 | Master Agent 5-Stage DAG State Machine | Complete DAG workflow with stage-by-stage DB persistence and accurate completion tracking | M1 | R3.1 |
| 8 | Job Search Crawling, Rate Limiting & Anti-bot | Domain rate limiting (5 req/sec), anti-bot fallback, and multi-page pagination traversal | M1 | R3.2, R3.3, R3.4 |
| 9 | FTSE 100 / 250 Constituent Discovery | Comprehensive constituent registry for FTSE 100 and FTSE 250 universes | M1 | R3.1 |
| 10 | Stage 1 Cosine Similarity Pre-filtering (>= 0.65) | Strict threshold gating: jobs below 0.65 cosine similarity are disqualified and filtered out | M1 | R4.1 |
| 11 | Stage 2 Multi-Attribute Structured Scoring | Exact mathematical scoring (Skill 40%, Exp 30%, Edu 15%, Loc 10%, Domain Fit 5%) | M1 | R4.2 |
| 12 | Candidate Recommendation Persistence & Reporting | Hybrid scoring, DB persistence to `match_results`, executive Markdown/JSON report | M1 | R4.3 |
| 13 | Python 3.12 Deprecation Cleanup | Replace `datetime.utcnow()` with `datetime.now(datetime.timezone.utc)` across all modules | M1 | Survey |
| 14 | Comprehensive E2E Test Suite | 100% pytest pass rate including broker, db, matching, parser, and full end-to-end pipeline | M1 | Acceptance |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Complete Engine Hardening, Two-Stage Matching & E2E Pipeline | All R1-R4 requirements: LocalMessageBroker, SQLite stage-by-stage checkpoints, ChromaDB 3072-dim persistence, Gemini 3.6 Flash & Embedding-2 with offline resilience, 5-stage DAG orchestrator, Stage 1 Cosine Pre-filter (>=0.65), Stage 2 Weighted Scoring (40/30/15/10/5), pagination traversal, Python 3.12 cleanups, and 100% pytest pass rate including E2E integration test | none | IN_PROGRESS |

---

## Code Layout
- `core/`
  - `messaging.py`: `LocalMessageBroker`, `RabbitMQBroker`, `MessageBroker()` factory.
  - `db.py`: `WorkflowState`, `JobListing`, `MatchResult`, `get_engine()`, `init_db()`.
  - `vector_db.py`: `get_chroma_client()`, collection initialization for 3072-dim embeddings.
  - `llm.py`: `extract_json`, `get_embedding` using `gemini-3.6-flash`, `gemini-embedding-2`, tenacity retries, offline fallbacks.
- `agents/`
  - `base.py`: `BaseAgent`, retry wrapper, envelope serialization, deduplication.
  - `company_list_agent.py`: `CompanyListAgent` for FTSE 100 & 250.
  - `job_search_agent.py`: `JobSearchAgent` with domain rate limiting, pagination traversal, anti-bot simulator.
  - `job_parsing_agent.py`: `JobParsingAgent` with `JOB_SCHEMA` extraction and database insertion.
  - `matching_agent.py`: `MatchingAgent` with Stage 1 cosine pre-filter ($\ge 0.65$), Stage 2 structured scoring, ChromaDB & SQL persistence.
  - `master_agent.py`: `MasterAgent` coordinating 5-stage DAG, database checkpointing at each transition, executive report generation.
- `tests/`
  - `test_broker.py`: Pub/sub and message passing tests.
  - `test_db.py`: Database initialization, CRUD, and workflow persistence tests.
  - `test_matching.py`: Cosine similarity, pre-filtering, and structured attribute scoring tests.
  - `test_parser.py`: HTML parsing, schema extraction, and pagination tests.
  - `test_pipeline_e2e.py`: End-to-end pipeline integration test from goal to final ranked report.
- `run_local_engine.py`: CLI entrypoint for running the multi-agent engine locally on the raw machine.

---

## Interface Contracts
### `core.messaging` ↔ `agents.base.BaseAgent`
- Message envelope format:
  ```json
  {
    "message_id": "<uuid>",
    "correlation_id": "<workflow_id>",
    "timestamp": "<iso_utc>",
    "source_agent": "<agent_name>",
    "target_agent": "<agent_name>",
    "type": "task_request | task_response | error",
    "payload": { ... }
  }
  ```
- Methods: `broker.publish(queue_name, envelope)`, `broker.consume(queue_name, callback)`.

### `agents.master_agent` ↔ `core.db`
- `WorkflowState` record must be updated at every stage transition:
  - Stage 1 (`STAGE_1_COMPANY_LIST`)
  - Stage 2 (`STAGE_2_JOB_DISCOVERY`)
  - Stage 3 (`STAGE_3_JOB_PARSING`)
  - Stage 4 (`STAGE_4_MATCHING`)
  - Stage 5 (`COMPLETED`)

### `agents.matching_agent` ↔ Two-Stage Pipeline Contract
- Input payload: `{"job": {...}, "candidate": {...}, "workflow_id": "<uuid>"}`
- Stage 1 Output: `cos_sim >= 0.65`. If `cos_sim < 0.65`, job is marked `disqualified` with `passed_prefilter = False` and excluded from ranked recommendations.
- Stage 2 Output: Structured score $\in [0, 100]$ across the 5 dimensions.
- Composite Output: `final_score = round((cos_sim * 40) + (struct_score * 0.6), 1)` for jobs passing pre-filter.
- Persisted to `match_results` table in DB and top recommendations aggregated.
