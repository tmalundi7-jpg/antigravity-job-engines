import uuid
import pytest
import numpy as np
from unittest.mock import MagicMock
from agents.matching_agent import cosine_similarity, MatchingAgent, STAGE_1_COSINE_THRESHOLD
from core.llm import generate_deterministic_embedding, get_embedding, EMBEDDING_DIM
from core.db import SessionLocal, MatchResult, init_db


def create_base_unit_vector(dim: int = 3072, seed: int = 42) -> list[float]:
    rng = np.random.RandomState(seed)
    raw = rng.standard_normal(dim)
    unit = raw / np.linalg.norm(raw)
    return unit.tolist()


def create_correlated_vector(base_vec: list[float], target_cos_sim: float, seed: int = 12345) -> list[float]:
    """
    Construct a unit vector v in R^dim such that cosine_similarity(base_vec, v) == target_cos_sim exactly.
    Uses Gram-Schmidt orthogonalization: v = target_cos_sim * u + sqrt(1 - target_cos_sim^2) * w
    where w is orthogonal to u.
    """
    u = np.array(base_vec, dtype=float)
    u = u / np.linalg.norm(u)
    dim = len(u)

    rng = np.random.RandomState(seed)
    w_raw = rng.standard_normal(dim)
    # Gram-Schmidt projection: make w orthogonal to u
    w_proj = w_raw - np.dot(w_raw, u) * u
    w = w_proj / np.linalg.norm(w_proj)

    # Combine
    v = target_cos_sim * u + np.sqrt(max(0.0, 1.0 - target_cos_sim ** 2)) * w
    v = v / np.linalg.norm(v)

    return v.tolist()


# ==============================================================================
# 1. STAGE 1 COSINE SIMILARITY THRESHOLD GATING STRESS TESTS
# ==============================================================================

@pytest.mark.parametrize("sim, should_pass", [
    (0.0, False),
    (0.500, False),
    (0.600, False),
    (0.640, False),
    (0.649, False),
    (0.6499, False),
    (0.6500, True),
    (0.6501, True),
    (0.651, True),
    (0.700, True),
    (0.850, True),
    (1.000, True),
])
def test_stage_1_exact_threshold_boundary(sim, should_pass):
    """
    Rigorously verifies the Stage 1 cosine similarity threshold at exactly 0.65.
    Tests boundary conditions including 0.649 vs 0.651 and 0.6499 vs 0.6500.
    Uses constructor DI so the mock embed_fn is baked in at construction time.
    """
    import chromadb
    init_db()

    cand_vec = create_base_unit_vector(seed=777)
    job_vec = create_correlated_vector(cand_vec, sim, seed=888)
    actual_cos_sim = cosine_similarity(cand_vec, job_vec)
    assert np.isclose(actual_cos_sim, sim, atol=1e-5), (
        f"Synthesized cosine similarity mismatch: {actual_cos_sim} vs {sim}"
    )

    # Build mock embed_fn and inject via DI constructor
    call_count = [0]
    def mock_embed_fn(text, model=None):
        call_count[0] += 1
        return cand_vec if call_count[0] == 1 else job_vec

    chroma = chromadb.Client()
    coll = chroma.get_or_create_collection(f"stress_thresh_{int(sim * 10000)}")
    agent = MatchingAgent(embed_fn=mock_embed_fn, collection=coll)

    job_id = f"job_thresh_{int(sim * 10000)}"
    wf_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "title": "Finance Analyst",
        "company": "Test Company",
        "location": "London",
        "requirements": ["ACCA", "Excel"],
        "years_experience": 3
    }
    candidate = {
        "id": "cand_thresh_test",
        "title": "Senior Accountant",
        "skills": ["ACCA", "Excel"],
        "years_experience": 5,
        "location": "London"
    }

    test_msg = {
        "correlation_id": wf_id,
        "payload": {
            "candidate": candidate,
            "parsed_jobs": [job]
        }
    }

    dispatched = {}
    def mock_send_response(target, payload, orig_msg, msg_type="task_response"):
        dispatched["target"] = target
        dispatched["payload"] = payload

    agent.send_response = mock_send_response
    agent.process_message(test_msg)

    payload = dispatched.get("payload", {})
    ranked = payload.get("ranked_matches", [])
    disqualified = payload.get("disqualified_matches", [])

    if should_pass:
        assert len(ranked) == 1, (
            f"Expected job with similarity {sim} to pass Stage 1, but was not in ranked_matches"
        )
        assert len(disqualified) == 0, (
            f"Expected 0 disqualified jobs, got {len(disqualified)}"
        )
        assert ranked[0]["job_id"] == job_id
        assert ranked[0]["passed_prefilter"] is True
        assert ranked[0]["disqualified"] is False
        assert ranked[0]["final_score"] > 0.0
        assert np.isclose(ranked[0]["similarity_score"], round(sim, 3), atol=1e-3)
    else:
        assert len(ranked) == 0, (
            f"Expected job with similarity {sim} to be excluded from ranked_matches, but found in ranked"
        )
        assert len(disqualified) == 1, (
            f"Expected job with similarity {sim} to be in disqualified_matches"
        )
        assert disqualified[0]["job_id"] == job_id
        assert disqualified[0]["passed_prefilter"] is False
        assert disqualified[0]["disqualified"] is True
        assert disqualified[0]["final_score"] == 0.0
        assert disqualified[0]["structured_score"] == 0.0
        assert "Disqualified" in disqualified[0]["reasoning"]

    # Verify DB persistence state
    with SessionLocal() as db:
        mr = db.query(MatchResult).filter(
            MatchResult.job_id == job_id,
            MatchResult.workflow_id == wf_id
        ).first()
        assert mr is not None, "MatchResult record was not persisted to DB"
        if should_pass:
            assert mr.passed_prefilter is True
            assert mr.final_score > 0.0
        else:
            assert mr.passed_prefilter is False
            assert mr.final_score == 0.0
            assert mr.structured_score == 0.0


