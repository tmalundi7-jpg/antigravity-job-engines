"""
Forensic Integrity Verification Probe for Milestone 1
Independently verifies:
1. Cheating / Dummy / Facade detection
2. Stage 1 Cosine Pre-filtering dynamic vector math & strict gating
3. Stage 2 Structured Multi-attribute scoring dynamic calculation
4. LocalMessageBroker, SQLite db, ChromaDB disk persistence
5. Gemini model targeting & deterministic unit math fallback
"""

import os
import sys
import uuid
import sqlite3
import numpy as np

# Ensure root in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import core.llm as llm
import core.db as db
import core.vector_db as vector_db
import core.messaging as messaging
from agents.matching_agent import MatchingAgent, cosine_similarity, STAGE_1_COSINE_THRESHOLD

results = {}

def run_check_1_cheating_facade():
    print("\n--- CHECK 1: Facade & Hardcoding Inspection ---")
    # Verify functions do not return constants or cheat
    # Test cosine_similarity on random non-trivial vectors
    r1 = np.random.randn(50)
    r2 = np.random.randn(50)
    sim = cosine_similarity(r1, r2)
    expected = float(np.dot(r1, r2) / (np.linalg.norm(r1) * np.linalg.norm(r2)))
    assert np.isclose(sim, expected), f"cosine_similarity mismatch: {sim} vs {expected}"

    # Verify generate_deterministic_embedding produces different vectors for different inputs
    v1 = llm.generate_deterministic_embedding("Civil Engineer London")
    v2 = llm.generate_deterministic_embedding("Pastry Chef Bakery Manchester")
    assert v1 != v2, "generate_deterministic_embedding returned identical vectors for different inputs!"
    assert len(v1) == 3072, f"Expected 3072 dimensions, got {len(v1)}"

    results["CHECK_1_FACADE_DETECTION"] = "PASS"
    print("CHECK 1: PASS - Genuine dynamic functions without facade or static returns.")

