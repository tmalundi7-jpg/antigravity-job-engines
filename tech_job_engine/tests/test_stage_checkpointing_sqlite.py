import time
import uuid
import pytest
from core.db import init_db, SessionLocal, WorkflowState
import core.db as db_module
from core.messaging import MessageBroker
from agents.job_parsing_agent import JobParsingAgent
from agents.matching_agent import MatchingAgent
from agents.master_agent import MasterAgent


def test_workflow_state_transitions_through_all_five_stages_in_sqlite():
    """
    Empirically verify that WorkflowState transitions through all 5 stages in SQLite:
      Stage 1: STAGE_1_COMPANY_LIST
      Stage 2: STAGE_2_JOB_DISCOVERY
      Stage 3: STAGE_3_JOB_PARSING
      Stage 4: STAGE_4_MATCHING
      Stage 5: COMPLETED

    Directly queries the SQLite database at each checkpoint transition to verify
    the state was committed to disk.
    """
    init_db()
    broker = MessageBroker()
    master = MasterAgent()
    master.run(block=False)

    parser = JobParsingAgent()
    parser.run(block=False)

    matcher = MatchingAgent()
    matcher.run(block=False)

    # Instrument checkpoint_workflow to record and verify every committed SQLite row
    original_checkpoint = db_module.checkpoint_workflow
    recorded_sqlite_transitions = []

    def checkpoint_spy(workflow_id, status, data=None):
        # Call original function to commit to SQLite
        res = original_checkpoint(workflow_id, status, data)
        # Immediately read back from SQLite to verify empirical persistence
        with SessionLocal() as session:
            record = session.query(WorkflowState).filter(WorkflowState.id == workflow_id).first()
            if record:
                recorded_sqlite_transitions.append({
                    "workflow_id": workflow_id,
                    "status_written": status,
                    "status_in_db": record.status,
                    "stage_data": dict(record.data or {}),
                    "updated_at": record.updated_at
                })
        return res

    # Patch checkpoint_workflow with spy
    import agents.master_agent as master_module
    old_master_ckpt = master_module.checkpoint_workflow
    master_module.checkpoint_workflow = checkpoint_spy

    try:
        test_company = [{"id": "STAGE_CO", "name": "Stage Checkpoint plc", "career_url": "https://stage.example.com"}]

        # 1. Start workflow -> Triggers Stage 1 checkpoint
        wf_id = master.start_workflow(
            goal="Stage Progression Audit",
            custom_companies=test_company
        )

        time.sleep(0.2)

        # 2. Simulate Company Discovery Response -> Triggers Stage 2 checkpoint
        broker.publish(
            queue_name="master_queue",
            payload={"companies": test_company},
            source="company_list_agent",
            target="master",
            msg_type="task_response",
            correlation_id=wf_id
        )

        time.sleep(0.2)

        # 3. Simulate Job Discovery Response with jobs -> Triggers Stage 3 checkpoint
        job_mock = {
            "source_url": "https://stage.example.com/job/1",
            "html_content": "<html><body><h2>Management Accountant</h2><p>Location: London</p><p>ACCA, Excel</p></body></html>",
            "metadata": {"company_name": "Stage Checkpoint plc", "page": 1}
        }
        broker.publish(
            queue_name="master_queue",
            payload={"company_id": "STAGE_CO", "company_name": "Stage Checkpoint plc", "raw_jobs": [job_mock], "count": 1},
            source="job_search_agent",
            target="master",
            msg_type="task_response",
            correlation_id=wf_id
        )

        # 4 & 5. Parser and Matcher are running in background, which will trigger
        # Stage 4 (Matching) and Stage 5 (COMPLETED)
        start = time.time()
        timeout = 20.0
        while time.time() - start < timeout:
            state = master.active_workflows.get(wf_id)
            if state and state.get("completed"):
                break
            time.sleep(0.3)

        state = master.active_workflows.get(wf_id)
        assert state is not None
        assert state.get("completed") is True, f"Workflow did not complete: {state}"

        # Extract sequence of statuses written to SQLite for this workflow
        wf_transitions = [t for t in recorded_sqlite_transitions if t["workflow_id"] == wf_id]
        statuses = [t["status_in_db"] for t in wf_transitions]

        expected_five_stages = [
            "STAGE_1_COMPANY_LIST",
            "STAGE_2_JOB_DISCOVERY",
            "STAGE_3_JOB_PARSING",
            "STAGE_4_MATCHING",
            "COMPLETED"
        ]

        # Verify that all 5 stages occurred in sequence in SQLite
        for stage in expected_five_stages:
            assert stage in statuses, f"Stage '{stage}' was NOT recorded in SQLite! Observed: {statuses}"

        # Verify order of progression
        first_indices = [statuses.index(s) for s in expected_five_stages]
        assert first_indices == sorted(first_indices), f"Stages did not transition in order! Indices: {first_indices}"

        # Verify payload data stored at each stage
        stage_1_data = next(t["stage_data"] for t in wf_transitions if t["status_in_db"] == "STAGE_1_COMPANY_LIST")
        assert "goal" in stage_1_data and stage_1_data["goal"] == "Stage Progression Audit"
        assert "params" in stage_1_data

        stage_2_data = next(t["stage_data"] for t in wf_transitions if t["status_in_db"] == "STAGE_2_JOB_DISCOVERY")
        assert stage_2_data.get("companies_count") == 1
        assert "Stage Checkpoint plc" in stage_2_data.get("companies", [])

        stage_3_data = next(t["stage_data"] for t in wf_transitions if t["status_in_db"] == "STAGE_3_JOB_PARSING")
        assert stage_3_data.get("total_raw_jobs") == 1

        stage_4_data = next(t["stage_data"] for t in wf_transitions if t["status_in_db"] == "STAGE_4_MATCHING")
        assert stage_4_data.get("total_parsed_jobs") == 1

        stage_5_data = next(t["stage_data"] for t in wf_transitions if t["status_in_db"] == "COMPLETED")
        assert "executive_report_markdown" in stage_5_data
        assert stage_5_data.get("total_companies") == 1
        assert stage_5_data.get("total_matched") + stage_5_data.get("total_disqualified") == 1

    finally:
        master_module.checkpoint_workflow = old_master_ckpt


