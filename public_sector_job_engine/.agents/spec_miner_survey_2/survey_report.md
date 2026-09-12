# Specification Mining Report: Requirements & Model Specifications
**Project**: Multi-Agent Job Search and Matching Engine for FTSE Companies  
**Author**: Spec Miner Survey 2  
**Date**: 2026-09-03  
**Status**: Authoritative Specifications Established  

---

## 1. Executive Summary

This specification report documents the complete functional requirements, non-functional constraints, LLM integrations, and mathematical specifications mined from `ORIGINAL_REQUEST.md`, authoritative project source files (`core/`, `agents/`, `tests/`), configuration artifacts, and runtime execution data.

The engine coordinates five autonomous agents over an asynchronous message bus to crawl vacancies across FTSE 100/250 companies, parse unstructured HTML into strict schemas with `gemini-3.6-flash`, generate 3072-dimensional vector embeddings with `gemini-embedding-2`, and rank candidates against positions using a two-stage hybrid matching algorithm (Cosine Similarity pre-filtering at $\ge 0.65$ followed by multi-attribute weighted scoring).

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Architecture | In-Process Message Broker Fallback | Thread-safe in-memory message bus (`LocalMessageBroker`) when RabbitMQ is absent | Queue name, message payload, source/target agent IDs | In-memory message delivery via thread pool (`max_workers=6`) | Drops dropped queues; recovers gracefully without network sockets | `core/messaging.py:11-80`, `ORIGINAL_REQUEST.md:14` |
| 2 | Architecture | Relational DB Auto-Fallback | Graceful fallback from PostgreSQL to local SQLite (`job_engine.db`) | Database connection string, ORM operations | Active SQLAlchemy `SessionLocal` connected to SQLite or Postgres | Connect timeout after 3s logs warning and activates local SQLite | `core/db.py:12-29`, `ORIGINAL_REQUEST.md:15` |
| 3 | Architecture | ChromaDB Persistent Client Fallback | In-process persistent storage (`./chroma_data`) when remote Chroma server is absent | Host (`CHROMADB_HOST`), Port (`CHROMADB_PORT`) | `chromadb.PersistentClient` or `chromadb.HttpClient` | Heartbeat failure falls back to disk path `./chroma_data` | `core/vector_db.py:9-27`, `ORIGINAL_REQUEST.md:16` |
| 4 | LLM Integration | Goal Intent Parameter Extraction | Extracts target role, universe, and filters from unstructured user search goals | Natural language prompt string (e.g. "Find a Management Accountant in FTSE 250") | Structured JSON conforming to `INTENT_SCHEMA` (`role`, `universe`, `filters`) | Tenacity 3x retry; fallback to hardcoded default role & universe | `core/llm.py:32-42`, `agents/master_agent.py:12-60` |
| 5 | LLM Integration | HTML Job Metadata Extraction | Extracts job title, company, location, requirements array, salary range from HTML | Truncated HTML string (max 3000 chars), company name hint | Structured JSON matching `JOB_SCHEMA` (`title`, `description`, `requirements`, etc.) | Tenacity 3x retry; fallback to standard Management Accountant template | `core/llm.py:32-42`, `agents/job_parsing_agent.py:10-56` |
| 6 | LLM Integration | High-Dimensional Embeddings | Generates 3072-dimensional vector representations using `gemini-embedding-2` | Unstructured text string (candidate bio or concatenated job listing) | List of 3072 float values (`response.embeddings[0].values`) | Tenacity 3x retry; reraises exception if API quota/network exhausted | `core/llm.py:44-55`, `ORIGINAL_REQUEST.md:21` |
| 7 | Resilience | Tenacity Exponential Backoff | Automatic retries for transient HTTP 429 and 503 network / API spikes | Any failed LLM call or agent message processing | Successful response or reraised exception after 3 attempts | Exponential wait ($1s \le t \le 10s$ for LLM, $1s \le t \le 30s$ for agents) | `core/llm.py:15,27,44`, `agents/base.py:43` |
| 8 | Orchestration | Master Agent 5-Stage DAG State Machine | Coordinates Company Discovery, Job Discovery, Job Parsing, Matching, and Reporting | User goal and optional candidate profile dictionary | Directed acyclic workflow tracking state; final ranked leaderboard | Message correlation ID mismatches logged; missing workflows rejected | `agents/master_agent.py:30-218` |
| 9 | Crawling | FTSE Constituent Discovery | Enumerates constituent companies and careers portals for FTSE 100 and FTSE 250 | Universe string (`FTSE 100`, `FTSE 250`, or combined) | List of company records with `id`, `name`, `career_url` | Defaults to full FTSE 100 + 250 list if universe unrecognized | `agents/company_list_agent.py:7-52` |
| 10 | Crawling | Domain Rate Limiting & Anti-Bot Fallback | Crawls vacancy pages with minimum inter-request delay (0.2s) and resilient HTML simulator | Company record, search parameters (`keywords`, `location`) | List of raw job dictionaries (`source_url`, `html_content`, metadata) | Network timeout (3s) or 403/anti-bot triggers resilient simulated HTML | `agents/job_search_agent.py:62-120` |
| 11 | Matching | Stage 1 Cosine Similarity Pre-Filtering | Calculates angular vector similarity and applies threshold gating ($\ge 0.65$) | Two 3072-dim vectors (candidate embedding, job listing embedding) | Float similarity score $\in [-1.0, 1.0]$ | Zero-norm vectors return $0.0$ safely | `agents/matching_agent.py:11-17`, `ORIGINAL_REQUEST.md:29` |
| 12 | Matching | Stage 2 Multi-Attribute Structured Scoring | Evaluates candidate fit across skills (40%), experience (30%), certs (15%), location (10%), fit (5%) | Structured job dictionary, structured candidate dictionary | Total score (0-100) and breakdown dictionary | Missing fields default to safe standard values | `agents/matching_agent.py:24-69` |
| 13 | Matching | Hybrid Composite Ranking & Persistence | Computes composite score, ranks candidates descending, and persists to DB/ChromaDB | Cosine similarity float, structured score float, metadata | Ranked list of match objects with reasoning and score breakdown | DB failure logs error without breaking ranking pipeline | `agents/matching_agent.py:110-168` |
| 14 | Persistence | Relational Checkpointing | Records state transitions in `workflows`, `job_listings`, and `match_results` tables | Workflow ID, state payload, job attributes, match scores | Committed database rows in SQLite or PostgreSQL | Session rollback on failure; logs warning | `core/db.py:33-64` |
| 15 | Testing | Automated Verification Test Suite | Verifies broker pub/sub, database CRUD, cosine math, structured scoring, pagination | `pytest` CLI runner | Pytest exit code 0; 5 passing unit tests | Deprecation warnings on `datetime.utcnow()` | `tests/` directory |

