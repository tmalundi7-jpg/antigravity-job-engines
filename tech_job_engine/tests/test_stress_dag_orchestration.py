import time
import uuid
import threading
import pytest
from core.db import init_db, SessionLocal, WorkflowState, JobListing, MatchResult
from core.messaging import MessageBroker
from agents.company_list_agent import CompanyListAgent
from agents.job_search_agent import JobSearchAgent
from agents.job_parsing_agent import JobParsingAgent
from agents.matching_agent import MatchingAgent
from agents.master_agent import MasterAgent


@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    init_db()


def make_mock_job_page(company_name, job_index):
    """Helper to generate a realistic mock job page with distinctive title."""
    return {
        "source_url": f"https://www.{company_name.lower().replace(' ', '')}.com/careers/job-{job_index}",
        "html_content": f"""
        <html><body>
          <h1>{company_name} - Role {job_index}</h1>
          <div class="job-details">
            <h2>Management Accountant - Senior Specialist {job_index}</h2>
            <p>Location: London, UK</p>
            <p>Salary: £65,000</p>
            <p>Requirements: ACCA, Financial Reporting, Variance Analysis, Excel</p>
            <p>Description: Lead monthly management accounts and budgeting for corporate division.</p>
          </div>
        </body></html>
        """,
        "metadata": {
            "company_name": company_name,
            "page": job_index
        }
    }


def test_dag_boundary_multiple_jobs_per_company():
    """
    Boundary Condition 1: Multiple jobs per company (5 jobs each across 2 companies = 10 jobs).
    Rigorous verification:
    - Master Agent coordinates all 10 jobs through discovery, parsing, matching.
    - No premature completion: does not finalize while parses or matches are in-flight.
    - No deadlocks: completes within timeout.
    - Accurate accounting: report reflects exactly 10 evaluated jobs.
    """
    broker = MessageBroker()
    master = MasterAgent()
    master.run(block=False)

    time.sleep(0.3)
    wf_id = str(uuid.uuid4())

    candidate = {
        "id": f"cand_multi_{uuid.uuid4().hex[:6]}",
        "name": "Jordan Lee",
        "title": "Management Accountant",
        "skills": ["ACCA", "Financial Reporting", "Variance Analysis", "Excel"],
        "years_experience": 5,
        "certifications": ["ACCA Qualified"],
        "location": "London"
    }

    test_companies = [
        {"id": "COMP_A", "name": "Company Alpha plc", "career_url": "https://alpha.example.com/careers"},
        {"id": "COMP_B", "name": "Company Beta plc", "career_url": "https://beta.example.com/careers"}
    ]

    # Start workflow
    actual_wf_id = master.start_workflow(
        goal="Find Management Accountant jobs at Alpha and Beta",
        candidate_profile=candidate,
        custom_companies=test_companies
    )

    # We also launch parser and matching agents in background
    parser = JobParsingAgent()
    parser.run(block=False)

    matcher = MatchingAgent()
    matcher.run(block=False)

    # Simulate CompanyListAgent response with 2 companies
    broker.publish(
        queue_name="master_queue",
        payload={"companies": test_companies},
        source="company_list_agent",
        target="master",
        msg_type="task_response",
        correlation_id=actual_wf_id
    )

    time.sleep(0.2)
    state = master.active_workflows[actual_wf_id]
    assert state["status"] == "STAGE_2_JOB_DISCOVERY"
    assert state["expected_searches"] == 2

    # Now simulate JobSearchAgent returning 5 jobs for Company Alpha
    alpha_jobs = [make_mock_job_page("Company Alpha plc", i) for i in range(1, 6)]
    broker.publish(
        queue_name="master_queue",
        payload={"company_id": "COMP_A", "company_name": "Company Alpha plc", "raw_jobs": alpha_jobs, "count": 5},
        source="job_search_agent",
        target="master",
        msg_type="task_response",
        correlation_id=actual_wf_id
    )

    # Now simulate JobSearchAgent returning 5 jobs for Company Beta
    beta_jobs = [make_mock_job_page("Company Beta plc", i) for i in range(1, 6)]
    broker.publish(
        queue_name="master_queue",
        payload={"company_id": "COMP_B", "company_name": "Company Beta plc", "raw_jobs": beta_jobs, "count": 5},
        source="job_search_agent",
        target="master",
        msg_type="task_response",
        correlation_id=actual_wf_id
    )

    # Await completion
    start = time.time()
    timeout = 25.0
    while time.time() - start < timeout:
        state = master.active_workflows.get(actual_wf_id)
        if state and state.get("completed"):
            break
        time.sleep(0.3)

    state = master.active_workflows.get(actual_wf_id)
    assert state is not None
    assert state.get("completed") is True, f"Workflow did not complete within {timeout}s! State: {state}"
    assert state["status"] == "COMPLETED"

    # Verify accounting: 10 raw jobs, 10 parsed jobs, 10 evaluated matches
    assert len(state["raw_jobs_collected"]) == 10, f"Expected 10 raw jobs, got {len(state['raw_jobs_collected'])}"
    assert len(state["parsed_jobs"]) == 10, f"Expected 10 parsed jobs, got {len(state['parsed_jobs'])}"

    total_evaluated = len(state["ranked_matches"]) + len(state["disqualified_matches"])
    assert total_evaluated == 10, f"Expected 10 total evaluated matches, got {total_evaluated}"

    # Verify counters
    assert state["completed_searches"] == 2
    assert state["dispatched_parses"] == 2
    assert state["completed_parses"] == 2
    assert state["dispatched_matches"] == 2
    assert state["completed_matches"] == 2


