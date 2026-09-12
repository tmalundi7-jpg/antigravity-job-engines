# Plan — Multi-Agent Job Search & Matching Engine

## Phase 0: Scope & Codebase Survey
- Dispatch 3 Explorers (teamwork_preview_explorer & teamwork_preview_spec_miner) in parallel to:
  - Explorer 1: Inspect existing project structure, core modules, existing implementations, config, and tests.
  - Explorer 2: Analyze Gemini LLM integration requirements (gemini-3.6-flash, gemini-embedding-2, 3072-dim embeddings, tenacity retry logic).
  - Explorer 3: Analyze the 5-stage DAG architecture (Master Agent, Job Search Agent, rate limiting, anti-bot, two-stage matching algorithm, SQLite & local ChromaDB fallbacks).
- Synthesize all findings into `PROJECT.md` Feature Inventory and Milestone plan.

## Phase 1: Milestones & Interface Contracts
- Define milestones, dependencies, and interface contracts in `PROJECT.md`.
- Ensure all R1-R4 requirements and automated acceptance criteria are accounted for.

## Phase 2: Iteration Loops for Each Milestone
- Milestone execution following the Project Pattern:
  - 3 Explorers -> 1 Worker -> 2 Reviewers -> 2 Challengers -> 1 Forensic Auditor -> Gate evaluation.
- Test and verify locally on raw computer machine (LocalMessageBroker, SQLite fallback, persistent ChromaDB).

## Phase 3: Final End-to-End Verification
- Run full pytest test suite (test_broker.py, test_db.py, test_matching.py, test_parser.py).
- Verify end-to-end pipeline execution from high-level goal to final ranked report.
- Verify Gemini model configuration and ChromaDB 3072-dim vector persistence.
- Forensic Auditor clean verification.

## Phase 4: Reporting & Hand-off
- Produce final executive and technical reports.
- Report back to Sentinel with complete verification results.
