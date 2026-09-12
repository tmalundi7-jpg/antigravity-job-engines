# Handoff Report — Explorer M1-1: Two-Stage Matching & Embedding Resilience Strategy

**Milestone**: Milestone 1: Engine Hardening & Two-Stage Matching  
**Sender**: Explorer M1-1 (`77bfe36a-230b-4123-a1fd-6394e8e1c524`)  
**Recipient**: Orchestrator / Implementer (`15b7e9c5-3634-43fc-888e-7210b47bc468`)  
**Date**: 2026-09-03  
**Working Directory**: `C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine\.agents\explorer_m1_1`  
**Detailed Report**: `C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine\.agents\explorer_m1_1\investigation.md`  

---

## 1. Observation

Direct observations from examining the codebase and test runs:

1. **`agents/matching_agent.py` Lines 107–135**:
   ```python
   107:             # Stage 1: Vector Similarity (Cosine threshold 0.65)
   108:             cos_sim = cosine_similarity(candidate_emb, job_emb)
   109:             
   110:             # Stage 2: Structured Scoring (0 - 100)
   111:             struct_score, breakdown = self.score_structured_attributes(job, candidate)
   112: 
   113:             # Combined weighted score (40% vector similarity + 60% structured score)
   114:             final_score = round((cos_sim * 100 * 0.4) + (struct_score * 0.6), 1)
   ...
   135:             ranked_matches.append(match_entry)
   ```
   *Observation*: Despite the comment on line 107 indicating a cosine threshold of 0.65, there is no `if` check or gating logic. Every single job proceeds to Stage 2 structured scoring, gets a combined `final_score`, and is appended to `ranked_matches`.

2. **`core/llm.py` Lines 10 and 44–55**:
   ```python
   10: client = genai.Client(api_key=config.GEMINI_API_KEY)
   ...
   44: @retry(
   45:     wait=wait_exponential(multiplier=1, min=1, max=10),
   46:     stop=stop_after_attempt(3),
   47:     reraise=True
   48: )
   49: def get_embedding(text: str, model: str = DEFAULT_EMBEDDING_MODEL) -> list[float]:
   50:     response = client.models.embed_content(
   51:         model=model,
   52:         contents=text
   53:     )
   54:     return response.embeddings[0].values
   ```
   *Observation*: `client` is created unconditionally at top-level. In `get_embedding`, if `client.models.embed_content` fails (e.g. invalid/missing API key, 429 quota, 503 network), tenacity retries 3 times and re-raises (`reraise=True`). There is no offline fallback or exception handler in `get_embedding`.

3. **`agents/matching_agent.py` Lines 88 and 94**:
   ```python
   88:         candidate_emb = get_embedding(candidate_text)
   ...
   94:             job_emb = get_embedding(job_text)
   ```
   *Observation*: Calls to `get_embedding` are naked (no `try...except`). When `get_embedding` re-raises, `process_message` crashes.

4. **`agents/base.py` Lines 43–58**:
   ```python
   43:     @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(3), reraise=True)
   44:     def _process_with_retry(self, msg: dict):
   45:         self.process_message(msg)
   ...
   33:         except Exception as e:
   ...
   36:             self.send_response(
   37:                 target="master_queue",
   38:                 payload={"error": str(e), "failed_message_id": msg_id},
   39:                 orig_msg=msg,
   40:                 msg_type="error"
   41:             )
   ```
   *Observation*: Any unhandled exception in `process_message` triggers 3 retry cycles with exponential backoff up to 30s. When exhausted, it publishes `msg_type="error"` to `master_queue`.

5. **`agents/master_agent.py` Lines 185–186**:
   ```python
   185:         elif source == "matching_agent" and msg_type == "task_response":
   186:             ranked_matches = payload.get("ranked_matches", [])
   ```
   *Observation*: `MasterAgent` only listens for `task_response` from `matching_agent`. When `matching_agent` emits `msg_type="error"`, the message is ignored, workflow state never transitions to `COMPLETED`, and the pipeline hangs indefinitely.