def test_dag_boundary_zero_jobs_all_companies():
    """
    Boundary Condition 2: Companies with 0 jobs.
    Rigorous verification:
    - When search returns raw_jobs: [], ensure NO deadlock.
    - Master Agent completes cleanly without hanging.
    - Final state is COMPLETED and executive report indicates 0 jobs found.
    """
    broker = MessageBroker()
    master = MasterAgent()
    master.run(block=False)

    test_companies = [
        {"id": "EMPTY_1", "name": "Empty Co 1", "career_url": "https://empty1.example.com"},
        {"id": "EMPTY_2", "name": "Empty Co 2", "career_url": "https://empty2.example.com"}
    ]

    actual_wf_id = master.start_workflow(
        goal="Search in companies with zero vacancies",
        custom_companies=test_companies
    )

    # Simulate CompanyListAgent response
    broker.publish(
        queue_name="master_queue",
        payload={"companies": test_companies},
        source="company_list_agent",
        target="master",
        msg_type="task_response",
        correlation_id=actual_wf_id
    )

    time.sleep(0.2)

    # Simulate JobSearchAgent returning 0 jobs for both companies
    broker.publish(
        queue_name="master_queue",
        payload={"company_id": "EMPTY_1", "company_name": "Empty Co 1", "raw_jobs": [], "count": 0},
        source="job_search_agent",
        target="master",
        msg_type="task_response",
        correlation_id=actual_wf_id
    )

    broker.publish(
        queue_name="master_queue",
        payload={"company_id": "EMPTY_2", "company_name": "Empty Co 2", "raw_jobs": [], "count": 0},
        source="job_search_agent",
        target="master",
        msg_type="task_response",
        correlation_id=actual_wf_id
    )

    # Await completion
    start = time.time()
    timeout = 10.0
    while time.time() - start < timeout:
        state = master.active_workflows.get(actual_wf_id)
        if state and state.get("completed"):
            break
        time.sleep(0.2)

    state = master.active_workflows.get(actual_wf_id)
    assert state is not None
    assert state.get("completed") is True, "Workflow deadlocked on 0-job boundary!"
    assert state["status"] == "COMPLETED"
    assert len(state["raw_jobs_collected"]) == 0
    assert len(state["parsed_jobs"]) == 0
    assert len(state["ranked_matches"]) == 0
    assert state["completed_searches"] == 2
    assert state["dispatched_parses"] == 0
    assert state["completed_parses"] == 0
    assert state["dispatched_matches"] == 0
    assert state["completed_matches"] == 0

    # Verify report handles empty result gracefully
    report = state.get("executive_report", "")
    assert "No jobs passed the Stage 1 vector cosine similarity pre-filter" in report


def test_dag_boundary_mixed_jobs():
    """
    Boundary Condition 3: Mixed companies (Company 1 has 5 jobs, Company 2 has 0 jobs).
    Verify that:
    - Company 2 returning 0 jobs does NOT prematurely finalize the workflow
      while Company 1's 5 jobs are being parsed and matched.
    - All 5 jobs from Company 1 are fully matched and persisted.
    """
    broker = MessageBroker()
    master = MasterAgent()
    master.run(block=False)

    parser = JobParsingAgent()
    parser.run(block=False)

    matcher = MatchingAgent()
    matcher.run(block=False)

    test_companies = [
        {"id": "MIX_1", "name": "Mix Active Co", "career_url": "https://active.example.com"},
        {"id": "MIX_2", "name": "Mix Dormant Co", "career_url": "https://dormant.example.com"}
    ]

    actual_wf_id = master.start_workflow(
        goal="Search in mixed active and dormant companies",
        custom_companies=test_companies
    )

    # Company list response
    broker.publish(
        queue_name="master_queue",
        payload={"companies": test_companies},
        source="company_list_agent",
        target="master",
        msg_type="task_response",
        correlation_id=actual_wf_id
    )

    time.sleep(0.2)

    # First send Company 2 (Dormant with 0 jobs)
    broker.publish(
        queue_name="master_queue",
        payload={"company_id": "MIX_2", "company_name": "Mix Dormant Co", "raw_jobs": [], "count": 0},
        source="job_search_agent",
        target="master",
        msg_type="task_response",
        correlation_id=actual_wf_id
    )

    time.sleep(0.2)
    # Check that workflow did NOT prematurely finalize
    state = master.active_workflows[actual_wf_id]
    assert state.get("completed") is False, "Premature completion detected after dormant company search!"
    assert state["completed_searches"] == 1

    # Now send Company 1 (Active with 5 jobs)
    active_jobs = [make_mock_job_page("Mix Active Co", i) for i in range(1, 6)]
    broker.publish(
        queue_name="master_queue",
        payload={"company_id": "MIX_1", "company_name": "Mix Active Co", "raw_jobs": active_jobs, "count": 5},
        source="job_search_agent",
        target="master",
        msg_type="task_response",
        correlation_id=actual_wf_id
    )

    # Await completion
    start = time.time()
    timeout = 20.0
    while time.time() - start < timeout:
        state = master.active_workflows.get(actual_wf_id)
        if state and state.get("completed"):
            break
        time.sleep(0.3)

    state = master.active_workflows.get(actual_wf_id)
    assert state.get("completed") is True, f"Workflow did not complete! State: {state}"
    assert state["status"] == "COMPLETED"
    assert len(state["raw_jobs_collected"]) == 5
    assert len(state["parsed_jobs"]) == 5
    total_evaluated = len(state["ranked_matches"]) + len(state["disqualified_matches"])
    assert total_evaluated == 5, f"Expected 5 evaluated matches, got {total_evaluated}"


