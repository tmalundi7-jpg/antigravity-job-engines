import time
import uuid
import pytest
from core.db import init_db, SessionLocal, WorkflowState, JobListing, MatchResult
from core.vector_db import get_or_create_collection
from agents.company_list_agent import CompanyListAgent
from agents.job_search_agent import JobSearchAgent
from agents.job_parsing_agent import JobParsingAgent
from agents.matching_agent import MatchingAgent
from agents.master_agent import MasterAgent


def test_complete_five_stage_pipeline_e2e():
    """
    End-to-End Pipeline Integration Test.
    Executes the complete 5-stage pipeline locally:
      Stage 1: Company Discovery (FTSE constituent seed list)
      Stage 2: Job Discovery (Multi-page crawl with pagination link detection)
      Stage 3: Job Parsing (Extraction into JobListing schema & SQLite persistence)
      Stage 4: Candidate Matching (3072-dim embeddings, ChromaDB, 2-stage scoring, SQLite persistence)
      Stage 5: Aggregation & Executive Report (WorkflowState COMPLETED)
    """
    # 1. Initialize relational database schema
    init_db()

    # 2. Launch all 5 agents into in-process message bus via daemon threads
    company_agent = CompanyListAgent()
    company_agent.run(block=False)

    search_agent = JobSearchAgent()
    search_agent.run(block=False)

    parse_agent = JobParsingAgent()
    parse_agent.run(block=False)

    match_agent = MatchingAgent()
    match_agent.run(block=False)

    master = MasterAgent()
    master.run(block=False)

    time.sleep(0.5)

    # 3. Define candidate profile and custom test companies for rapid, deterministic execution
    test_cand_id = f"cand_e2e_{uuid.uuid4().hex[:6]}"
    candidate_profile = {
        "id": test_cand_id,
        "name": "Alex Morgan",
        "title": "Management Accountant",
        "skills": ["ACCA", "Financial Reporting", "Variance Analysis", "Excel", "Budgeting", "SAP"],
        "years_experience": 5,
        "certifications": ["ACCA Qualified"],
        "location": "London",
        "bio": "Qualified Management Accountant with 5 years experience in FTSE corporate reporting."
    }

    test_companies = [
        {"id": "FTSE_E2E_01", "name": "Balfour Beatty plc", "career_url": "https://www.balfourbeatty.com/careers"},
        {"id": "FTSE_E2E_02", "name": "Greggs plc", "career_url": "https://www.greggsfamily.co.uk/careers"}
    ]

    # 4. Initiate workflow
    workflow_id = master.start_workflow(
        goal="Find a Management Accountant in London",
        candidate_profile=candidate_profile,
        custom_companies=test_companies
    )
    assert workflow_id is not None

    # 5. Await pipeline completion
    start_time = time.time()
    timeout = 30.0
    completed = False
    report = None

    while time.time() - start_time < timeout:
        state = master.active_workflows.get(workflow_id)
        if state and state.get("completed"):
            completed = True
            report = state
            break
        time.sleep(0.5)

    assert completed, f"Pipeline timed out after {timeout}s! State: {master.active_workflows.get(workflow_id)}"
    assert report is not None
    assert report["status"] == "COMPLETED"

    # 6. Verify Acceptance Criteria on Match Report
    assert len(report["companies"]) == 2
    assert len(report["raw_jobs_collected"]) >= 2
    ranked_matches = report.get("ranked_matches", [])
    assert len(ranked_matches) > 0, "Expected ranked matches to be populated"

    # Check descending sort order of final scores
    scores = [m["final_score"] for m in ranked_matches]
    assert scores == sorted(scores, reverse=True), "Ranked matches must be sorted descending by final_score"

    # Check top match quality
    top_match = ranked_matches[0]
    assert top_match["final_score"] >= 60.0
    assert "score_breakdown" in top_match
    assert "reasoning" in top_match

    # 7. Verify ChromaDB 3072-Dimensional Vector Persistence
    collection = get_or_create_collection("ftse_job_listings")
    assert collection.count() > 0, "ChromaDB collection should contain indexed jobs"
    chroma_data = collection.get(include=["embeddings", "metadatas", "documents"])
    assert len(chroma_data["embeddings"]) > 0
    first_embedding = chroma_data["embeddings"][0]
    assert len(first_embedding) == 3072, f"Expected 3072-dim vector for gemini-embedding-2, got {len(first_embedding)}"

    # 8. Verify SQLite Database Persistence
    with SessionLocal() as db:
        # A. WorkflowState checkpoint
        wf_record = db.query(WorkflowState).filter(WorkflowState.id == workflow_id).first()
        assert wf_record is not None, "WorkflowState must be recorded in SQLite"
        assert wf_record.status == "COMPLETED"
        assert wf_record.data is not None

        # B. JobListing records
        jobs = db.query(JobListing).all()
        assert len(jobs) > 0, "JobListing rows must be persisted in SQLite"
        # Verify that parsed jobs from pipeline have full metadata and raw_html
        parsed_jobs_with_html = [j for j in jobs if j.raw_html is not None]
        assert len(parsed_jobs_with_html) > 0, "Expected at least one job with raw_html persisted from pipeline"
        sample_job = parsed_jobs_with_html[0]
        assert sample_job.title is not None
        assert sample_job.company is not None
        assert sample_job.requirements is not None
        assert len(sample_job.raw_html) > 0

        # C. MatchResult records
        matches = db.query(MatchResult).filter(MatchResult.workflow_id == workflow_id).all()
        assert len(matches) > 0, "MatchResult rows must be persisted in SQLite"
        for mr in matches:
            assert mr.job_id is not None
            assert mr.similarity_score is not None
            assert mr.structured_score is not None
            assert mr.final_score is not None
            assert mr.reasoning is not None