def run_check_2_stage_1_prefilter():
    print("\n--- CHECK 2: Stage 1 Cosine Similarity Pre-filtering & Gating ---")
    agent = MatchingAgent()

    # Generate synthetic candidate embedding
    cand_dim = 3072
    base = np.random.RandomState(999).randn(cand_dim)
    cand_vec = (base / np.linalg.norm(base)).tolist()

    # Create 2 orthogonal vectors to candidate
    rand_ortho = np.random.RandomState(888).randn(cand_dim)
    rand_ortho = rand_ortho - np.dot(rand_ortho, cand_vec) * np.array(cand_vec)
    ortho_unit = rand_ortho / np.linalg.norm(rand_ortho)

    # Job A: cosine similarity = 0.60 (< 0.65) -> MUST BE DISQUALIFIED
    target_cos_a = 0.60
    vec_a = target_cos_a * np.array(cand_vec) + np.sqrt(1 - target_cos_a**2) * ortho_unit
    vec_a = (vec_a / np.linalg.norm(vec_a)).tolist()
    calc_sim_a = cosine_similarity(cand_vec, vec_a)
    assert np.isclose(calc_sim_a, 0.60, atol=1e-3), f"Sim A was {calc_sim_a}"

    # Job B: cosine similarity = 0.75 (>= 0.65) -> MUST PASS
    target_cos_b = 0.75
    vec_b = target_cos_b * np.array(cand_vec) + np.sqrt(1 - target_cos_b**2) * ortho_unit
    vec_b = (vec_b / np.linalg.norm(vec_b)).tolist()
    calc_sim_b = cosine_similarity(cand_vec, vec_b)
    assert np.isclose(calc_sim_b, 0.75, atol=1e-3), f"Sim B was {calc_sim_b}"

    # Monkeypatch get_embedding to return these exact vectors
    cand_profile = {
        "id": "cand_forensic_01",
        "title": "Forensic Candidate",
        "skills": ["python", "sql"],
        "years_experience": 5,
        "location": "London"
    }

    job_fail = {
        "job_id": "job_forensic_fail_01",
        "title": "Low Similarity Job",
        "company": "Company A",
        "location": "London",
        "requirements": ["python", "sql"],
        "years_experience": 3
    }

    job_pass = {
        "job_id": "job_forensic_pass_02",
        "title": "High Similarity Job",
        "company": "Company B",
        "location": "London",
        "requirements": ["python", "sql"],
        "years_experience": 3
    }

    emb_map = {
        "cand": cand_vec,
        job_fail["job_id"]: vec_a,
        job_pass["job_id"]: vec_b
    }

    def fake_get_embedding(text, model=None):
        if "Forensic Candidate" in text:
            return emb_map["cand"]
        elif "Low Similarity Job" in text:
            return emb_map[job_fail["job_id"]]
        elif "High Similarity Job" in text:
            return emb_map[job_pass["job_id"]]
        return llm.generate_deterministic_embedding(text)

    # Temporary patch
    orig_get_emb = llm.get_embedding
    orig_gen_det = llm.generate_deterministic_embedding
    llm.get_embedding = fake_get_embedding
    llm.generate_deterministic_embedding = fake_get_embedding

    dispatched = {}
    def mock_send(target, payload, orig_msg, msg_type="task_response"):
        dispatched["payload"] = payload

    agent.send_response = mock_send

    test_msg = {
        "correlation_id": "wf_forensic_gate_test",
        "payload": {
            "candidate": cand_profile,
            "parsed_jobs": [job_fail, job_pass]
        }
    }

    try:
        agent.process_message(test_msg)
    finally:
        llm.get_embedding = orig_get_emb
        llm.generate_deterministic_embedding = orig_gen_det

    payload = dispatched.get("payload", {})
    ranked = payload.get("ranked_matches", [])
    disqualified = payload.get("disqualified_matches", [])

    assert len(ranked) == 1, f"Expected 1 ranked match, got {len(ranked)}"
    assert ranked[0]["job_id"] == "job_forensic_pass_02"
    assert ranked[0]["passed_prefilter"] is True
    assert ranked[0]["final_score"] > 0.0

    assert len(disqualified) == 1, f"Expected 1 disqualified match, got {len(disqualified)}"
    assert disqualified[0]["job_id"] == "job_forensic_fail_01"
    assert disqualified[0]["passed_prefilter"] is False
    assert disqualified[0]["final_score"] == 0.0
    assert "Disqualified" in disqualified[0]["reasoning"]

    # Check database persistence of both
    with db.SessionLocal() as session:
        mr_pass = session.query(db.MatchResult).filter(db.MatchResult.job_id == "job_forensic_pass_02").first()
        mr_fail = session.query(db.MatchResult).filter(db.MatchResult.job_id == "job_forensic_fail_01").first()
        assert mr_pass is not None and mr_pass.passed_prefilter is True
        assert mr_fail is not None and mr_fail.passed_prefilter is False and mr_fail.final_score == 0.0

    results["CHECK_2_STAGE_1_PREFILTER"] = "PASS"
    print(f"CHECK 2: PASS - Cosine math verified. Strict gating confirmed: {calc_sim_a:.3f} disqualified, {calc_sim_b:.3f} passed.")

