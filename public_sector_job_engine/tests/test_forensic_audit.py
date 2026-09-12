"""
Forensic audit tests: boundary cosine similarity assertions for Stage 1 gate.

Edge-case coverage:
  - cosine(v_a, v_b) = 0.6499  →  Stage 1 REJECTS  (final_score == 0.0)
  - cosine(v_a, v_b) = 0.6500  →  Stage 1 PASSES   (final_score > 0.0)
"""
import math
import numpy as np
import pytest


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_pair_with_cosine(target_cos: float, dim: int = 3072):
    """
    Returns (v_a, v_b) where cosine_similarity(v_a, v_b) == target_cos.
    Uses a 2-D construction: v_a = e_1, v_b = cos*e_1 + sin*e_2, then
    pads to `dim` dimensions.
    """
    assert -1.0 <= target_cos <= 1.0
    theta = math.acos(target_cos)
    v_a = [0.0] * dim
    v_b = [0.0] * dim
    v_a[0] = 1.0
    v_b[0] = math.cos(theta)
    v_b[1] = math.sin(theta)
    return v_a, v_b


def _cosine(v1, v2):
    a, b = np.array(v1), np.array(v2)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def matching_agent(tmp_path):
    """
    Build a MatchingAgent with a deterministic (no-network) embed_fn and
    an in-memory ChromaDB collection so the tests never call Gemini API.
    """
    import chromadb
    from agents.matching_agent import MatchingAgent

    chroma = chromadb.Client()
    collection = chroma.get_or_create_collection("test_forensic")

    def _passthrough_embed(text):
        # Returns a deterministic vector so tests control cosine values explicitly
        from core.llm import generate_deterministic_embedding
        return generate_deterministic_embedding(text)

    return MatchingAgent(embed_fn=_passthrough_embed, collection=collection)


# ── Stage 1 gate boundary tests ────────────────────────────────────────────────

class TestStage1BoundaryGate:
    """Verify the exact 0.65 threshold is treated as a closed lower bound."""

    def test_cosine_0_6499_is_rejected(self, matching_agent):
        """A job with cosine similarity 0.6499 must be disqualified (final_score == 0.0)."""
        v_a, v_b = _make_pair_with_cosine(0.6499)
        # Verify our construction is accurate
        assert abs(_cosine(v_a, v_b) - 0.6499) < 1e-4

        from agents.matching_agent import cosine_similarity, STAGE_1_COSINE_THRESHOLD
        sim = cosine_similarity(v_a, v_b)
        assert sim < STAGE_1_COSINE_THRESHOLD, (
            f"Expected sim={sim:.6f} < threshold={STAGE_1_COSINE_THRESHOLD}"
        )

    def test_cosine_0_6500_passes(self, matching_agent):
        """A job with cosine similarity exactly 0.6500 must pass Stage 1."""
        v_a, v_b = _make_pair_with_cosine(0.6500)
        assert abs(_cosine(v_a, v_b) - 0.6500) < 1e-4

        from agents.matching_agent import cosine_similarity, STAGE_1_COSINE_THRESHOLD
        sim = cosine_similarity(v_a, v_b)
        assert sim >= STAGE_1_COSINE_THRESHOLD, (
            f"Expected sim={sim:.6f} >= threshold={STAGE_1_COSINE_THRESHOLD}"
        )

    def test_threshold_constant_value(self):
        """Guard: threshold must remain exactly 0.65."""
        from agents.matching_agent import STAGE_1_COSINE_THRESHOLD
        assert STAGE_1_COSINE_THRESHOLD == 0.65


# ── Integration-level boundary test ────────────────────────────────────────────

class TestStage1EndToEndBoundary:
    """
    Drive MatchingAgent.process_message() with a carefully crafted message
    whose embedding similarity sits right at the gate boundary.

    Uses a mock embed_fn that returns pre-built vectors with known cosine.
    """

    def _run_match(self, sim_value: float):
        """Build a MatchingAgent that returns controlled vectors and run one job."""
        import chromadb
        from agents.matching_agent import MatchingAgent

        chroma = chromadb.Client()
        coll = chroma.get_or_create_collection(f"boundary_{int(sim_value*10000)}")

        v_a, v_b = _make_pair_with_cosine(sim_value)
        call_count = {"n": 0}

        def _fixed_embed(text):
            call_count["n"] += 1
            # First call → candidate, subsequent calls → job
            return v_a if call_count["n"] == 1 else v_b

        agent = MatchingAgent(embed_fn=_fixed_embed, collection=coll)

        result = {"ranked": [], "disqualified": []}

        # Monkey-patch send_response to capture output
        def _capture(target, payload, orig_msg, msg_type="task_response"):
            result["ranked"] = payload.get("ranked_matches", [])
            result["disqualified"] = payload.get("disqualified_matches", [])

        agent.send_response = _capture

        candidate = {
            "id": "cand_test",
            "name": "Test",
            "title": "Management Accountant",
            "skills": ["ACCA"],
            "years_experience": 5,
            "certifications": ["ACCA"],
            "location": "London",
        }
        job = {
            "job_id": "job_test_1",
            "title": "Management Accountant",
            "company": "Test Corp",
            "location": "London",
            "description": "Finance role",
            "requirements": ["ACCA"],
            "salary_range": "£60,000",
            "years_experience": 3,
        }

        msg = {
            "message_id": "msg_test",
            "correlation_id": "wf_test",
            "source_agent": "master",
            "target_agent": "matching_agent",
            "type": "task_request",
            "payload": {"candidate": candidate, "parsed_jobs": [job]},
        }
        agent.process_message(msg)
        return result

    def test_below_threshold_gives_zero_score(self):
        result = self._run_match(0.6499)
        assert len(result["disqualified"]) == 1
        assert result["disqualified"][0]["final_score"] == 0.0
        assert len(result["ranked"]) == 0

    def test_at_threshold_gives_positive_score(self):
        result = self._run_match(0.6500)
        assert len(result["ranked"]) == 1
        assert result["ranked"][0]["final_score"] > 0.0
        assert len(result["disqualified"]) == 0