# ==============================================================================
# 2. DISQUALIFICATION INTEGRITY & RECOMMENDATION PURITY TESTS
# ==============================================================================

def test_disqualified_candidates_complete_exclusion():
    """
    Verifies that candidates below 0.65 are completely excluded from ranked recommendations
    and top recommendations, even if their structured attributes are 100% perfect.
    """
    import chromadb
    init_db()

    # Base candidate vector
    cand_vec = create_base_unit_vector(seed=1)

    # 4 jobs constructed relative to cand_vec:
    # Job 1: Perfect structured match, but cos_sim = 0.649 (disqualified)
    # Job 2: Good structured match, cos_sim = 0.680 (qualified)
    # Job 3: Unrelated, cos_sim = 0.200 (disqualified)
    # Job 4: Excellent structured match, cos_sim = 0.900 (qualified, should be top recommendation)
    vec_j1 = create_correlated_vector(cand_vec, 0.649, seed=101)
    vec_j2 = create_correlated_vector(cand_vec, 0.680, seed=102)
    vec_j3 = create_correlated_vector(cand_vec, 0.200, seed=103)
    vec_j4 = create_correlated_vector(cand_vec, 0.900, seed=104)

    assert np.isclose(cosine_similarity(cand_vec, vec_j1), 0.649, atol=1e-4)
    assert np.isclose(cosine_similarity(cand_vec, vec_j2), 0.680, atol=1e-4)
    assert np.isclose(cosine_similarity(cand_vec, vec_j3), 0.200, atol=1e-4)
    assert np.isclose(cosine_similarity(cand_vec, vec_j4), 0.900, atol=1e-4)

    job_vectors = {
        "job_1": vec_j1,
        "job_2": vec_j2,
        "job_3": vec_j3,
        "job_4": vec_j4,
    }

    def mock_embed_fn(text, model=None):
        for jid, v in job_vectors.items():
            if jid in text:
                return v
        return cand_vec

    chroma = chromadb.Client()
    coll = chroma.get_or_create_collection("disq_exclusion")
    agent = MatchingAgent(embed_fn=mock_embed_fn, collection=coll)

    candidate = {
        "id": "cand_alex",
        "title": "Senior Management Accountant",
        "skills": ["ACCA", "Financial Reporting", "Variance Analysis", "Excel", "Budgeting", "CIMA"],
        "years_experience": 6,
        "certifications": ["ACCA Qualified"],
        "location": "London"
    }

    parsed_jobs = [
        {
            "job_id": "job_1",
            "title": "job_1 Perfect Structured Accountant",
            "company": "Company A",
            "location": "London",
            "requirements": ["ACCA", "CIMA", "Excel", "Variance Analysis", "Budgeting", "Financial Reporting"],
            "years_experience": 3
        },
        {
            "job_id": "job_2",
            "title": "job_2 Finance Analyst",
            "company": "Company B",
            "location": "London",
            "requirements": ["ACCA", "Excel"],
            "years_experience": 4
        },
        {
            "job_id": "job_3",
            "title": "job_3 Warehouse Operative",
            "company": "Company C",
            "location": "Manchester",
            "requirements": ["Forklift", "Physical Stamina"],
            "years_experience": 1
        },
        {
            "job_id": "job_4",
            "title": "job_4 Group Financial Controller",
            "company": "Company D",
            "location": "London",
            "requirements": ["ACCA", "Financial Reporting", "Variance Analysis", "Budgeting"],
            "years_experience": 5
        },
    ]

    wf_id = str(uuid.uuid4())
    dispatched = {}
    agent.send_response = lambda target, payload, orig_msg, **kw: dispatched.update(payload=payload)

    agent.process_message({
        "correlation_id": wf_id,
        "payload": {
            "candidate": candidate,
            "parsed_jobs": parsed_jobs
        }
    })

    payload = dispatched.get("payload", {})
    ranked = payload.get("ranked_matches", [])
    disqualified = payload.get("disqualified_matches", [])
    top_recs = payload.get("top_recommendations", [])

    # Total counts
    assert payload["total_evaluated"] == 4
    assert payload["passed_count"] == 2
    assert payload["disqualified_count"] == 2

    # Verify ranked matches contains ONLY job_4 and job_2, in descending final_score order
    ranked_ids = [m["job_id"] for m in ranked]
    assert "job_4" in ranked_ids
    assert "job_2" in ranked_ids
    assert "job_1" not in ranked_ids, "CRITICAL BUG: job_1 (sim=0.649) leaked into ranked_matches!"
    assert "job_3" not in ranked_ids, "CRITICAL BUG: job_3 (sim=0.200) leaked into ranked_matches!"

    # Verify descending sort order
    scores = [m["final_score"] for m in ranked]
    assert scores == sorted(scores, reverse=True), "Ranked matches are not sorted descending by final_score"

    # Verify top recommendations
    top_ids = [m["job_id"] for m in top_recs]
    assert "job_1" not in top_ids, "CRITICAL BUG: Disqualified job_1 leaked into top_recommendations!"
    assert "job_3" not in top_ids, "CRITICAL BUG: Disqualified job_3 leaked into top_recommendations!"
    for rec in top_recs:
        assert rec["final_score"] >= 70.0

    # Verify disqualified list
    disq_ids = [d["job_id"] for d in disqualified]
    assert "job_1" in disq_ids
    assert "job_3" in disq_ids
    for d in disqualified:
        assert d["final_score"] == 0.0
        assert d["structured_score"] == 0.0
        assert d["passed_prefilter"] is False
        assert d["disqualified"] is True


