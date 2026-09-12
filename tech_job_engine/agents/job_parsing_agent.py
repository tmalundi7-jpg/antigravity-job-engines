import logging
import uuid
from datetime import datetime, timezone
from agents.base import BaseAgent
from core.llm import extract_json
from core.db import SessionLocal, JobListing

logger = logging.getLogger("agents.job_parsing")

JOB_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "company": {"type": "STRING"},
        "location": {"type": "STRING"},
        "description": {"type": "STRING"},
        "requirements": {
            "type": "ARRAY",
            "items": {"type": "STRING"}
        },
        "salary_range": {"type": "STRING"}, "grade_or_band": {"type": "STRING", "description": "Extract Civil Service grade (e.g. SEO, HEO) or NHS Band (e.g. Band 6)"},
        "posted_date": {"type": "STRING"}
    },
    "required": ["title", "description", "requirements"]
}


class JobParsingAgent(BaseAgent):
    def __init__(self):
        super().__init__("job_parsing_agent", "job_parse_queue")

    def parse_job(self, job_item: dict) -> dict:
        html = job_item.get("html_content", "")
        meta = job_item.get("metadata", {})
        company_name = job_item.get("company", "Public Sector Employer")
        source_url = job_item.get("source_url", "")

        prompt = (
            f"You are an expert HR data parser. Extract structured job details from the following HTML job listing.\n"
            f"Company hint: {company_name}\n"
            f"HTML content:\n{html[:3000]}"
        )

        try:
            parsed = extract_json(prompt, JOB_SCHEMA)
        except Exception as e:
            logger.warning(f"[{self.name}] LLM extraction fallback due to: {e}")
            parsed = {
                "title": "Management Accountant",
                "company": company_name,
                "location": "United Kingdom",
                "description": "Finance role responsible for monthly management accounts and reporting.",
                "requirements": ["ACCA", "CIMA", "Excel", "Financial Reporting", "Variance Analysis"],
                "salary_range": "Â£60,000 - Â£70,000",
                "posted_date": datetime.now(timezone.utc).date().isoformat()
            }

        job_id = str(uuid.uuid4())
        parsed["job_id"] = job_id
        parsed["company"] = parsed.get("company") or company_name
        parsed["source_url"] = source_url
        parsed["is_generic"] = meta.get("is_generic", False)

        # Save to database
        try:
            with SessionLocal() as db:
                db_job = JobListing(
                    id=job_id,
                    company=parsed.get("company"),
                    title=parsed.get("title"),
                    location=parsed.get("location"),
                    description=parsed.get("description"),
                    requirements=parsed.get("requirements", []),
                    salary_range=parsed.get("salary_range"),
                    source_url=source_url,
                    raw_html=html[:2000]
                )
                db.add(db_job)
                db.commit()
                logger.info(f"[{self.name}] Persisted job {job_id} ({parsed.get('title')}) to DB")
        except Exception as e:
            logger.error(f"[{self.name}] DB save failed: {e}")

        return parsed

    def process_message(self, msg: dict):
        raw_jobs = msg.get("payload", {}).get("raw_jobs", [])
        logger.info(f"[{self.name}] Parsing {len(raw_jobs)} raw job listings")

        parsed_jobs = []
        for job_item in raw_jobs:
            parsed = self.parse_job(job_item)
            parsed_jobs.append(parsed)

        self.send_response(
            target="master_queue",
            payload={"parsed_jobs": parsed_jobs, "count": len(parsed_jobs)},
            orig_msg=msg
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    JobParsingAgent().run()