def test_dag_boundary_zero_companies():
    """
    Boundary Condition 4: Empty company list returned by company discovery (0 companies).
    Ensure MasterAgent cleanly terminates without hanging.
    """
    broker = MessageBroker()
    master = MasterAgent()
    master.run(block=False)

    actual_wf_id = master.start_workflow(
        goal="Search in non-existent universe",
        custom_companies=[]
    )

    # Publish empty companies list
    broker.publish(
        queue_name="master_queue",
        payload={"companies": []},
        source="company_list_agent",
        target="master",
        msg_type="task_response",
        correlation_id=actual_wf_id
    )

    start = time.time()
    timeout = 5.0
    while time.time() - start < timeout:
        state = master.active_workflows.get(actual_wf_id)
        if state and state.get("completed"):
            break
        time.sleep(0.2)

    state = master.active_workflows.get(actual_wf_id)
    assert state is not None
    assert state.get("completed") is True, "Deadlocked on 0 companies boundary!"
    assert state["status"] == "COMPLETED"
    assert len(state["companies"]) == 0
    assert len(state["raw_jobs_collected"]) == 0


def test_dag_concurrent_workflows():
    """
    Stress test: Execute 2 independent workflows concurrently on the same MasterAgent.
    Verify correlation_id isolation, zero data cross-talk, and both reach COMPLETED.
    """
    broker = MessageBroker()
    master = MasterAgent()
    master.run(block=False)

    parser = JobParsingAgent()
    parser.run(block=False)

    matcher = MatchingAgent()
    matcher.run(block=False)

    comp_wf1 = [{"id": "CW1", "name": "Concurrent Co 1", "career_url": "https://c1.example.com"}]
    comp_wf2 = [{"id": "CW2", "name": "Concurrent Co 2", "career_url": "https://c2.example.com"}]

    wf1_id = master.start_workflow(goal="Concurrent Workflow 1", custom_companies=comp_wf1)
    wf2_id = master.start_workflow(goal="Concurrent Workflow 2", custom_companies=comp_wf2)

    assert wf1_id != wf2_id

    # Dispatch company list responses
    broker.publish("master_queue", {"companies": comp_wf1}, "company_list_agent", "master", "task_response", correlation_id=wf1_id)
    broker.publish("master_queue", {"companies": comp_wf2}, "company_list_agent", "master", "task_response", correlation_id=wf2_id)

    time.sleep(0.2)

    # Dispatch job search responses
    jobs_wf1 = [make_mock_job_page("Concurrent Co 1", 1)]
    jobs_wf2 = [make_mock_job_page("Concurrent Co 2", 1)]

    broker.publish("master_queue", {"company_id": "CW1", "company_name": "Concurrent Co 1", "raw_jobs": jobs_wf1, "count": 1}, "job_search_agent", "master", "task_response", correlation_id=wf1_id)
    broker.publish("master_queue", {"company_id": "CW2", "company_name": "Concurrent Co 2", "raw_jobs": jobs_wf2, "count": 1}, "job_search_agent", "master", "task_response", correlation_id=wf2_id)

    # Await both completions
    start = time.time()
    timeout = 20.0
    while time.time() - start < timeout:
        s1 = master.active_workflows.get(wf1_id)
        s2 = master.active_workflows.get(wf2_id)
        if s1 and s1.get("completed") and s2 and s2.get("completed"):
            break
        time.sleep(0.3)

    s1 = master.active_workflows.get(wf1_id)
    s2 = master.active_workflows.get(wf2_id)

    assert s1.get("completed") is True, f"Workflow 1 failed to complete: {s1}"
    assert s2.get("completed") is True, f"Workflow 2 failed to complete: {s2}"

    # Verify no cross-talk
    assert s1["companies"][0]["name"] == "Concurrent Co 1"
    assert s2["companies"][0]["name"] == "Concurrent Co 2"
