import sys
import os
import time
import logging
import argparse

# Setup path and environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from core.db import init_db
from agents.source_dispatch_agent import SourceDispatchAgent
from agents.job_search_agent import JobSearchAgent
from agents.job_parsing_agent import JobParsingAgent
from agents.matching_agent import MatchingAgent
from agents.master_agent import MasterAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Runner")

def run_pipeline(goal: str, timeout_seconds: int = 60, universe: str = None,
                 include_entry_level: bool = True, limit: int = None):
    logger.info("==================================================================")
    logger.info("Starting FTSE Multi-Agent Job Search & Matching Engine")
    logger.info("==================================================================")

    # Override universe in goal if --universe was explicitly provided
    if universe:
        logger.info(f"Universe override: '{universe}'")

    # 1. Initialize relational database schema
    logger.info("Initializing relational database schema...")
    init_db()

    # 2. Instantiate and launch all sub-agents in non-blocking daemon threads
    logger.info("Launching sub-agents into local message bus...")
    dispatch_agent = SourceDispatchAgent()
    dispatch_agent.run(block=False)

    search_agent = JobSearchAgent()
    search_agent.run(block=False)

    parse_agent = JobParsingAgent()
    parse_agent.run(block=False)

    match_agent = MatchingAgent()
    match_agent.run(block=False)

    master = MasterAgent()
    master.run(block=False)

    time.sleep(0.5)

    # 3. Build candidate profile with entry-level flag passed into search params
    candidate_profile = None  # use master agent default

    # 4. Build custom company limit payload (passed via custom_companies placeholder)
    #    The limit is handled inside SourceDispatchAgent.process_message via payload["limit"]
    # We need to start the workflow and inject the limit and universe overrides.
    # We do this by temporarily monkeypatching the company list queue message.
    # Cleanest approach: pass a custom_companies=None with limit hint via a wrapper.
    # Actually, the cleanest is to start_workflow and then pass a supplemental payload.
    # For now, we inject limit via a start_workflow override:

    logger.info(f"Submitting high-level user goal: '{goal}'")

    # Patch broker to inject limit/universe into Stage 1 request
    original_publish = master.broker.publish
    _patched = [False]

    def _patching_publish(queue_name, payload, **kwargs):
        if not _patched[0] and queue_name == "company_list_queue":
            _patched[0] = True
            if universe:
                payload["universe"] = universe
            if limit:
                payload["limit"] = limit
            # Pass include_entry_level flag for job_search_agent to pick up
            payload["include_entry_level"] = include_entry_level
            logger.info(f"[Runner] Injected into company_list_queue: universe={payload.get('universe')}, limit={payload.get('limit')}")
        return original_publish(queue_name, payload, **kwargs)

    master.broker.publish = _patching_publish

    # Also patch job_search_queue messages to pass include_entry_level
    original_publish2 = master.broker.publish
    _search_patched = False

    def _patching_publish_search(queue_name, payload, **kwargs):
        nonlocal _search_patched
        if queue_name == "job_search_queue":
            sp = payload.get("search_parameters", {})
            sp["include_entry_level"] = include_entry_level
            payload["search_parameters"] = sp
        return original_publish2(queue_name, payload, **kwargs)

    master.broker.publish = _patching_publish_search

    workflow_id = master.start_workflow(goal)

    # 5. Monitor progress until completion or timeout
    start_time = time.time()
    completed = False
    report = None

    while time.time() - start_time < timeout_seconds:
        state = master.active_workflows.get(workflow_id)
        if state and state.get("completed"):
            completed = True
            report = state
            break

        status = state.get("status") if state else "STARTING"
        logger.info(f"Pipeline running... Current Status: {status}")
        time.sleep(2.0)

    if not completed:
        logger.error(f"Pipeline timed out after {timeout_seconds} seconds!")
        return None

    # 6. Display executive summary
    matches = report.get("ranked_matches", [])
    logger.info("==================================================================")
    logger.info("PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("==================================================================")
    logger.info(f"Goal: {goal}")
    logger.info(f"Target Universe: {report.get('params', {}).get('universe')}")
    logger.info(f"Target Role: {report.get('params', {}).get('role')}")
    logger.info(f"Total Companies Scanned: {len(report.get('companies', []))}")
    logger.info(f"Total Jobs Discovered: {len(report.get('raw_jobs_collected', []))}")
    logger.info(f"Total Jobs Parsed: {len(report.get('parsed_jobs', []))}")
    logger.info(f"Total Matches Scored: {len(matches)}")
    logger.info("------------------------------------------------------------------")

    for i, match in enumerate(matches, 1):
        logger.info(f"#{i} | Score: {match['final_score']}/100 | {match['job_title']} at {match['company']}")
        logger.info(f"     Location: {match['location']} | Salary: {match.get('salary_range', 'Competitive')}")
        logger.info(f"     Breakdown: {match.get('score_breakdown')}")
        logger.info(f"     Reasoning: {match.get('reasoning')}")
        logger.info(f"     Link: {match.get('source_url')}")
        logger.info("------------------------------------------------------------------")

    # 7. Print report file locations
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(workspace_dir, "reports")
    exec_report_path    = os.path.join(reports_dir, "executive_report.md")
    roles_report_path   = os.path.join(reports_dir, "available_roles_report.md")
    exec_xlsx_path      = os.path.join(reports_dir, "executive_report.xlsx")
    roles_xlsx_path     = os.path.join(reports_dir, "available_roles_report.xlsx")
    generic_xlsx_path   = os.path.join(reports_dir, "generic_roles_report.xlsx")

    all_parsed = report.get("parsed_jobs", [])
    finance_count = sum(1 for j in all_parsed if not j.get("is_generic"))
    generic_count = sum(1 for j in all_parsed if j.get("is_generic"))

    logger.info("==================================================================")
    logger.info("REPORTS GENERATED (all saved to reports/ folder):")
    logger.info(f"  [1] Finance/Accounting Matched  -> executive_report.xlsx")
    logger.info(f"  [2] All Finance Roles Available  -> available_roles_report.xlsx")
    logger.info(f"  [3] Generic / All Other Roles    -> generic_roles_report.xlsx")
    logger.info("------------------------------------------------------------------")
    logger.info(f"  Finance Roles Found          : {finance_count}")
    logger.info(f"  Generic Roles Found          : {generic_count}")
    logger.info(f"  Total Matched to Candidate   : {len(matches)}")
    logger.info(f"  Reports Folder               : {reports_dir}")
    logger.info("==================================================================")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FTSE Multi-Agent Job Engine Runner")
    parser.add_argument(
        "--goal",
        default="Find public sector finance, accounting, audit, and tax roles across the UK (NHS, Civil Service, Local Gov) including entry level positions",
        help="High-level user search goal"
    )
    parser.add_argument("--timeout", type=int, default=3600, help="Pipeline timeout in seconds")
    parser.add_argument(
        "--universe",
        default=None,
        help=(
            "Comma-separated FTSE index names to search, e.g. "
            "'FTSE 100,FTSE 250,FTSE AIM 100 Index'. "
            "Supported: FTSE 100, FTSE 250, FTSE 350, FTSE All-Share, "
            "FTSE AIM UK 50 Index, FTSE AIM 100 Index, FTSE AIM All-Share, "
            "FTSE MID 250 (ex IT), FTSE 350 High Yield, FTSE 350 Low Yield, "
            "FTSE 350 (ex IT), FTSE All-Share (ex IT), "
            "FTSE 4Good UK Idx, FTSE 4Good USA Idx, FTSE 4Good Global Idx, FTSE 4Good Europe Idx"
        )
    )
    parser.add_argument(
        "--location",
        default=None,
        help=(
            "Optional location filter, e.g. 'Manchester', 'Birmingham', 'Edinburgh'. "
            "Omit (or leave blank) to search all of the UK."
        )
    )
    parser.add_argument(
        "--no-entry-level",
        action="store_true",
        default=False,
        help="Disable automatic entry-level role expansion (Graduate, Junior, Trainee, etc.)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of portals per run (e.g. --limit 5 for quick testing)"
    )
    args = parser.parse_args()

    # If a specific location was given, append it to the goal so the LLM extracts it
    goal = args.goal
    if args.location:
        goal = f"{goal} in {args.location}"

    run_pipeline(
        goal=goal,
        timeout_seconds=args.timeout,
        universe=args.universe,
        include_entry_level=not args.no_entry_level,
        limit=args.limit,
    )