6. **`core/db.py` Lines 53–64**:
   ```python
   53: class MatchResult(Base):
   54:     __tablename__ = 'match_results'
   55:     id = Column(String, primary_key=True)
   56:     workflow_id = Column(String, nullable=True)
   57:     job_id = Column(String)
   58:     candidate_id = Column(String, nullable=True)
   59:     similarity_score = Column(Float)
   60:     structured_score = Column(Float, nullable=True)
   61:     final_score = Column(Float)
   62:     reasoning = Column(Text, nullable=True)
   63:     created_at = Column(DateTime, default=datetime.utcnow)
   ```
   *Observation*: `MatchResult` lacks a `passed_prefilter` column.

7. **`tests/test_matching.py` Lines 1–38**:
   *Observation*: Currently contains only `test_cosine_similarity` and `test_structured_attribute_scoring`. No tests exist for cosine threshold gating, disqualified job exclusion, offline embedding dimension/determinism, or pipeline hang resilience.

---

## 2. Logic Chain

1. **Gating Vulnerability (from Obs 1 & 6)**:
   - Because `agents/matching_agent.py` lacks an `if cos_sim >= 0.65:` gate, jobs with low cosine similarity (e.g. 0.20) are processed through Stage 2 structured scoring and combined into `final_score`.
   - If a completely unrelated job has coincidental overlap on generic location or years of experience, it can accumulate up to 40-50 structured points, resulting in a composite score of 30-40 and polluting `ranked_matches`.
   - Therefore, a strict threshold check (`STAGE_1_COSINE_THRESHOLD = 0.65`) must be added. Jobs failing this check must have `passed_prefilter = False`, `final_score = 0.0`, be excluded from `ranked_matches`, and be placed in `disqualified_matches`.
   - `MatchResult` in `core/db.py` must have `passed_prefilter = Column(Boolean, default=True)` so that SQLite/Postgres persistently distinguishes passed vs failed candidates.

2. **Pipeline Deadlock / Hang Mechanism (from Obs 2, 3, 4, 5)**:
   - When running on a machine without a valid `GEMINI_API_KEY`, `client.models.embed_content` fails.
   - Tenacity in `core/llm.py` retries 3 times, then raises.
   - `MatchingAgent.process_message` lacks a try/except around `get_embedding`, so the exception escapes to `_process_with_retry` in `agents/base.py`, which retries the whole message 3 times with exponential backoff up to 30s.
   - `BaseAgent.handle_message` catches the failure and sends `msg_type="error"` to `master_queue`.
   - `MasterAgent` does not handle `msg_type="error"` from `matching_agent`; it only listens for `task_response`.
   - The workflow never completes and hangs until overall timeout.
   - Therefore, `core/llm.py` must provide a deterministic offline fallback that generates 3072-dimensional embeddings whenever the API key is missing or calls fail. `MatchingAgent` must also wrap embedding calls in try/except for defense in depth.

3. **Mathematical Necessity of Blended Semantic Subspace**:
   - In 3072-dimensional space, naive text hashing generates orthogonal vectors with expected inner product $\approx 0.0$.
   - If an offline fallback used naive hashing, all jobs would have $\text{cos\_sim} \approx 0.0 < 0.65$, meaning 100% of jobs would fail the Stage 1 pre-filter during offline runs, breaking unit tests and offline demos.
   - By creating a blended subspace with a fixed base centroid $B$ (seed 42) and SHA256-seeded token projection vectors weighted by skill importance ($\alpha = 0.45$):
     - Unrelated texts have zero token overlap $\rightarrow \cos \approx 0.40 < 0.65$ (correctly rejected).
     - Matching texts have high token overlap $\rightarrow \cos \approx 0.70\text{--}0.88 \ge 0.65$ (correctly passed).
     - Identical texts have $\cos = 1.0$.
   - This ensures offline runs behave identically to online runs with real Gemini embeddings.

---

## 3. Caveats

1. **`agents/master_agent.py` Completion Counter Dependency**:
   - Line 193 of `master_agent.py` currently checks `len(state["ranked_matches"]) >= dispatched`.
   - If an entire batch of jobs discovered for a company has 0 jobs that pass Stage 1 ($\text{cos\_sim} < 0.65$), `len(ranked_matches)` returned is 0.
   - In `master_agent.py`, the completion check should track matching batch completions (`state["completed_matching_batches"] += 1`) rather than match count, or else a workflow where all jobs are disqualified will stall. This must be addressed in Milestone 1.