def run_check_3_stage_2_scoring():
    print("\n--- CHECK 3: Stage 2 Structured Scoring Dynamic Evaluation ---")
    agent = MatchingAgent()

    # Test 1: Full match across all dimensions
    job1 = {
        "requirements": ["ACCA", "Excel", "Variance Analysis", "Financial Reporting"],
        "years_experience": 3,
        "location": "London"
    }
    cand1 = {
        "skills": ["ACCA", "Excel", "Variance Analysis", "Financial Reporting"],
        "years_experience": 5,
        "certifications": ["ACCA Qualified"],
        "location": "London"
    }
    score1, bd1 = agent.score_structured_attributes(job1, cand1)
    print("Test 1 (Full match):", score1, bd1)
    assert bd1["skills"] == 40.0, f"Expected skills 40.0, got {bd1['skills']}"
    assert bd1["experience"] == 30.0, f"Expected exp 30.0, got {bd1['experience']}"
    assert bd1["education"] == 15.0, f"Expected edu 15.0, got {bd1['education']}"
    assert bd1["location"] == 10.0, f"Expected loc 10.0, got {bd1['location']}"
    assert bd1["keywords"] == 5.0
    assert score1 == 100.0, f"Expected 100.0, got {score1}"

    # Test 2: Low/Zero match
    job2 = {
        "requirements": ["Java", "Kubernetes", "Rust", "C++"],
        "years_experience": 10,
        "location": "Edinburgh"
    }
    cand2 = {
        "skills": ["Python"],
        "years_experience": 2,
        "certifications": ["AWS"],
        "location": "London"
    }
    score2, bd2 = agent.score_structured_attributes(job2, cand2)
    print("Test 2 (Low match):", score2, bd2)
    assert bd2["skills"] == 0.0, f"Expected skills 0.0, got {bd2['skills']}"
    assert np.isclose(bd2["experience"], (2/10)*30.0, atol=0.1), f"Expected exp 6.0, got {bd2['experience']}"
    assert bd2["education"] == 7.5, f"Expected cert 7.5, got {bd2['education']}"
    assert bd2["location"] == 3.0, f"Expected loc 3.0, got {bd2['location']}"
    assert bd2["keywords"] == 5.0
    assert score2 == round(0.0 + 6.0 + 7.5 + 3.0 + 5.0, 1)

    # Test 3: Partial skill match
    job3 = {
        "requirements": ["Python", "SQL", "Docker", "AWS"],
        "years_experience": 4,
        "location": "Manchester"
    }
    cand3 = {
        "skills": ["Python", "SQL"],
        "years_experience": 4,
        "certifications": ["None"],
        "location": "Manchester"
    }
    score3, bd3 = agent.score_structured_attributes(job3, cand3)
    print("Test 3 (Partial match):", score3, bd3)
    # matched 2/4 = 0.5 ratio -> min(1.0, 0.5 * 1.2) * 40 = 0.6 * 40 = 24.0
    assert np.isclose(bd3["skills"], 24.0, atol=0.1), f"Expected skills 24.0, got {bd3['skills']}"
    assert bd3["experience"] == 30.0
    assert bd3["location"] == 10.0

    results["CHECK_3_STAGE_2_SCORING"] = "PASS"
    print("CHECK 3: PASS - Structured scoring dynamically computes skills (40%), experience (30%), education (15%), location (10%), keywords (5%).")

def run_check_4_persistence():
    print("\n--- CHECK 4: Disk Persistence (SQLite & ChromaDB & Broker) ---")
    # A. SQLite Direct Disk Inspection
    db_path = os.path.join(root_dir, "job_engine.db")
    assert os.path.exists(db_path), f"SQLite database file missing at {db_path}"
    file_size = os.path.getsize(db_path)
    assert file_size > 0, f"SQLite db file is empty: {file_size} bytes"
    print(f"SQLite DB file verified on disk: {db_path} ({file_size} bytes)")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Verify tables exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    assert "workflows" in tables, "Table 'workflows' missing in SQLite"
    assert "job_listings" in tables, "Table 'job_listings' missing in SQLite"
    assert "match_results" in tables, "Table 'match_results' missing in SQLite"

    # Verify schemas
    cur.execute("PRAGMA table_info(workflows);")
    wf_cols = {r[1]: r[2] for r in cur.fetchall()}
    assert "updated_at" in wf_cols, "Column 'updated_at' missing in workflows table"

    cur.execute("PRAGMA table_info(match_results);")
    mr_cols = {r[1]: r[2] for r in cur.fetchall()}
    assert "passed_prefilter" in mr_cols, "Column 'passed_prefilter' missing in match_results table"

    cur.execute("SELECT count(*) FROM workflows;")
    wf_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM job_listings;")
    jl_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM match_results;")
    mr_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM match_results WHERE passed_prefilter=0;")
    disq_count = cur.fetchone()[0]
    conn.close()

    print(f"SQLite table row counts: workflows={wf_count}, job_listings={jl_count}, match_results={mr_count}, disqualified={disq_count}")
    assert wf_count > 0, "No workflows stored in SQLite"
    assert jl_count > 0, "No job listings stored in SQLite"
    assert mr_count > 0, "No match results stored in SQLite"

    # B. ChromaDB Direct Disk Inspection
    chroma_dir = os.path.join(root_dir, "chroma_data")
    assert os.path.isdir(chroma_dir), f"ChromaDB directory missing at {chroma_dir}"
    chroma_sqlite = os.path.join(chroma_dir, "chroma.sqlite3")
    assert os.path.exists(chroma_sqlite), f"chroma.sqlite3 missing at {chroma_sqlite}"
    chroma_size = os.path.getsize(chroma_sqlite)
    assert chroma_size > 0, f"chroma.sqlite3 empty: {chroma_size} bytes"
    print(f"ChromaDB persistent file verified: {chroma_sqlite} ({chroma_size} bytes)")

    # Query ChromaDB collection directly
    col = vector_db.get_or_create_collection("ftse_job_listings")
    col_count = col.count()
    print(f"ChromaDB collection 'ftse_job_listings' entry count: {col_count}")
    assert col_count > 0, "ChromaDB collection is empty!"

    sample = col.get(limit=1, include=["embeddings", "metadatas", "documents"])
    assert len(sample["embeddings"]) == 1, "Failed to retrieve sample embedding"
    emb_dim = len(sample["embeddings"][0])
    assert emb_dim == 3072, f"Expected 3072 vector dimensions, got {emb_dim}"
    print(f"ChromaDB sample vector dimension verified: {emb_dim}")

    # C. LocalMessageBroker verification
    broker = messaging.LocalMessageBroker()
    q_name = f"test_forensic_queue_{uuid.uuid4().hex[:6]}"
    broker.declare_queue(q_name)
    received = []
    broker.consume(q_name, lambda m: received.append(m), block=False)
    broker.publish(q_name, {"ping": "pong"}, "forensic_src", "forensic_tgt", "ping")
    import time
    time.sleep(0.3)
    assert len(received) == 1, f"LocalMessageBroker failed: received {len(received)} messages"
    assert received[0]["payload"] == {"ping": "pong"}
    assert received[0]["type"] == "ping"

    results["CHECK_4_PERSISTENCE"] = "PASS"
    print("CHECK 4: PASS - SQLite, ChromaDB, and LocalMessageBroker operate and persist genuinely.")