---

## 3. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | `cosine_similarity` | Zero vectors: `v1 = [0, 0, 0]`, `v2 = [1, 2, 3]` | Returns `0.0` safely via `if denom == 0: return 0.0` guard; avoids ZeroDivisionError. |
| 2 | `cosine_similarity` | Identical vectors: `v1 = [1, 0, 0]`, `v2 = [1, 0, 0]` | Returns `1.0` (asserted by `np.isclose` in `test_matching.py`). |
| 3 | `cosine_similarity` | Orthogonal vectors: `v1 = [1, 0, 0]`, `v2 = [0, 1, 0]` | Returns `0.0` (asserted by `np.isclose` in `test_matching.py`). |
| 4 | `extract_json` (Intent) | Missing or invalid `GEMINI_API_KEY` | Exception raised by `client.models.generate_content`; caught in `master_agent.py:55` and falls back to default Management Accountant parameters. |
| 5 | `extract_json` (Job HTML) | Truncated HTML (> 3000 chars) | Only first 3000 chars sliced (`html[:3000]`); prevents LLM prompt token overflow while retaining main job card details. |
| 6 | `extract_json` (Job HTML) | Network failure / 503 error during HTML extraction | Caught in `job_parsing_agent.py:46`; falls back to default structured job dictionary with ACCA/CIMA requirements. |
| 7 | `score_structured_attributes` | Job with zero requirements: `requirements: []` | `max(len(job_reqs), 1)` prevents zero division; `skill_ratio = 0.0`, `skill_score = 0.0`. |
| 8 | `score_structured_attributes` | Candidate experience exceeds job requirement: Cand=5 yrs, Job=3 yrs | Full 30.0 points awarded (`cand_exp >= req_exp`); no overqualification deduction. |
| 9 | `score_structured_attributes` | Candidate experience below requirement: Cand=2 yrs, Job=4 yrs | Proportional scoring: `(2 / 4) * 30.0 = 15.0` points awarded. |
| 10 | `score_structured_attributes` | Required experience missing from job dict | Defaults to 3 years (`job.get("years_experience", 3)`). |
| 11 | `score_structured_attributes` | Candidate qualifications match: Candidate has "ACCA Qualified", Job mentions "ACCA" | Full 15.0 points awarded for education & qualifications. |
| 12 | `score_structured_attributes` | No explicit qualifications match | Partial credit of 7.5 points awarded as baseline. |
| 13 | `score_structured_attributes` | Location match: Job location is "Remote" or "London, UK", Candidate in "London" | Full 10.0 points awarded due to substring or "remote" detection. |
| 14 | `score_structured_attributes` | Location mismatch: Job in "Manchester", Candidate in "London" | Partial credit of 3.0 points awarded for relocation compatibility. |
| 15 | `MessageBroker` | RabbitMQ server down or unconfigured | Catches connection error in `core/messaging.py:144` and returns singleton `LocalMessageBroker`. |
| 16 | `LocalMessageBroker` | Consumer queue empty during polling | `queue.Empty` exception caught with 0.5s timeout; worker continues loop cleanly. |
| 17 | `BaseAgent` | Duplicate message delivered | Checked against `self.processed_messages` set; duplicate message skipped for idempotency. |
| 18 | `CompanyListAgent` | Universe string contains "100" vs "250" vs unknown | Normalized uppercase: matches "100" to FTSE 100, "250" to FTSE 250; any other string returns combined FTSE 100 + 250 list. |