def test_stage_checkpointing_under_zero_jobs():
    """
    Verify stage checkpointing behavior when 0 jobs are found.
    Empirically documents the exact SQLite state transitions when discovery returns 0 jobs.
    """
    init_db()
    broker = MessageBroker()
    master = MasterAgent()
    master.run(block=False)

    original_checkpoint = db_module.checkpoint_workflow
    recorded_transitions = []

    def checkpoint_spy(workflow_id, status, data=None):
        res = original_checkpoint(workflow_id, status, data)
        with SessionLocal() as session:
            record = session.query(WorkflowState).filter(WorkflowState.id == workflow_id).first()
            if record:
                recorded_transitions.append({
                    "workflow_id": workflow_id,
                    "status_in_db": record.status,
                    "stage_data": dict(record.data or {})
                })
        return res

    import agents.master_agent as master_module
    old_master_ckpt = master_module.checkpoint_workflow
    master_module.checkpoint_workflow = checkpoint_spy

    try:
        test_company = [{"id": "ZERO_JOB_CO", "name": "Zero Jobs Co", "career_url": "https://zero.example.com"}]

        wf_id = master.start_workflow(
            goal="Zero Jobs Checkpoint Test",
            custom_companies=test_company
        )

        time.sleep(0.2)

        # Stage 2: Company Discovery
        broker.publish(
            queue_name="master_queue",
            payload={"companies": test_company},
            source="company_list_agent",
            target="master",
            msg_type="task_response",
            correlation_id=wf_id
        )

        time.sleep(0.2)

        # Stage 2 Search response with 0 jobs
        broker.publish(
            queue_name="master_queue",
            payload={"company_id": "ZERO_JOB_CO", "company_name": "Zero Jobs Co", "raw_jobs": [], "count": 0},
            source="job_search_agent",
            target="master",
            msg_type="task_response",
            correlation_id=wf_id
        )

        start = time.time()
        timeout = 10.0
        while time.time() - start < timeout:
            state = master.active_workflows.get(wf_id)
            if state and state.get("completed"):
                break
            time.sleep(0.2)

        wf_transitions = [t for t in recorded_transitions if t["workflow_id"] == wf_id]
        statuses = [t["status_in_db"] for t in wf_transitions]

        # In 0-job condition, Stage 1 -> Stage 2 -> COMPLETED
        assert "STAGE_1_COMPANY_LIST" in statuses
        assert "STAGE_2_JOB_DISCOVERY" in statuses
        assert "COMPLETED" in statuses

        # Final record in SQLite
        with SessionLocal() as session:
            final_record = session.query(WorkflowState).filter(WorkflowState.id == wf_id).first()
            assert final_record.status == "COMPLETED"
            assert final_record.data.get("total_raw_jobs") == 0
            assert final_record.data.get("total_parsed_jobs") == 0
    finally:
        master_module.checkpoint_workflow = old_master_ckpt