def run_check_5_gemini_targeting_and_fallback():
    print("\n--- CHECK 5: Gemini Models & Deterministic Math Fallback ---")
    assert llm.DEFAULT_GENERATION_MODEL == "gemini-3.6-flash", f"Wrong generation model: {llm.DEFAULT_GENERATION_MODEL}"
    assert llm.DEFAULT_EMBEDDING_MODEL == "gemini-embedding-2", f"Wrong embedding model: {llm.DEFAULT_EMBEDDING_MODEL}"
    assert llm.EMBEDDING_DIM == 3072, f"Wrong embedding dim: {llm.EMBEDDING_DIM}"
    print("Gemini model constants verified: gemini-3.6-flash, gemini-embedding-2 (3072 dim).")

    # Mathematical properties of generate_deterministic_embedding:
    # 1. Determinism across 50 iterations
    text_sample = "Senior Financial Reporting Manager ACCA IFRS London FTSE 100"
    baseline = llm.generate_deterministic_embedding(text_sample)
    for _ in range(50):
        retest = llm.generate_deterministic_embedding(text_sample)
        assert baseline == retest, "Non-deterministic embedding detected!"

    # 2. Length & Unit Norm
    assert len(baseline) == 3072
    norm = np.linalg.norm(baseline)
    assert np.isclose(norm, 1.0, atol=1e-5), f"Vector is not unit norm: {norm}"

    # 3. Orthogonality / Cosine separation
    # Related profile
    related_text = "Group Financial Reporting Manager ACCA IFRS London"
    related_emb = llm.generate_deterministic_embedding(related_text)
    sim_rel = cosine_similarity(baseline, related_emb)
    print(f"Cosine similarity (related): {sim_rel:.4f}")
    assert sim_rel >= STAGE_1_COSINE_THRESHOLD, f"Related texts failed threshold: {sim_rel} < 0.65"

    # Unrelated profile
    unrelated_text = "Sous Chef French Restaurant Kitchen Cooking HACCP Grill"
    unrelated_emb = llm.generate_deterministic_embedding(unrelated_text)
    sim_unrel = cosine_similarity(baseline, unrelated_emb)
    print(f"Cosine similarity (unrelated): {sim_unrel:.4f}")
    assert sim_unrel < STAGE_1_COSINE_THRESHOLD, f"Unrelated texts passed threshold: {sim_unrel} >= 0.65"

    results["CHECK_5_GEMINI_AND_FALLBACK"] = "PASS"
    print("CHECK 5: PASS - Gemini models targeted and fallback deterministic math verified.")

if __name__ == "__main__":
    try:
        run_check_1_cheating_facade()
        run_check_2_stage_1_prefilter()
        run_check_3_stage_2_scoring()
        run_check_4_persistence()
        run_check_5_gemini_targeting_and_fallback()

        print("\n=======================================================")
        print("ALL FORENSIC CHECKS PASSED: VERDICT = CLEAN")
        print("=======================================================")
    except Exception as e:
        print(f"\nFORENSIC INTEGRITY VIOLATION DETECTED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
