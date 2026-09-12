# Original User Request

## Initial Request — 2026-09-03T01:13:44Z

Multi-agent job search and matching engine for FTSE companies orchestrating web scraping, job parsing, and candidate matching.

Working directory: C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine
Integrity mode: development

## Requirements

### R1. Native Local Execution on Raw Computer Machine
The engine must run reliably on the host computer without requiring external Docker Desktop or cloud services to be pre-started. Includes:
- In-process thread-safe message broker (`LocalMessageBroker`) fallback when RabbitMQ is absent.
- Auto-fallback to local SQLite (`job_engine.db`) when PostgreSQL is not running.
- Auto-fallback to embedded persistent ChromaDB (`./chroma_data`) when ChromaDB HTTP server is not running.

### R2. LLM Integration with Gemini
- Extract search parameters from unstructured user goals using `gemini-3.6-flash` and JSON structured schema.
- Extract structured job metadata (title, requirements, salary, location) from unstructured HTML listings.
- Generate high-dimensional vector embeddings using `gemini-embedding-2`.
- Resilient fault tolerance using `tenacity` exponential backoff retries for transient 503/429 spikes.

### R3. Web Crawling & Sub-Agent Orchestration
- Master Agent decomposes goals into a Directed Acyclic Graph (DAG) across 5 stages: Company Discovery, Job Discovery, Job Parsing, Candidate Matching, and Executive Reporting.
- Job Search Agent handles rate limiting (max requests/second), pagination detection, and anti-bot mitigation.

### R4. Two-Stage Candidate Matching Algorithm
- Stage 1: Fast vector cosine similarity pre-filtering (threshold >= 0.65).
- Stage 2: Multi-attribute structured weighted scoring:
  - Skill Overlap (40%)
  - Experience Match (30%)
  - Education & Professional Qualifications (15%)
  - Location Match (10%)
  - Keyword / Domain Fit (5%)
- Persist structured results, workflow checkpoints, and ranked recommendations to database.

## Acceptance Criteria

### Automated Verification
- [x] Pytest test suite passes 100% locally on raw machine (`tests/test_broker.py`, `tests/test_db.py`, `tests/test_matching.py`, `tests/test_parser.py`).
- [x] End-to-end pipeline test completes from high-level goal to final ranked match report.
- [x] Correct Gemini models configured and verified (`gemini-3.6-flash`, `gemini-embedding-2`).
- [x] SQLite database records workflow states and job listing models.
- [x] ChromaDB persists 3072-dimensional embeddings locally to disk.