def test_all_jobs_disqualified_resilience():
    """
    Verifies that when 100% of jobs fail Stage 1:
    - No unhandled exceptions / index errors occur
    - ranked_matches and top_recommendations are empty lists
    - disqualified_count == total_evaluated
    """
    import chromadb
    init_db()

    # Candidate has base unit vector; all jobs have cos_sim = 0.30 to candidate
    cand_vec = create_base_unit_vector(seed=42)

    def mock_embed_fn(text, model=None):
        if "Accountant" in text and "cand" in text.lower():
            return cand_vec
        # Each job gets a vector correlated with cand_vec at sim=0.30
        seed = abs(hash(text)) % 100000 + 10
        return create_correlated_vector(cand_vec, 0.30, seed=seed)

    chroma = chromadb.Client()
    coll = chroma.get_or_create_collection("all_disq")
    agent = MatchingAgent(embed_fn=mock_embed_fn, collection=coll)

    jobs = [
        {"job_id": f"unrelated_{i}", "title": f"Unrelated Role {i}", "requirements": ["Skill"]}
        for i in range(5)
    ]

    dispatched = {}
    agent.send_response = lambda target, payload, orig_msg, **kw: dispatched.update(payload=payload)

    # Should not raise any IndexError or AttributeError
    agent.process_message({
        "correlation_id": "test_all_disq",
        "payload": {
            "candidate": {"id": "cand_01", "title": "Accountant", "skills": ["ACCA"]},
            "parsed_jobs": jobs
        }
    })

    payload = dispatched.get("payload", {})
    assert payload["total_evaluated"] == 5
    assert payload["passed_count"] == 0
    assert payload["disqualified_count"] == 5
    assert payload["ranked_matches"] == []
    assert payload["top_recommendations"] == []


# ==============================================================================
# 3. VECTOR DIMENSION AND NORMALIZATION INVARIANTS
# ==============================================================================