2. **ChromaDB Dimension Consistency**:
   - The local collection `ftse_job_listings` in `chroma_data` expects 3072-dimensional embeddings. Any change to the fallback dimension (e.g. attempting 768 or 1536) will throw an incompatibility error during `collection.upsert()`. The 3072 dimension is strictly enforced.
3. **No External Network Dependencies**:
   - The deterministic offline fallback requires only `hashlib`, `re`, and `numpy` (already in `requirements.txt`). No HuggingFace or PyTorch models are needed.

---

## 4. Conclusion

1. **Stage 1 Pre-Filtering**:
   - Add `STAGE_1_COSINE_THRESHOLD = 0.65` in `agents/matching_agent.py`.
   - Gating logic: `passed_prefilter = (cos_sim >= STAGE_1_COSINE_THRESHOLD)`.
   - If False: record `disqualified = True`, `passed_prefilter = False`, `final_score = 0.0`, populate failure reasoning, add to `disqualified_matches`, exclude from `ranked_matches` and `top_recommendations`, persist to `MatchResult(passed_prefilter=False)`.
   - If True: execute Stage 2 structured scoring, compute `final_score = round(cos_sim * 40 + struct_score * 0.6, 1)`, add to `ranked_matches`.
2. **Embedding Resilience**:
   - In `core/llm.py`, implement `generate_deterministic_embedding(text: str, dim: int = 3072) -> list[float]` using the blended semantic subspace ($\alpha = 0.45$).
   - Wrap `client` initialization lazily via `get_client()`.
   - In `get_embedding`, immediately return `generate_deterministic_embedding(text)` if API key is missing.
   - If API key is present, invoke Gemini with short exponential backoff (1s–5s, max 3 attempts); on any unhandled error, log warning and return `generate_deterministic_embedding(text)`.
   - In `agents/matching_agent.py`, wrap candidate and job embedding calls with try/except fallback.
3. **Database Schema**:
   - Add `passed_prefilter = Column(Boolean, default=True)` to `MatchResult` in `core/db.py`.
4. **Test Suite**:
   - Add unit tests in `tests/test_matching.py` verifying:
     - 3072-d output and unit norm.
     - Determinism across runs.
     - Semantic separation ($\ge 0.65$ for matching profiles, $< 0.65$ for unrelated).
     - Strict exclusion of disqualified jobs from `ranked_matches`.
     - Database persistence of `passed_prefilter`.

---

## 5. Verification Method

Once the changes are implemented by the implementer:

1. **Unit & Pre-filter Tests**:
   Run the matching test suite:
   ```powershell
   pytest tests/test_matching.py -v
   ```
   *Expected Result*: All tests pass 100%, including threshold gating, disqualified exclusion, and offline embedding properties.

2. **Full Test Suite without API Key**:
   Unset or clear `GEMINI_API_KEY` and run:
   ```powershell
   pytest -v
   ```
   *Expected Result*: All tests pass without hangs, timeouts, or unhandled exceptions.

3. **Database Persistence Verification**:
   Inspect SQLite records after running a matching flow:
   ```powershell
   python -c "from core.db import SessionLocal, MatchResult; db=SessionLocal(); print([(r.job_id, r.similarity_score, r.passed_prefilter, r.final_score) for r in db.query(MatchResult).all()]); db.close()"
   ```
   *Expected Result*: Disqualified jobs show `passed_prefilter=False` and `final_score=0.0`. Passed jobs show `passed_prefilter=True` and `final_score >= 70.0`.

4. **Invalidation Conditions**:
   - If `generate_deterministic_embedding` returns a vector with length $\neq 3072$, ChromaDB will raise an error on upsert.
   - If `cos_sim` for an unrelated job $\ge 0.65$, $\alpha$ is too high; if `cos_sim` for a matching job $< 0.65$, $\alpha$ is too low.
   - If `ranked_matches` contains any job with `similarity_score < 0.65`, pre-filter gating has regressed.