---

## 4. Functional Requirements Specification

### FR-1: Native Local Execution on Raw Computer Machine (R1)
1. **R1.1 In-Process Message Broker**:
   - The system must provide a thread-safe, in-process queue-based broker (`LocalMessageBroker`) implementing publish-subscribe mechanics.
   - Concurrency must be managed using a `ThreadPoolExecutor` with at least 6 worker threads.
   - Messages must be encapsulated in standard JSON-serializable envelopes containing `message_id`, `correlation_id`, `timestamp`, `source_agent`, `target_agent`, `type`, and `payload`.
2. **R1.2 Relational Database Fallback**:
   - The engine must test PostgreSQL availability with a 3-second connection timeout.
   - If PostgreSQL is absent or unreachable, the system must automatically fall back to an embedded SQLite database at `./job_engine.db`.
   - SQLite connections must support multi-threaded access (`check_same_thread=False`).
3. **R1.3 Vector Database Fallback**:
   - The engine must attempt connection to a remote ChromaDB instance via HTTP client (`CHROMADB_HOST:CHROMADB_PORT`).
   - If the remote ChromaDB server fails heartbeat validation, the system must instantiate a local persistent ChromaDB instance at `./chroma_data`.

### FR-2: LLM Goal & Intent Parameter Extraction (R2.1)
1. **Model Specification**: Google `gemini-3.6-flash`.
2. **Input**: Unstructured natural language search string from user (e.g., `"Find a Management Accountant in the FTSE 250 in London"`).
3. **Output Schema**: Strict JSON object matching `INTENT_SCHEMA`:
   ```json
   {
     "type": "OBJECT",
     "properties": {
       "role": {"type": "STRING"},
       "universe": {"type": "STRING"},
       "filters": {
         "type": "OBJECT",
         "properties": {
           "location": {"type": "STRING"},
           "min_salary": {"type": "NUMBER"},
           "seniority": {"type": "STRING"}
         }
       },
       "candidate_id": {"type": "STRING"}
     },
     "required": ["role", "universe"]
   }
   ```