def test_deterministic_embedding_dimension_and_unit_norm_stress():
    """
    Empirically verifies the invariant that all generated embeddings
    are strictly 3072 floats and unit-normalized across diverse, adversarial text inputs.
    """
    adversarial_inputs = [
        # Empty & whitespace
        "",
        "   ",
        "\t\n\r\n",
        # Single characters & tiny tokens
        "a",
        "ab",
        "1",
        # Punctuation & special chars
        "!@#$%^&*()_+{}[]:;\"'<>?,./~`",
        # Emojis & multi-byte UTF-8
        "🚀 💻 💼 📈 💰 🏢 🇬🇧",
        # Non-Latin scripts (Arabic, Cyrillic, Chinese, Greek)
        "محاسب قانوني خبير مالي",
        "Главный бухгалтер МСФО отчетность",
        "高级财务会计师 预算管理 审计",
        "Ορκωτός Ελεγκτής Λογιστής",
        # Pure stop-words
        "the and with for that this from are was were been have has had will would about into over after role team join",
        # Pure numbers
        "100200 400500 999999 123456789",
        # Massive input (10,000 words)
        "ACCA CIMA Financial Reporting Excel Variance Analysis " * 2000,
        # Standard realistic job descriptions
        "Senior Management Accountant Balfour Beatty London ACCA CIMA Excel Variance Analysis Budgeting Forecasting SAP",
        "Junior Data Engineer Python SQL Snowflake Airflow ETL Pipeline GCP AWS Docker",
        "Head of Treasury FX Hedging Liquidity Capital Markets FTSE 100 London"
    ]

    for idx, text in enumerate(adversarial_inputs):
        emb = generate_deterministic_embedding(text, dim=3072)

        # 1. Type and length invariant
        assert isinstance(emb, list), f"Input #{idx}: Output is not a list"
        assert len(emb) == 3072, f"Input #{idx}: Embedding dimension is {len(emb)}, expected 3072"

        # 2. Float elements invariant
        assert all(isinstance(x, (float, np.floating)) for x in emb), f"Input #{idx}: Non-float elements detected"

        # 3. Finite numbers (no NaN, no Inf)
        emb_arr = np.array(emb, dtype=float)
        assert np.isfinite(emb_arr).all(), f"Input #{idx}: NaN or Inf detected in embedding"

        # 4. Unit norm invariant (norm == 1.0 within 1e-4)
        norm = np.linalg.norm(emb_arr)
        assert np.isclose(norm, 1.0, atol=1e-4), f"Input #{idx}: Vector norm is {norm}, expected 1.0"

        # 5. Determinism invariant
        emb_repeat = generate_deterministic_embedding(text, dim=3072)
        assert np.allclose(emb_arr, np.array(emb_repeat, dtype=float)), f"Input #{idx}: Non-deterministic embedding output"


def test_get_embedding_api_fallback_invariants(monkeypatch):
    """
    Verifies that get_embedding always returns a 3072-dimensional unit vector
    under API success, API failure (quota 429 / 503), and absent API key.
    """
    # 1. Fallback when get_client() returns None
    monkeypatch.setattr("core.llm.get_client", lambda: None)
    emb_no_key = get_embedding("Financial Analyst London ACCA")
    assert len(emb_no_key) == 3072
    assert np.isclose(np.linalg.norm(emb_no_key), 1.0, atol=1e-4)

    # 2. Fallback when API throws 429 / ResourceExhausted
    mock_client = MagicMock()
    mock_client.models.embed_content.side_effect = RuntimeError("429 ResourceExhausted: quota exceeded")
    monkeypatch.setattr("core.llm.get_client", lambda: mock_client)

    emb_quota = get_embedding("Senior Management Accountant")
    assert len(emb_quota) == 3072
    assert np.isclose(np.linalg.norm(emb_quota), 1.0, atol=1e-4)

    # 3. API success returns 3072 floats
    mock_response = MagicMock()
    rng = np.random.RandomState(99)
    raw_vec = rng.standard_normal(3072)
    sample_vec = (raw_vec / np.linalg.norm(raw_vec)).tolist()
    mock_response.embeddings = [MagicMock(values=sample_vec)]
    mock_client.models.embed_content.side_effect = None
    mock_client.models.embed_content.return_value = mock_response

    # Reset quota flag
    import core.llm
    core.llm._QUOTA_EXHAUSTED = False

    emb_api = get_embedding("Treasury Manager London")
    assert len(emb_api) == 3072
    assert np.isclose(np.linalg.norm(emb_api), 1.0, atol=1e-4)


