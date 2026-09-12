import os
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pytest
from core.db import (
    init_db,
    get_engine,
    SessionLocal,
    WorkflowState,
    JobListing,
    MatchResult,
    checkpoint_workflow
)
from core.vector_db import get_or_create_collection
from core.llm import generate_deterministic_embedding


def test_sqlite_table_creation_and_schema_verification():
    """
    Empirically verify SQLite database initialization, table creation,
    and schema column presence (including migrations).
    """
    init_db()
    engine = get_engine()

    from sqlalchemy import inspect
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    assert "workflows" in table_names, "workflows table missing in SQLite"
    assert "job_listings" in table_names, "job_listings table missing in SQLite"
    assert "match_results" in table_names, "match_results table missing in SQLite"

    # Verify column presence
    wf_cols = [c["name"] for c in inspector.get_columns("workflows")]
    assert "id" in wf_cols
    assert "status" in wf_cols
    assert "created_at" in wf_cols
    assert "updated_at" in wf_cols
    assert "data" in wf_cols

    mr_cols = [c["name"] for c in inspector.get_columns("match_results")]
    assert "id" in mr_cols
    assert "workflow_id" in mr_cols
    assert "job_id" in mr_cols
    assert "similarity_score" in mr_cols
    assert "structured_score" in mr_cols
    assert "final_score" in mr_cols
    assert "passed_prefilter" in mr_cols

    job_cols = [c["name"] for c in inspector.get_columns("job_listings")]
    assert "id" in job_cols
    assert "company" in job_cols
    assert "title" in job_cols
    assert "requirements" in job_cols
    assert "raw_html" in job_cols


def test_sqlite_crud_operations():
    """
    Test Create, Read, Update, Delete across all tables.
    """
    init_db()

    # 1. JobListing CRUD
    test_job_id = f"job_crud_{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        job = JobListing(
            id=test_job_id,
            company="FTSE Test Co",
            title="Senior Auditor",
            location="London",
            description="Auditing financial reports",
            requirements=["ACA", "Audit", "Financial Controls"],
            salary_range="£70,000"
        )
        db.add(job)
        db.commit()

    with SessionLocal() as db:
        fetched = db.query(JobListing).filter(JobListing.id == test_job_id).first()
        assert fetched is not None
        assert fetched.company == "FTSE Test Co"
        assert fetched.requirements == ["ACA", "Audit", "Financial Controls"]

        # Update
        fetched.salary_range = "£75,000"
        db.commit()

    with SessionLocal() as db:
        updated = db.query(JobListing).filter(JobListing.id == test_job_id).first()
        assert updated.salary_range == "£75,000"

        # Delete
        db.delete(updated)
        db.commit()

    with SessionLocal() as db:
        deleted = db.query(JobListing).filter(JobListing.id == test_job_id).first()
        assert deleted is None

    # 2. WorkflowState CRUD & checkpointing
    test_wf_id = f"wf_crud_{uuid.uuid4().hex[:8]}"
    success = checkpoint_workflow(test_wf_id, "STAGE_1_COMPANY_LIST", {"step": 1})
    assert success is True

    with SessionLocal() as db:
        wf = db.query(WorkflowState).filter(WorkflowState.id == test_wf_id).first()
        assert wf is not None
        assert wf.status == "STAGE_1_COMPANY_LIST"
        assert wf.data.get("step") == 1

    # Checkpoint update (preserves and merges data)
    success2 = checkpoint_workflow(test_wf_id, "STAGE_2_JOB_DISCOVERY", {"step": 2, "count": 10})
    assert success2 is True

    with SessionLocal() as db:
        wf = db.query(WorkflowState).filter(WorkflowState.id == test_wf_id).first()
        assert wf.status == "STAGE_2_JOB_DISCOVERY"
        assert wf.data.get("step") == 2
        assert wf.data.get("count") == 10

    # 3. MatchResult CRUD with boolean flag
    test_mr_id = f"mr_crud_{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        mr = MatchResult(
            id=test_mr_id,
            workflow_id=test_wf_id,
            job_id=test_job_id,
            candidate_id="cand_1",
            similarity_score=0.725,
            structured_score=85.0,
            final_score=80.0,
            passed_prefilter=True,
            reasoning="Passed Stage 1"
        )
        db.add(mr)
        db.commit()

    with SessionLocal() as db:
        fetched_mr = db.query(MatchResult).filter(MatchResult.id == test_mr_id).first()
        assert fetched_mr is not None
        assert fetched_mr.passed_prefilter is True
        assert abs(fetched_mr.similarity_score - 0.725) < 1e-4
        assert fetched_mr.final_score == 80.0