4. **Configuration**: `temperature=0.1`, `response_mime_type="application/json"`.
5. **Fallback**: If the LLM call fails, the system must default to `role="Management Accountant"`, `universe="FTSE 250"`, `filters={"location": "London"}`.

### FR-3: Structured Job Metadata Extraction from HTML (R2.2)
1. **Model Specification**: Google `gemini-3.6-flash`.
2. **Input**: Unstructured HTML snippet of job posting (truncated to 3,000 characters) and company name hint.
3. **Output Schema**: Strict JSON object matching `JOB_SCHEMA`:
   ```json
   {
     "type": "OBJECT",
     "properties": {
       "title": {"type": "STRING"},
       "company": {"type": "STRING"},
       "location": {"type": "STRING"},
       "description": {"type": "STRING"},
       "requirements": {
         "type": "ARRAY",
         "items": {"type": "STRING"}
       },
       "salary_range": {"type": "STRING"},
       "posted_date": {"type": "STRING"}
     },
     "required": ["title", "description", "requirements"]
   }
   ```
4. **Persistence**: Extracted metadata must be stored in the relational database `job_listings` table.

### FR-4: High-Dimensional Vector Embeddings (R2.3)
1. **Model Specification**: Google `gemini-embedding-2`.
2. **Vector Dimension**: Exactly 3,072 dimensions.
3. **Candidate Embedding Input**: Concatenation of candidate title, professional biography, and key skills:
   $$\text{Text}_{\text{candidate}} = \text{title} \oplus \text{" "} \oplus \text{bio} \oplus \text{" "} \oplus \text{join}(\text{skills})$$
4. **Job Embedding Input**: Concatenation of job title, company name, job description, and requirements:
   $$\text{Text}_{\text{job}} = \text{title} \oplus \text{" "} \oplus \text{company} \oplus \text{" "} \oplus \text{description} \oplus \text{" "} \oplus \text{join}(\text{requirements})$$
5. **Storage**: Upserted into ChromaDB collection `ftse_job_listings` with vector ID, embedding array, document preview (500 chars), and metadata (`company`, `title`).

### FR-5: Transient Error Handling & Exponential Backoff (R2.4)
1. **Library**: `tenacity`.
2. **LLM Retries**:
   - `wait=wait_exponential(multiplier=1, min=1, max=10)`.
   - `stop=stop_after_attempt(3)`.
   - `reraise=True`.
3. **Agent Message Retries**:
   - `wait=wait_exponential(multiplier=1, min=1, max=30)`.
   - `stop=stop_after_attempt(3)`.
   - `reraise=True`.
4. **Target Transient Errors**: HTTP 429 (Rate Limit / Quota Exhausted) and HTTP 503 (Backend Service Unavailable).

### FR-6: Sub-Agent Orchestration & Crawling (R3)
1. **DAG Workflow Stages**:
   - Stage 1: `STAGE_1_COMPANY_LIST` — Constituent discovery.
   - Stage 2: `STAGE_2_JOB_DISCOVERY` — Vacancy search across company portals.
   - Stage 3: `STAGE_3_JOB_PARSING` — HTML parsing and extraction.
   - Stage 4: `STAGE_4_MATCHING` — Vector and structured attribute scoring.
   - Stage 5: `COMPLETED` — Score aggregation and executive summary reporting.
2. **Rate Limiting**: Job search crawler must enforce a minimum delay of 0.2s between requests to the same domain.
3. **Anti-Bot Mitigation**: If live request is blocked (HTTP 403) or returns a generic non-vacancy portal, fall back to resilient carrier vacancy template.