# ==============================================================================
# 4. EDGE CASES: ZERO-NORM, ORTHOGONAL, EMPTY REQUIREMENTS, LOCATION MISMATCH
# ==============================================================================

def test_cosine_similarity_edge_cases():
    """
    Tests cosine similarity function on extreme vector topologies:
    - zero-norm vectors
    - orthogonal vectors
    - anti-parallel vectors
    - identical vectors
    """
    dim = 3072
    zero_vec = [0.0] * dim
    unit_u = [0.0] * dim
    unit_u[0] = 1.0
    unit_w = [0.0] * dim
    unit_w[1] = 1.0

    # Zero-norm: must return 0.0 without ZeroDivisionError
    assert cosine_similarity(zero_vec, zero_vec) == 0.0
    assert cosine_similarity(zero_vec, unit_u) == 0.0
    assert cosine_similarity(unit_u, zero_vec) == 0.0

    # Orthogonal: must return 0.0
    assert np.isclose(cosine_similarity(unit_u, unit_w), 0.0)

    # Anti-parallel: must return -1.0
    neg_u = [-x for x in unit_u]
    assert np.isclose(cosine_similarity(unit_u, neg_u), -1.0)

    # Identical: must return 1.0
    assert np.isclose(cosine_similarity(unit_u, unit_u), 1.0)


def test_structured_scoring_edge_cases():
    """
    Stress-tests score_structured_attributes on boundary cases:
    - empty requirements
    - mismatched locations
    - zero vs high experience
    - missing certifications
    """
    agent = MatchingAgent()

    # 1. Empty requirements
    job_empty_reqs = {
        "title": "Accountant",
        "requirements": [],
        "years_experience": 2,
        "location": "London"
    }
    candidate = {
        "title": "Accountant",
        "skills": ["ACCA", "Excel"],
        "years_experience": 5,
        "certifications": ["ACCA"],
        "location": "London"
    }
    score, breakdown = agent.score_structured_attributes(job_empty_reqs, candidate)
    assert score >= 0.0
    assert breakdown["skills"] == 0.0  # 0 matched
    assert breakdown["experience"] == 30.0  # 5 >= 2
    assert breakdown["location"] == 10.0

    # 2. Location mismatch
    job_mismatched_loc = {
        "title": "Accountant",
        "requirements": ["ACCA"],
        "years_experience": 2,
        "location": "Edinburgh"
    }
    cand_london = {
        "title": "Accountant",
        "skills": ["ACCA"],
        "years_experience": 2,
        "certifications": ["ACCA"],
        "location": "London"
    }
    score_loc, breakdown_loc = agent.score_structured_attributes(job_mismatched_loc, cand_london)
    assert breakdown_loc["location"] == 3.0  # Mismatched location yields 3.0 out of 10.0

    # 3. Remote job matches any candidate location
    job_remote = {
        "title": "Accountant",
        "requirements": ["ACCA"],
        "years_experience": 2,
        "location": "Remote / UK"
    }
    _, breakdown_remote = agent.score_structured_attributes(job_remote, cand_london)
    assert breakdown_remote["location"] == 10.0  # Remote qualifies for full 10 points

    # 4. Zero experience candidate against high requirement
    cand_zero_exp = {
        "title": "Graduate",
        "skills": ["ACCA"],
        "years_experience": 0,
        "certifications": [],
        "location": "London"
    }
    job_senior = {
        "title": "Director",
        "requirements": ["ACCA"],
        "years_experience": 10,
        "location": "London"
    }
    _, breakdown_senior = agent.score_structured_attributes(job_senior, cand_zero_exp)
    assert breakdown_senior["experience"] == 0.0


def test_adversarial_none_type_behavior_reproduction():
    """
    Empirical bug reproduction: Tests how MatchingAgent handles explicit None
    values for optional schema fields in candidate and job objects.
    
    Demonstrates whether score_structured_attributes or process_message raises
    TypeError when fields like candidate.skills or job.requirements are None.
    """
    agent = MatchingAgent()

    job_with_none_reqs = {
        "title": "Analyst",
        "requirements": None,
        "location": "London",
        "years_experience": 2
    }
    cand_with_none_skills = {
        "title": "Analyst",
        "skills": None,
        "certifications": ["ACCA"],
        "location": "London",
        "years_experience": 3
    }

    # Empirically verify that Passing None for skills or requirements raises TypeError
    with pytest.raises(TypeError, match="object is not iterable"):
        agent.score_structured_attributes(job_with_none_reqs, cand_with_none_skills)
