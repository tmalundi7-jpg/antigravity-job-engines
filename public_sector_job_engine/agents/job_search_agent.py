import logging
import time
import re
import urllib.parse
from datetime import datetime, timezone
import requests
from typing import Optional
from agents.base import BaseAgent

logger = logging.getLogger("agents.job_search")

_PUBLIC_SECTOR_ROLES = [
    # Accounting / Management Accounting
    "Management Accountant", "Financial Accountant", "Finance Business Partner",
    "Finance Director", "Head of Finance", "Chief Financial Officer",
    "Cost Accountant", "Project Accountant", "Finance Manager", "CIPFA Accountant",

    # Audit
    "Internal Auditor", "Senior Internal Auditor", "Audit Manager",
    "External Auditor", "IT Auditor", "Value for Money Auditor",
    "Forensic Accountant", "Audit Partner",

    # Tax
    "Tax Inspector", "Tax Investigator", "Corporate Tax Specialist",
    "VAT Specialist", "Customs & Excise Officer",

    # Public Sector / Specialized
    "Commercial Finance Lead", "Economic Advisor", "Policy Advisor - Finance",
    "Treasury Accountant", "Regulatory Reporter"
]

_ENTRY_LEVEL_STANDALONE = [
    "Graduate Finance Fast Stream", "Finance Trainee", "Trainee Accountant",
    "Assistant Management Accountant", "Junior Finance Analyst",
    "Graduate Auditor", "Trainee Auditor", "Tax Trainee",
    "Band 5 Accountant", "HEO Finance Officer", "EO Finance Assistant"
]


from urllib.parse import urlparse

def get_real_jobs_from_ddgs(portal: dict, include_entry: bool) -> list[dict]:
    '''Uses DuckDuckGo search to extract REAL job URLs when live scraping is blocked by Cloudflare.'''
    jobs = []
    p_name = portal["name"]
    p_sector = portal["sector"]
    domain = urlparse(portal["url"]).netloc
    if not domain:
        domain = portal["url"].replace("https://", "").replace("http://", "").split("/")[0]
        
    import logging
    log = logging.getLogger("ddgs")
    
    # SEARCH 1: Finance Roles
    query_fin = f"site:{domain} finance OR accountant OR audit"
    if include_entry:
        query_fin += " (graduate OR entry OR trainee OR assistant)"
        
    # SEARCH 2: Generic Roles
    query_gen = f"site:{domain} admin OR HR OR manager OR IT OR project"
    
    import time, random
    from ddgs import DDGS
    
    try:
        # Finance Sweep
        log.info(f"DDGS Finance sweep for {domain}: {query_fin}")
        results_fin = DDGS().text(query_fin, max_results=8)
        for r in results_fin:
            href = r.get("href", portal["url"])
            if domain not in href: continue
            jobs.append({
                "title": r.get("title", f"Finance Role at {p_name}").replace(" - Civil Service Jobs - GOV.UK", ""),
                "company": p_name,
                "location": "United Kingdom",
                "salary": "Competitive",
                "source_url": href,
                "html_content": f"<html><body><h1>{r.get('title')}</h1><p>{r.get('body')}</p></body></html>",
                "metadata": {"company_name": p_name, "is_generic": False}
            })
            
        time.sleep(random.uniform(1.0, 3.0))
        
        # Generic Sweep
        log.info(f"DDGS Generic sweep for {domain}: {query_gen}")
        results_gen = DDGS().text(query_gen, max_results=8)
        for r in results_gen:
            href = r.get("href", portal["url"])
            if domain not in href: continue
            # Avoid duplicates if DDG returns same link
            if any(j["source_url"] == href for j in jobs): continue
            
            jobs.append({
                "title": r.get("title", f"Role at {p_name}").replace(" - Civil Service Jobs - GOV.UK", ""),
                "company": p_name,
                "location": "United Kingdom",
                "salary": "Competitive",
                "source_url": href,
                "html_content": f"<html><body><h1>{r.get('title')}</h1><p>{r.get('body')}</p></body></html>",
                "metadata": {"company_name": p_name, "is_generic": True}
            })
            
    except Exception as e:
        log.error(f"DDGS failed for {domain}: {e}")
        
    return jobs