def test_sqlite_concurrent_multithreaded_writes():
    """
    Stress test: 20 concurrent worker threads inserting records into SQLite
    to verify thread-safety and lack of unhandled lock failures.
    """
    init_db()
    num_threads = 20
    inserts_per_thread = 10
    inserted_ids = []
    lock = threading.Lock()

    def worker(thread_idx):
        for i in range(inserts_per_thread):
            rec_id = f"conc_{thread_idx}_{i}_{uuid.uuid4().hex[:6]}"
            with SessionLocal() as db:
                job = JobListing(
                    id=rec_id,
                    company=f"Company_{thread_idx}",
                    title=f"Role_{i}",
                    location="London",
                    description="Concurrent stress test",
                    requirements=["Python", "SQL"]
                )
                db.add(job)
                db.commit()
            with lock:
                inserted_ids.append(rec_id)

    with ThreadPoolExecutor(max_workers=num_threads) as pool:
        futures = [pool.submit(worker, t) for t in range(num_threads)]
        for f in futures:
            f.result()

    assert len(inserted_ids) == num_threads * inserts_per_thread

    # Verify all exist in database
    with SessionLocal() as db:
        count = db.query(JobListing).filter(JobListing.id.in_(inserted_ids)).count()
        assert count == len(inserted_ids), f"Expected {len(inserted_ids)} records in DB, found {count}"


def test_chromadb_disk_persistence():
    """
    Empirically verify ChromaDB local disk persistence:
    1. Embeddings are persisted to ./chroma_data on the filesystem.
    2. Dimension is strictly 3072.
    3. Vectors survive independent client recreation from the raw directory.
    """
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chroma_dir = os.path.join(workspace_dir, "chroma_data")
    assert os.path.exists(chroma_dir), f"Chroma directory {chroma_dir} does not exist"

    # 1. Insert a distinctive test vector via the standard helper
    col = get_or_create_collection("ftse_job_listings")
    test_id = f"disk_test_{uuid.uuid4().hex[:8]}"
    emb_3072 = generate_deterministic_embedding("ChromaDB Persistence Test Management Accountant")
    assert len(emb_3072) == 3072, f"Expected 3072 dimensions, got {len(emb_3072)}"

    col.upsert(
        ids=[test_id],
        embeddings=[emb_3072],
        metadatas=[{"company": "Persistence Test Co", "type": "disk_audit"}],
        documents=["Distinctive persistence document test"]
    )

    # 2. Instantiate a completely new PersistentClient directly from chromadb
    import chromadb
    from chromadb.config import Settings
    fresh_client = chromadb.PersistentClient(path=chroma_dir, settings=Settings(anonymized_telemetry=False))
    fresh_col = fresh_client.get_collection("ftse_job_listings")

    # 3. Retrieve the record using the new client
    res = fresh_col.get(ids=[test_id], include=["embeddings", "metadatas", "documents"])
    assert len(res["ids"]) == 1, f"Failed to retrieve record {test_id} from fresh client"
    assert res["ids"][0] == test_id
    assert res["metadatas"][0]["company"] == "Persistence Test Co"
    assert res["documents"][0] == "Distinctive persistence document test"

    retrieved_emb = res["embeddings"][0]
    assert len(retrieved_emb) == 3072, f"Expected 3072 dims from disk, got {len(retrieved_emb)}"
    # Verify values match
    assert np.allclose(emb_3072[:20], retrieved_emb[:20], atol=1e-5), "Retrieved vector values do not match original"

    # Verify SQLite file exists in chroma_data
    chroma_sqlite = os.path.join(chroma_dir, "chroma.sqlite3")
    assert os.path.exists(chroma_sqlite), f"chroma.sqlite3 missing in {chroma_dir}"
    assert os.path.getsize(chroma_sqlite) > 0, "chroma.sqlite3 is empty"
