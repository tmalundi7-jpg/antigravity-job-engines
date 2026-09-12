import pytest
import numpy as np
from agents.matching_agent import cosine_similarity, MatchingAgent, STAGE_1_COSINE_THRESHOLD
from core.llm import generate_deterministic_embedding, get_embedding
from core.db import SessionLocal, MatchResult, init_db


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert np.isclose(cosine_similarity(v1, v2), 1.0)

    v3 = [0.0, 1.0, 0.0]
    assert np.isclose(cosine_similarity(v1, v3), 0.0)

    v4 = [1.0, 1.0, 0.0]
    assert np.isclose(cosine_similarity(v1, v4), 1.0 / np.sqrt(2))


def test_structured_attribute_scoring():
    agent = MatchingAgent()
    job = {
        "title": "Management Accountant",
        "company": "Balfour Beatty",
        "location": "London",
        "requirements": ["ACCA", "CIMA", "Excel", "Variance Analysis"],
        "years_experience": 3
    }
    candidate = {
        "title": "Senior Management Accountant",
        "skills": ["ACCA", "CIMA", "Excel", "Budgeting", "Variance Analysis"],
        "years_experience": 5,
        "certifications": ["ACCA Qualified"],
        "location": "London"
    }
    score, breakdown = agent.score_structured_attributes(job, candidate)

    assert score >= 70.0
    assert breakdown["experience"] == 30.0  # Full experience points (5 >= 3)
    assert breakdown["location"] == 10.0   # London match
    assert breakdown["education"] == 15.0  # ACCA certified


def test_deterministic_offline_embedding_properties():
    # 1. Dimension and unit norm
    emb1 = generate_deterministic_embedding("Senior Management Accountant ACCA Excel")
    assert len(emb1) == 3072
    norm1 = np.linalg.norm(emb1)
    assert np.isclose(norm1, 1.0, atol=1e-4)

    # 2. Determinism
    emb2 = generate_deterministic_embedding("Senior Management Accountant ACCA Excel")
    assert np.allclose(emb1, emb2)

    # 3. Semantic separation
    cand_text = "Senior Management Accountant ACCA CIMA Financial Reporting Excel Variance Analysis"
    match_job_text = "Management Accountant Balfour Beatty London ACCA CIMA Excel Variance Analysis Budgeting"
    unrelated_job_text = "Sous Chef Italian Restaurant London Cooking Food Hygiene HACCP Kitchen Catering"

    cand_emb = generate_deterministic_embedding(cand_text)
    match_emb = generate_deterministic_embedding(match_job_text)
    unrelated_emb = generate_deterministic_embedding(unrelated_job_text)

    sim_match = cosine_similarity(cand_emb, match_emb)
    sim_unrelated = cosine_similarity(cand_emb, unrelated_emb)

    assert sim_match >= STAGE_1_COSINE_THRESHOLD, f"Matching job failed prefilter: {sim_match} < {STAGE_1_COSINE_THRESHOLD}"
    assert sim_unrelated < STAGE_1_COSINE_THRESHOLD, f"Unrelated job passed prefilter: {sim_unrelated} >= {STAGE_1_COSINE_THRESHOLD}"


def test_stage_1_prefilter_strict_gating(monkeypatch):
    init_db()
    agent = MatchingAgent()

    candidate = {
        "id": "cand_test_01",
        "title": "Senior Management Accountant",
        "skills": ["ACCA", "Financial Reporting", "Excel"],
        "years_experience": 5,
        "location": "London"
    }

    matching_job = {
        "job_id": "job_match_101",
        "title": "Management Accountant",
        "company": "Balfour Beatty",
        "location": "London",
        "requirements": ["ACCA", "Excel", "Financial Reporting"],
        "years_experience": 3
    }

    unrelated_job = {
        "job_id": "job_unrelated_202",
        "title": "Forklift Driver",
        "company": "Logistics Co",
        "location": "London",
        "requirements": ["Forklift License", "Heavy Lifting"],
        "years_experience": 1
    }

    test_msg = {
        "correlation_id": "test_workflow_uuid",
        "payload": {
            "candidate": candidate,
            "parsed_jobs": [matching_job, unrelated_job]
        }
    }

    dispatched_response = {}

    def mock_send_response(target, payload, orig_msg, msg_type="task_response"):
        dispatched_response["target"] = target
        dispatched_response["payload"] = payload

    monkeypatch.setattr(agent, "send_response", mock_send_response)

    agent.process_message(test_msg)

    payload = dispatched_response.get("payload", {})
    ranked = payload.get("ranked_matches", [])
    disqualified = payload.get("disqualified_matches", [])

    # Verify strict pre-filter gating
    assert len(ranked) == 1
    assert ranked[0]["job_id"] == "job_match_101"
    assert ranked[0]["passed_prefilter"] is True
    assert ranked[0]["similarity_score"] >= STAGE_1_COSINE_THRESHOLD

    assert len(disqualified) == 1
    assert disqualified[0]["job_id"] == "job_unrelated_202"
    assert disqualified[0]["passed_prefilter"] is False
    assert disqualified[0]["disqualified"] is True
    assert disqualified[0]["final_score"] == 0.0

    # Verify DB persistence of both records
    with SessionLocal() as db:
        mr_pass = db.query(MatchResult).filter(MatchResult.job_id == "job_match_101").first()
        mr_fail = db.query(MatchResult).filter(MatchResult.job_id == "job_unrelated_202").first()
        assert mr_pass is not None
        assert mr_pass.passed_prefilter is True
        assert mr_fail is not None
        assert mr_fail.passed_prefilter is False
        assert mr_fail.final_score == 0.0