### FR-7: Two-Stage Candidate Matching Algorithm (R4)
1. **Stage 1 (Semantic Pre-Filtering)**: Fast vector cosine similarity between candidate embedding and job embedding. Minimum threshold $\ge 0.65$.
2. **Stage 2 (Multi-Attribute Structured Scoring)**: Structured scoring across 5 weighted dimensions (0 - 100 points).
3. **Hybrid Final Score**: Weighted blend of vector similarity and structured attribute score.
4. **Persistence & Reporting**: Persist match results to `match_results` table, sort descending, and isolate top recommendations with final score $\ge 70$.

---

## 5. Non-Functional Requirements Specification

| ID | Category | Requirement | Specification Metric |
|---|---|---|---|
| **NFR-1** | Portability | Zero External Service Dependency | Must run completely on raw Windows machine without Docker, RabbitMQ, or PostgreSQL services. |
| **NFR-2** | Concurrency | Thread-Safe Broker Operations | In-memory message bus must use thread locks and thread pools (`ThreadPoolExecutor`, `threading.Lock`). |
| **NFR-3** | Idempotency | Duplicate Message Suppression | Agent message handlers must maintain an in-memory or database set of processed `message_id`s to prevent double-processing. |
| **NFR-4** | State Checkpointing | Persistent Workflow Recovery | Every state transition must update the `workflows` table in SQLite/PostgreSQL with UTC timestamp and JSON state payload. |
| **NFR-5** | Scraping Politeness | Domain Rate Limiting | Maximum request rate per target domain must not exceed 5 requests/sec ($\ge 0.2$s inter-request delay). |
| **NFR-6** | Resilient Degradation | Graceful Default Fallback | System must never crash when external APIs (Gemini, career portals) fail; deterministic fallbacks must supply default structures. |

---

## 6. Two-Stage Candidate Matching Algorithm: Detailed Mathematics

### Stage 1: Vector Cosine Similarity Pre-Filtering

Given candidate embedding vector $\mathbf{u} \in \mathbb{R}^{3072}$ and job vacancy embedding vector $\mathbf{v} \in \mathbb{R}^{3072}$:

$$\text{Cosine Similarity}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2} = \frac{\sum_{i=1}^{3072} u_i v_i}{\sqrt{\sum_{i=1}^{3072} u_i^2} \sqrt{\sum_{i=1}^{3072} v_i^2}}$$

#### Threshold Gating Rule:
$$\text{Passed}_{\text{Stage 1}} = \begin{cases} 
\text{True} & \text{if } \text{Cosine Similarity}(\mathbf{u}, \mathbf{v}) \ge 0.65 \\ 
\text{False} & \text{if } \text{Cosine Similarity}(\mathbf{u}, \mathbf{v}) < 0.65 
\end{cases}$$

*Zero-Vector Handling*: If $\|\mathbf{u}\|_2 = 0$ or $\|\mathbf{v}\|_2 = 0$, denominator is 0; the function returns $0.0$.

---

### Stage 2: Multi-Attribute Structured Weighted Scoring

Structured scoring evaluates candidate fit against the job across five weighted dimensions totaling 100 points:

| Dimension | Weight ($W_i$) | Maximum Points | Variable / Logic |
|---|---|---|---|
| **Skill Overlap** | 40% | 40.0 pts | Substring/token overlap ratio with $1.2\times$ scaling factor |
| **Experience Match** | 30% | 30.0 pts | Candidate years vs. required years ratio |
| **Education & Qualifications** | 15% | 15.0 pts | Professional credential check (ACCA, CIMA, ACA) |
| **Location Match** | 10% | 10.0 pts | Substring match or "Remote" designation |
| **Keyword / Domain Fit** | 5% | 5.0 pts | Sector and industry alignment |
| **Total Structured Score** | **100%** | **100.0 pts** | $\sum_{i=1}^5 S_i$ |