# (We keep the old mock function around just in case, but we won't use it unconditionally)
def generate_mock_public_jobs(portal: dict, include_entry: bool) -> list[dict]:

    """Generates realistic job listings when live bot-protected portals reject automated requests."""
    jobs = []
    p_name = portal["name"]
    p_sector = portal["sector"]
    
    # Generate 5-10 realistic jobs per portal
    import random
    random.seed(hash(p_name) + int(time.time()))
    count = random.randint(5, 10)
    
    for i in range(count):
        is_entry = include_entry and random.random() < 0.3
        
        if is_entry:
            title = random.choice(_ENTRY_LEVEL_STANDALONE)
            salary = random.choice(["£25,000 - £30,000", "Band 5 (NHS)", "EO Grade (£27k)", "£28,500"])
        else:
            title = random.choice(_PUBLIC_SECTOR_ROLES)
            if p_sector == "NHS":
                salary = random.choice(["Band 6", "Band 7", "Band 8a (£50,952 - £57,349)", "Band 8b"])
            elif p_sector == "Civil Service":
                salary = random.choice(["HEO (£34,000)", "SEO (£40,000)", "Grade 7 (£55,000)", "Grade 6 (£65,000)"])
            else:
                salary = random.choice(["£40,000 - £45,000", "£50,000 - £60,000", "Competitive"])
        
        jobs.append({
            "title": title,
            "company": f"Example {p_sector} Organization",
            "location": random.choice(["London", "Manchester", "Leeds", "Edinburgh", "Cardiff", "Belfast", "National / Hybrid"]),
            "salary": salary,
            "source_url": portal["url"] + f"?jobId={random.randint(10000, 99999)}",
            "html_content": f"<html><body><h1>{title}</h1><p>Sector: {p_sector}</p><p>We are seeking a highly motivated professional to join our team.</p><ul><li>Public Sector Pension</li><li>Flexible working</li></ul></body></html>"
        })
    return jobs

class JobSearchAgent(BaseAgent):
    def __init__(self, broker=None):
        super().__init__("job_search_agent", "job_search_queue")

    def process_message(self, message: dict):
        logger.info(f"[{self.name}] Processing portal search: {message.get('payload', {}).get('portal', {}).get('name')}")
        
        payload = message.get("payload", {})
        portal = payload.get("portal")
        if not portal:
            return
            
        workflow_id = message.get("correlation_id") or payload.get("workflow_id")
        params = payload.get("params", {})
        include_entry_level = payload.get("include_entry_level", True)
        
        # 1. Attempt Live Connection
        live_failed = False
        try:
            logger.info(f"[{self.name}] Attempting live connection to {portal['url']} ...")
            resp = requests.get(portal["url"], timeout=5)
            if resp.status_code != 200:
                live_failed = True
        except Exception as e:
            logger.warning(f"[{self.name}] Connection to {portal['name']} timed out/failed: {e}")
            live_failed = True
            
        # 2. Extract Jobs (Simulated if protected)
        raw_jobs = []
        if live_failed or True:
            logger.info(f"[{self.name}] Falling back to DDGS to extract REAL URLs for {portal['name']} (anti-bot protection active).")
            raw_jobs = get_real_jobs_from_ddgs(portal, include_entry_level)
            if not raw_jobs:
                search_url = portal.get("url", portal.get("search_url", ""))
                logger.info(f"[{self.name}] DDGS returned 0 results for {portal['name']}. Adding portal search link as fallback.")
                raw_jobs = [{
                    "title": f"Browse {portal['name']} — Search Finance/Accounting Roles",
                    "company": portal["name"],
                    "location": "United Kingdom",
                    "salary": "See website",
                    "source_url": search_url,
                    "html_content": "<html><body><h1>No specific roles indexed. Visit portal directly.</h1></body></html>",
                    "metadata": {"company_name": portal["name"], "is_generic": False, "is_portal_link": True}
                }]
            
        logger.info(f"[{self.name}] Found {len(raw_jobs)} roles from {portal['name']}.")
        
        # 3. Notify Master with raw_jobs
        self.broker.publish(queue_name="master_queue", source=self.name, target="master", msg_type="task_response", correlation_id=workflow_id, payload={
            "type": "stage_2_complete",
            "workflow_id": workflow_id,
            "portal": portal,
            "raw_jobs": raw_jobs,
            "count": len(raw_jobs)
        })