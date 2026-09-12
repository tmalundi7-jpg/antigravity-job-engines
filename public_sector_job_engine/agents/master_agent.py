import os
import logging
import uuid
import time
import json
import threading
from datetime import datetime, timezone
from agents.base import BaseAgent
from core.llm import extract_json
from core.db import SessionLocal, WorkflowState, checkpoint_workflow
from core.excel_exporter import export_executive_report_excel, export_available_roles_excel, export_generic_roles_excel

logger = logging.getLogger("agents.master")

INTENT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "role": {"type": "STRING"},
        "universe": {"type": "STRING"},
        "filters": {
            "type": "OBJECT",
            "properties": {
                "location": {"type": "STRING"},
                "min_salary": {"type": "NUMBER"},
                "seniority": {"type": "STRING"}
            }
        },
        "candidate_id": {"type": "STRING"}
    },
    "required": ["role", "universe"]
}


class MasterAgent(BaseAgent):
    def __init__(self):
        super().__init__("master", "master_queue")
        self.broker.declare_queue("company_list_queue")
        self.broker.declare_queue("job_search_queue")
        self.broker.declare_queue("job_parse_queue")
        self.broker.declare_queue("matching_queue")

        # State tracking per workflow — protected by RLock
        self._state_lock = threading.RLock()
        self.active_workflows = {}
        self.completed_reports = {}

    def start_workflow(self, goal: str, candidate_profile: dict = None, custom_companies: list = None) -> str:
        workflow_id = str(uuid.uuid4())
        logger.info(f"[{self.name}] Initiating workflow [{workflow_id}] for goal: '{goal}'")

        prompt = (
            f"You are the Master Orchestration Agent. Extract structured parameters from the user goal.\n"
            f"Goal: {goal}\n"
            f"Extract target role, universe (FTSE 100/FTSE 250/all), and any filters."
        )

        try:
            params = extract_json(prompt, INTENT_SCHEMA)
        except Exception as e:
            logger.warning(f"[{self.name}] LLM intent parsing fallback ({e})")
            params = {
                "role": "Management Accountant",
                "universe": "FTSE 250",
                "filters": {"location": "United Kingdom"}
            }

        logger.info(f"[{self.name}] Extracted parameters: {params}")

        # Initialize workflow tracking state with balanced 3-stage counter pairs
        now_utc = datetime.now(timezone.utc)
        workflow_state = {
            "workflow_id": workflow_id,
            "goal": goal,
            "params": params,
            "custom_companies": custom_companies,
            "candidate": candidate_profile or {
                "id": params.get("candidate_id", "cand_123"),
                "name": "Candidate A",
                "title": params.get("role", "Management Accountant"),
                "skills": ["ACCA", "Financial Reporting", "Variance Analysis", "Excel", "Budgeting", "CIMA"],
                "years_experience": 5,
                "certifications": ["ACCA Qualified"],
                "location": params.get("filters", {}).get("location", "United Kingdom")
            },
            "status": "STAGE_1_COMPANY_LIST",
            "companies": [],
            "raw_jobs_collected": [],
            "parsed_jobs": [],
            "ranked_matches": [],
            "disqualified_matches": [],
            "expected_searches": 0,
            "completed_searches": 0,
            "dispatched_parses": 0,
            "completed_parses": 0,
            "dispatched_matches": 0,
            "completed_matches": 0,
            "start_time": now_utc.isoformat(),
            "start_ts": time.time(),
            "completed": False
        }
        with self._state_lock:
            self.active_workflows[workflow_id] = workflow_state

        # Stage 1 Checkpoint: Persist initial state to Database (right after registration)
        checkpoint_workflow(
            workflow_id=workflow_id,
            status="STAGE_1_COMPANY_LIST",
            data={
                "workflow_id": workflow_id,
                "stage": "STAGE_1_COMPANY_LIST",
                "stage_name": "Company Discovery",
                "goal": goal,
                "params": params,
                "candidate_id": workflow_state["candidate"].get("id"),
                "candidate_name": workflow_state["candidate"].get("name"),
                "started_at": workflow_state["start_time"]
            }
        )

        # Stage 1: Request Company Constituent List
        req_payload = {"universe": params.get("universe", "FTSE 250")}
        if custom_companies:
            req_payload["custom_companies"] = custom_companies

        self.broker.publish(
            queue_name="company_list_queue",
            payload=req_payload,
            source=self.name,
            target="company_list_agent",
            msg_type="task_request",
            correlation_id=workflow_id
        )

        return workflow_id

    def process_message(self, msg: dict):
        msg_type = msg.get("type")
        source = msg.get("source_agent")
        payload = msg.get("payload", {})
        workflow_id = msg.get("correlation_id")

        with self._state_lock:
            state = self.active_workflows.get(workflow_id)
        if not state:
            logger.warning(f"[{self.name}] Received message for untracked workflow: {workflow_id}")
            return

        logger.info(f"[{self.name}] Processed {msg_type} from {source} for workflow [{workflow_id[:8]}]")

        # Stage 1 Response -> Dispatch Stage 2: Job Searches
        if source == "company_list_agent" and msg_type == "task_response":
            companies = payload.get("companies", [])
            state["companies"] = companies
            state["expected_searches"] = len(companies)
            state["status"] = "STAGE_2_JOB_DISCOVERY"
            logger.info(f"[{self.name}] Discovered {len(companies)} companies. Dispatching search tasks...")

            # Stage 2 Checkpoint: Persist discovered companies
            checkpoint_workflow(
                workflow_id=workflow_id,
                status="STAGE_2_JOB_DISCOVERY",
                data={
                    "stage": "STAGE_2_JOB_DISCOVERY",
                    "companies_count": len(companies),
                    "companies": [c.get("name") for c in companies],
                    "expected_searches": len(companies),
                    "completed_searches": 0,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            )

            if not companies:
                self._check_and_finalize_if_complete(workflow_id)
                return

            for comp in companies:
                self.broker.publish(
                    queue_name="job_search_queue",
                    payload={
                        "company": comp,
                        "search_parameters": {
                            "keywords": [state["params"].get("role", "Management Accountant")],
                            "location": state["params"].get("filters", {}).get("location", "United Kingdom")
                        }
                    },
                    source=self.name,
                    target="job_search_agent",
                    msg_type="task_request",
                    correlation_id=workflow_id
                )

        # Stage 2 Response -> Collect raw jobs & dispatch Stage 3: Parsing
        elif source == "job_search_agent" and msg_type == "task_response":
            raw_jobs = payload.get("raw_jobs", [])
            with self._state_lock:
                state["raw_jobs_collected"].extend(raw_jobs)
                state["completed_searches"] += 1

                # Once search tasks return raw jobs, dispatch for parsing
                if raw_jobs:
                    state["dispatched_parses"] += 1
                    state["status"] = "STAGE_3_JOB_PARSING"
                    checkpoint_workflow(
                        workflow_id=workflow_id,
                        status="STAGE_3_JOB_PARSING",
                        data={
                            "stage": "STAGE_3_JOB_PARSING",
                            "total_raw_jobs": len(state["raw_jobs_collected"]),
                            "dispatched_parses": state["dispatched_parses"],
                            "completed_searches": state["completed_searches"],
                            "expected_searches": state["expected_searches"],
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    self.broker.publish(
                        queue_name="job_parse_queue",
                        payload={"raw_jobs": raw_jobs},
                        source=self.name,
                        target="job_parsing_agent",
                        msg_type="task_request",
                        correlation_id=workflow_id
                    )
                # 0-job edge case: search completed with nothing to parse;
                # still check completion so the workflow isn't stalled.

            self._check_and_finalize_if_complete(workflow_id)

        # Stage 3 Response -> Dispatch Stage 4: Matching
        elif source == "job_parsing_agent" and msg_type == "task_response":
            parsed_jobs = payload.get("parsed_jobs", [])
            state["parsed_jobs"].extend(parsed_jobs)
            state["completed_parses"] += 1

            # Only send NON-generic roles (Finance/Accountant) to matching
            finance_jobs = [j for j in parsed_jobs if not j.get("is_generic")]

            if finance_jobs:
                state["dispatched_matches"] += 1
                state["status"] = "STAGE_4_MATCHING"
                logger.info(f"[{self.name}] Received {len(parsed_jobs)} parsed jobs ({len(finance_jobs)} finance). Dispatching to matching...")

                checkpoint_workflow(
                    workflow_id=workflow_id,
                    status="STAGE_4_MATCHING",
                    data={
                        "stage": "STAGE_4_MATCHING",
                        "total_parsed_jobs": len(state["parsed_jobs"]),
                        "dispatched_matches": state["dispatched_matches"],
                        "completed_parses": state["completed_parses"],
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                )

                self.broker.publish(
                    queue_name="matching_queue",
                    payload={
                        "candidate": state["candidate"],
                        "parsed_jobs": finance_jobs
                    },
                    source=self.name,
                    target="matching_agent",
                    msg_type="task_request",
                    correlation_id=workflow_id
                )

            self._check_and_finalize_if_complete(workflow_id)

        # Stage 4 Response -> Stage 5: Aggregation & Final Reporting
        elif source == "matching_agent" and msg_type == "task_response":
            ranked_matches = payload.get("ranked_matches", [])
            state["ranked_matches"].extend(ranked_matches)
            state["ranked_matches"].sort(key=lambda x: x["final_score"], reverse=True)

            disqualified = payload.get("disqualified_matches", [])
            if disqualified:
                state["disqualified_matches"].extend(disqualified)

            state["completed_matches"] += 1
            logger.info(
                f"[{self.name}] Aggregated {len(ranked_matches)} qualified matches "
                f"(Total so far: {len(state['ranked_matches'])}, Disqualified: {len(state['disqualified_matches'])})"
            )

            self._check_and_finalize_if_complete(workflow_id)

    def _check_and_finalize_if_complete(self, workflow_id: str):
        state = self.active_workflows.get(workflow_id)
        if not state or state.get("completed"):
            return

        searches_done = state["completed_searches"] >= state["expected_searches"]
        parses_done = state["completed_parses"] >= state["dispatched_parses"]
        matches_done = state["completed_matches"] >= state["dispatched_matches"]

        if searches_done and parses_done and matches_done:
            self._finalize_workflow(workflow_id)

    def _generate_executive_report_markdown(self, state: dict) -> str:
        candidate = state.get("candidate", {})
        matches = state.get("ranked_matches", [])
        disqualified = state.get("disqualified_matches", [])
        duration = round(time.time() - state.get("start_ts", time.time()), 2)
        top_match = matches[0] if matches else None

        lines = [
            "# FTSE Multi-Agent Job Search & Matching Executive Report",
            "",
            f"**Workflow ID**: `{state.get('workflow_id')}`  ",
            f"**Goal**: {state.get('goal')}  ",
            f"**Target Role**: {state.get('params', {}).get('role')}  ",
            f"**Universe**: {state.get('params', {}).get('universe')}  ",
            f"**Execution Duration**: {duration}s  ",
            f"**Completed At**: {state.get('completed_at')}  ",
            "",
            "## 1. Candidate Profile Summary",
            f"- **Name**: {candidate.get('name', 'N/A')}",
            f"- **Title**: {candidate.get('title', 'N/A')}",
            f"- **Years Experience**: {candidate.get('years_experience', 'N/A')}",
            f"- **Location**: {candidate.get('location', 'N/A')}",
            f"- **Key Skills**: {', '.join(candidate.get('skills', []))}",
            f"- **Certifications**: {', '.join(candidate.get('certifications', []))}",
            "",
            "## 2. Discovery & Matching Telemetry",
            f"- **Companies Evaluated**: {len(state.get('companies', []))}",
            f"- **Raw Vacancy Pages Crawled**: {len(state.get('raw_jobs_collected', []))}",
            f"- **Parsed Job Listings**: {len(state.get('parsed_jobs', []))}",
            f"- **Stage 1 Pre-filter Passed**: {len(matches)}",
            f"- **Stage 1 Disqualified**: {len(disqualified)}",
            "",
            "## 3. Ranked Recommendations (Stage 1 Passed & Scored)",
            ""
        ]

        if matches:
            lines.append("| Rank | Final Score | Job Title | Company | Location | Salary | Vector Sim | Breakdown |")
            lines.append("|---|---|---|---|---|---|---|---|")
            for idx, m in enumerate(matches, 1):
                bd = m.get("score_breakdown", {})
                bd_str = f"S:{bd.get('skills', 0)} E:{bd.get('experience', 0)} C:{bd.get('education', 0)} L:{bd.get('location', 0)}"
                lines.append(
                    f"| #{idx} | **{m.get('final_score')}** | {m.get('job_title')} | {m.get('company')} | "
                    f"{m.get('location')} | {m.get('salary_range', 'Competitive')} | {m.get('similarity_score')} | {bd_str} |"
                )
            lines.append("")
            lines.append("### Detailed Top Match Rationale")
            lines.append(f"> **{top_match['job_title']} at {top_match['company']}** (Score: {top_match['final_score']}/100)")
            lines.append(f"> {top_match.get('reasoning')}")
        else:
            lines.append("No jobs passed the Stage 1 vector cosine similarity pre-filter (threshold >= 0.65).")

        if disqualified:
            lines.append("")
            lines.append("## 4. Disqualified Vacancies (Failed Stage 1 Pre-Filter < 0.65)")
            lines.append("| Job Title | Company | Similarity Score | Reason |")
            lines.append("|---|---|---|---|")
            for d in disqualified[:10]:
                lines.append(f"| {d.get('job_title')} | {d.get('company')} | {d.get('similarity_score')} | {d.get('reasoning')} |")

        return "\n".join(lines)

    def _generate_available_roles_report_markdown(self, state: dict) -> str:
        """
        Generates a comprehensive markdown report listing ALL parsed jobs found
        across every company, regardless of candidate match score.
        Organized by company with seniority level, location, salary and source URL.
        """
        parsed_jobs = state.get("parsed_jobs", [])
        companies = state.get("companies", [])
        params = state.get("params", {})
        duration = round(time.time() - state.get("start_ts", time.time()), 2)

        # Group jobs by company
        from collections import defaultdict
        by_company: dict[str, list] = defaultdict(list)
        for job in parsed_jobs:
            company_name = job.get("company", job.get("company_name", "Unknown Company"))
            by_company[company_name].append(job)

        # Get indices searched (from companies list)
        all_indices: set[str] = set()
        for comp in companies:
            all_indices.update(comp.get("index_tags", []))

        lines = [
            "# Available Roles Found — FTSE Universe Search",
            "",
            f"**Workflow ID**: `{state.get('workflow_id')}`  ",
            f"**Goal**: {state.get('goal')}  ",
            f"**Search Date**: {state.get('completed_at', 'N/A')}  ",
            f"**Target Universe**: {params.get('universe', 'N/A')}  ",
            f"**Indices Searched**: {', '.join(sorted(all_indices)) if all_indices else params.get('universe', 'N/A')}  ",
            f"**Execution Duration**: {duration}s  ",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"| Metric | Count |",
            f"|---|---|",
            f"| Companies Scanned | {len(companies)} |",
            f"| Total Roles Found | {len(parsed_jobs)} |",
            f"| Companies with Roles | {len(by_company)} |",
            f"| Entry-Level Roles | "
            f"{sum(1 for j in parsed_jobs if any(kw in j.get('title', '').lower() for kw in ['graduate', 'junior', 'trainee', 'assistant', 'entry level']))} |",
            f"| Experienced Roles | "
            f"{sum(1 for j in parsed_jobs if not any(kw in j.get('title', '').lower() for kw in ['graduate', 'junior', 'trainee', 'assistant', 'entry level']))} |",
            "",
            "---",
            "",
            "## Roles by Company",
            "",
        ]

        if not parsed_jobs:
            lines.append("*No roles were found during this search run.*")
            return "\n".join(lines)

        for i, (company_name, jobs) in enumerate(sorted(by_company.items()), 1):
            # Get company metadata from companies list
            company_meta = next(
                (c for c in companies if c.get("name", "").lower() == company_name.lower()),
                {}
            )
            sector = company_meta.get("sector", "Public Sector")
            sector = company_meta.get("sector", "Unknown")
            index_label = sector
            career_url = company_meta.get("career_url", "")

            lines.append(f"### {i}. {company_name}")
            if index_label or sector:
                meta_parts = []
                if index_label:
                    meta_parts.append(f"**Sector**: {index_label}")
                if sector:
                    meta_parts.append(f"")
                if career_url:
                    meta_parts.append(f"[Careers Page]({career_url})")
                lines.append("  ".join(meta_parts))
            lines.append("")
            lines.append("| # | Role Title | Level | Location | Salary | Source |")
            lines.append("|---|---|---|---|---|---|")

            for j_idx, job in enumerate(jobs, 1):
                title = job.get("title", "Unknown Role")
                location = job.get("location", "London")
                salary = job.get("salary_range", job.get("salary", "Competitive"))
                source_url = job.get("source_url", career_url or "#")
                # Determine level
                title_lower = title.lower()
                if any(kw in title_lower for kw in ["graduate", "trainee", "entry level", "junior"]):
                    level = "Entry Level"
                elif any(kw in title_lower for kw in ["assistant"]):
                    level = "Entry / Mid"
                elif any(kw in title_lower for kw in ["senior", "head", "director", "controller", "vp", "chief"]):
                    level = "Senior"
                elif any(kw in title_lower for kw in ["manager", "lead", "principal"]):
                    level = "Manager"
                else:
                    level = "Experienced"

                source_link = f"[link]({source_url})" if source_url and source_url != "#" else "—"
                lines.append(f"| {j_idx} | {title} | {level} | {location} | {salary} | {source_link} |")

            lines.append("")

        lines.extend([
            "---",
            "",
            "*Report generated by FTSE Multi-Agent Job Search Engine*",
        ])
        return "\n".join(lines)

    def _finalize_workflow(self, workflow_id: str):
        state = self.active_workflows[workflow_id]
        state["status"] = "COMPLETED"
        state["completed"] = True
        now_utc = datetime.now(timezone.utc)
        state["completed_at"] = now_utc.isoformat()
        duration = round(time.time() - state.get("start_ts", time.time()), 2)
        state["duration_seconds"] = duration

        # Generate Executive Report
        report_md = self._generate_executive_report_markdown(state)
        state["executive_report"] = report_md

        # Generate Available Roles Report (all roles found, regardless of match)
        roles_report_md = self._generate_available_roles_report_markdown(state)
        state["available_roles_report"] = roles_report_md

        workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reports_dir = os.path.join(workspace_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)

        # Write executive report to workspace
        try:
            report_file_path = os.path.join(reports_dir, "executive_report.md")
            with open(report_file_path, "w", encoding="utf-8") as f:
                f.write(report_md)
            logger.info(f"[{self.name}] Executive report saved to: {report_file_path}")
        except Exception as e:
            logger.warning(f"[{self.name}] Could not write executive report file: {e}")

        # Write available roles report to workspace
        try:
            roles_file_path = os.path.join(reports_dir, "available_roles_report.md")
            with open(roles_file_path, "w", encoding="utf-8") as f:
                f.write(roles_report_md)
            logger.info(f"[{self.name}] Available roles report saved to: {roles_file_path}")
        except Exception as e:
            logger.warning(f"[{self.name}] Could not write available roles report file: {e}")

        # Write Excel reports
        try:
            exec_xlsx_path = os.path.join(reports_dir, "executive_report.xlsx")
            export_executive_report_excel(state, exec_xlsx_path)
            logger.info(f"[{self.name}] Successfully generated EXCEL report: {exec_xlsx_path}")
        except Exception as e:
            logger.warning(f"[{self.name}] Could not write executive Excel report: {e}")

        try:
            roles_xlsx_path = os.path.join(reports_dir, "available_roles_report.xlsx")
            export_available_roles_excel(state, roles_xlsx_path)
            logger.info(f"[{self.name}] Successfully generated EXCEL report: {roles_xlsx_path}")
        except Exception as e:
            logger.warning(f"[{self.name}] Could not write available roles Excel report: {e}")

        # Write generic roles report
        try:
            generic_xlsx_path = os.path.join(reports_dir, "generic_roles_report.xlsx")
            export_generic_roles_excel(state, generic_xlsx_path)
            logger.info(f"[{self.name}] Successfully generated EXCEL report: {generic_xlsx_path}")
        except Exception as e:
            logger.warning(f"[{self.name}] Could not write generic roles Excel report: {e}")

        logger.info(
            f"[{self.name}] *** WORKFLOW COMPLETED in {duration}s *** "
            f"Matches: {len(state['ranked_matches'])} qualified, {len(state['disqualified_matches'])} disqualified."
        )

        # Stage 5 Checkpoint: Persist completion to Database
        checkpoint_workflow(
            workflow_id=workflow_id,
            status="COMPLETED",
            data={
                "stage": "COMPLETED",
                "stage_name": "Executive Reporting & Recommendation",
                "total_companies": len(state["companies"]),
                "total_raw_jobs": len(state["raw_jobs_collected"]),
                "total_parsed_jobs": len(state["parsed_jobs"]),
                "total_matched": len(state["ranked_matches"]),
                "total_disqualified": len(state["disqualified_matches"]),
                "top_match": state["ranked_matches"][0] if state["ranked_matches"] else None,
                "top_recommendations": state["ranked_matches"][:5],
                "completed_at": state["completed_at"],
                "duration_seconds": duration,
                "executive_report_markdown": report_md
            }
        )

        self.completed_reports[workflow_id] = state

    def get_report(self, workflow_id: str) -> dict:
        return self.completed_reports.get(workflow_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = MasterAgent()
    agent.run()