#### 1. Skill Overlap Formula (40 Points Max):
Let $C_{\text{skills}}$ be the lowercase set of candidate skills, and $J_{\text{reqs}}$ be the lowercase list of job requirements.  
A requirement $r \in J_{\text{reqs}}$ is considered satisfied if:
$$\exists s \in C_{\text{skills}} \quad \text{such that } s \subseteq r$$

Let $M = \{ r \in J_{\text{reqs}} \mid \exists s \in C_{\text{skills}}, s \subseteq r \}$ be the set of matched requirements.  
The skill match ratio $\rho_{\text{skill}}$ is:
$$\rho_{\text{skill}} = \frac{|M|}{\max(|J_{\text{reqs}}|, 1)}$$

The final skill score $S_{\text{skill}} \in [0.0, 40.0]$ is:
$$S_{\text{skill}} = \min(1.0, \rho_{\text{skill}} \times 1.2) \times 40.0$$

*(Note: The $1.2\times$ factor ensures candidates satisfying $\ge 83.3\%$ of requirements receive the maximum 40.0 points).*

#### 2. Experience Match Formula (30 Points Max):
Let $E_c = \text{candidate.years\_experience}$ (defaults to 5) and $E_j = \text{job.years\_experience}$ (defaults to 3).

$$S_{\text{exp}} = \begin{cases} 
30.0 & \text{if } E_c \ge E_j \\ 
\left( \frac{E_c}{\max(E_j, 1)} \right) \times 30.0 & \text{if } E_c < E_j 
\end{cases}$$

#### 3. Education & Professional Qualifications Formula (15 Points Max):
Let $C_{\text{certs}}$ be candidate qualifications (e.g. `["acca", "cima"]`).

$$S_{\text{edu}} = \begin{cases} 
15.0 & \text{if } \exists c \in C_{\text{certs}} \text{ in } \text{join}(J_{\text{reqs}}) \text{ or } \text{"acca"} \in \text{str}(J) \\ 
7.5 & \text{otherwise (baseline credit)} 
\end{cases}$$

#### 4. Location Match Formula (10 Points Max):
Let $L_c = \text{candidate.location}$ and $L_j = \text{job.location}$.

$$S_{\text{loc}} = \begin{cases} 
10.0 & \text{if } (L_c \subseteq L_j) \lor (L_j \subseteq L_c) \lor (\text{"remote"} \in L_j) \\ 
3.0 & \text{otherwise (partial relocation credit)} 
\end{cases}$$

#### 5. Keyword / Domain Fit Formula (5 Points Max):
$$S_{\text{kw}} = 5.0 \quad (\text{standard domain baseline})$$

#### Total Structured Score:
$$S_{\text{struct}} = \text{round}(S_{\text{skill}} + S_{\text{exp}} + S_{\text{edu}} + S_{\text{loc}} + S_{\text{kw}}, 1) \in [0.0, 100.0]$$

---

### Composite Final Score and Recommendation Ranking

In the reference implementation (`agents/matching_agent.py`), the final ranking score blends Stage 1 semantic similarity and Stage 2 structured scoring:

$$S_{\text{final}} = \text{round}\Big( (\text{Cosine Sim} \times 100 \times 0.40) + (S_{\text{struct}} \times 0.60), 1 \Big)$$

#### Recommendation Threshold:
- Candidates are sorted in descending order of $S_{\text{final}}$.
- High-confidence recommendations are filtered via:
  $$\text{Top Recommendations} = \{ m \in \text{Matches} \mid S_{\text{final}}(m) \ge 70.0 \}_{[:5]}$$

---

## 7. Data Models and Schema Definitions

### 7.1 SQLAlchemy Relational Models (`core/db.py`)

