## 2026-09-03T01:15:17Z

You are the Project Orchestrator for the project: Multi-agent job search and matching engine for FTSE companies orchestrating web scraping, job parsing, and candidate matching.

Workspace directory: C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine
Your working directory: C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine\.agents\orchestrator_1
Original Request: Read C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine\ORIGINAL_REQUEST.md

Key Requirements:
R1. Native Local Execution on Raw Computer Machine (LocalMessageBroker fallback for RabbitMQ, SQLite fallback for PostgreSQL, ChromaDB persistent ./chroma_data fallback for Chroma server).
R2. LLM Integration with Gemini (gemini-3.6-flash for search params & job extraction, gemini-embedding-2 for 3072-dim embeddings, tenacity backoff retries).
R3. Web Crawling & Sub-Agent Orchestration (Master Agent 5-stage DAG: Company Discovery, Job Discovery, Job Parsing, Candidate Matching, Executive Reporting; Job Search Agent rate limiting, pagination, anti-bot).
R4. Two-Stage Candidate Matching Algorithm (Stage 1: vector cosine pre-filtering >= 0.65; Stage 2: multi-attribute weighted scoring [Skill 40%, Experience 30%, Education 15%, Location 10%, Domain Fit 5%]; persist to DB).
Acceptance criteria:
- Pytest test suite passes 100% locally on raw machine (tests/test_broker.py, tests/test_db.py, tests/test_matching.py, tests/test_parser.py).
- End-to-end pipeline test completes from high-level goal to final ranked match report.
- Correct Gemini models configured and verified (gemini-3.6-flash, gemini-embedding-2).
- SQLite records workflow states and job listing models.
- ChromaDB persists 3072-dimensional embeddings locally to disk.

Maintain your BRIEFING.md, plan.md, and progress.md in your working directory C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine\.agents\orchestrator_1.
When done, report back to your parent sentinel.