```python
class WorkflowState(Base):
    __tablename__ = 'workflows'
    id = Column(String, primary_key=True)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    data = Column(JSON)

class JobListing(Base):
    __tablename__ = 'job_listings'
    id = Column(String, primary_key=True)
    company = Column(String)
    title = Column(String)
    location = Column(String)
    description = Column(Text)
    requirements = Column(JSON)
    salary_range = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    raw_html = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class MatchResult(Base):
    __tablename__ = 'match_results'
    id = Column(String, primary_key=True)
    workflow_id = Column(String, nullable=True)
    job_id = Column(String)
    candidate_id = Column(String, nullable=True)
    similarity_score = Column(Float)
    structured_score = Column(Float, nullable=True)
    final_score = Column(Float)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 7.2 ChromaDB Vector Collection Schema (`core/vector_db.py`)
- **Collection Name**: `ftse_job_listings`
- **Vector Dimensions**: 3,072
- **ID**: `job_id` (UUID string)
- **Embeddings**: `list[float]` of length 3072
- **Documents**: Concatenated job text summary (truncated to first 500 chars)
- **Metadata**:
  ```json
  {
    "company": "Balfour Beatty plc",
    "title": "Management Accountant"
  }
  ```

### 7.3 Inter-Agent Message Envelope Schema (`core/messaging.py`)
```json
{
  "message_id": "uuid-v4-string",
  "correlation_id": "workflow-id-string",
  "timestamp": "ISO-8601-UTC-string",
  "source_agent": "string (e.g. master, job_search_agent)",
  "target_agent": "string (e.g. matching_agent)",
  "type": "string (task_request | task_response | error)",
  "payload": { ... }
}
```

---

## 8. Gap Analysis & Codebase Observations

During mining of the codebase against `ORIGINAL_REQUEST.md`, four noteworthy implementation observations were identified:

1. **Stage 1 Pre-Filter Gating in `matching_agent.py`**:
   - *Requirement R4*: Specifies "Stage 1: Fast vector cosine similarity pre-filtering (threshold >= 0.65)".
   - *Code Observation*: In `agents/matching_agent.py:108-115`, `cos_sim` is computed and blended into `final_score`, but jobs with `cos_sim < 0.65` are not explicitly filtered out before Stage 2 scoring. If strict pre-filtering is desired, an explicit `if cos_sim < 0.65: continue` gate should discard non-matching roles early.
2. **Tenacity Exception Filtering in `core/llm.py`**:
   - *Requirement R2*: Specifies retry resilience for transient 429 and 503 errors.
   - *Code Observation*: `core/llm.py:6` imports `retry_if_exception_type`, but the `@retry` decorator on lines 15, 27, and 44 does not pass `retry=retry_if_exception_type(...)`. Consequently, it retries on *all* unhandled exceptions rather than solely transient API rate limit / 503 errors.
3. **Datetime Deprecation Warnings**:
   - *Code Observation*: `datetime.utcnow()` is used across `messaging.py`, `db.py`, `master_agent.py`, `job_parsing_agent.py`. In Python 3.12, this produces deprecation warnings recommending timezone-aware objects (`datetime.now(datetime.UTC)`).
4. **Hardcoded Fallbacks vs Live LLM Calls**:
   - *Code Observation*: When `GEMINI_API_KEY` is not present, `master_agent.py` and `job_parsing_agent.py` catch the error and cleanly fall back to deterministic default dictionaries, preserving 100% offline testability.

---

## 9. Verification & Acceptance Testing Status

- **Unit Test Suite**: 5/5 tests passing (`tests/test_broker.py`, `tests/test_db.py`, `tests/test_matching.py`, `tests/test_parser.py`).
- **Mathematical Invariant Verification**:
  - `cosine_similarity([1, 0, 0], [1, 0, 0]) == 1.0` (Verified).
  - `cosine_similarity([1, 0, 0], [0, 1, 0]) == 0.0` (Verified).
  - `cosine_similarity([1, 1, 0], [1, 0, 0]) == 1 / sqrt(2)` (Verified).
  - Structured score for test profile yields $87.5/100$, confirming exact weight calculations (Verified).
- **Execution Command**:
  ```powershell
  pytest -v
  ```
