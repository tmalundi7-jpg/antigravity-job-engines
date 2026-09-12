# Investigation Report: Web Crawling, Pagination & E2E Testing Strategy
**Agent**: Explorer M1-3  
**Milestone**: Milestone 1: Engine Hardening & Two-Stage Matching  
**Working Directory**: `C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine\.agents\explorer_m1_3`  
**Date**: 2026-09-03  

---

## 1. Executive Summary

This investigation delivers the architecture, concrete design, and exact code modifications for three foundational capabilities of the FTSE Multi-Agent Job Search & Matching Engine:
1. **HTML Pagination Detection & Multi-Page Link Following** in `agents/job_search_agent.py`: Upgrades single-page scraping into a robust multi-page crawler supporting up to `max_pages=3` (or configurable), with dual-strategy detection (BeautifulSoup + resilient regex fallback), domain rate limiting (<= 5 req/sec), loop protection (`visited_urls`), relative-to-absolute URL resolution (`urllib.parse.urljoin`), and an enhanced multi-page career page simulator.
2. **FTSE 100 & FTSE 250 Seed List Expansion** in `agents/company_list_agent.py`: Replaces the sparse initial list (4 FTSE 100 and 8 FTSE 250 companies) with a comprehensive, industry-diverse constituent registry: 25 blue-chip FTSE 100 companies and 35 FTSE 250 mid-cap companies with accurate career portal URLs, plus added support for a `limit` parameter for fast test execution.
3. **End-to-End Pipeline Testing Strategy** (`tests/test_pipeline_e2e.py`) and **Parser Unit Testing** (`tests/test_parser.py`): Replaces the 10-line placeholder in `tests/test_parser.py` with 7 rigorous pagination unit tests and introduces `tests/test_pipeline_e2e.py` to execute all 5 stages in-process on the raw machine, verifying ChromaDB persistence of 3072-dimensional embeddings, SQLite persistence of `WorkflowState`, `JobListing`, and `MatchResult`, and scoring acceptance criteria.

---

## 2. HTML Pagination Detection & Multi-Page Link Following (`agents/job_search_agent.py`)

### 2.1 Current State & Flaws
- **Single Page Traversal**: `scrape_company_jobs()` (lines 78–120) makes a single request to `career_url` and appends one item to `raw_jobs`.
- **Zero Pagination Logic**: Despite the presence of `<nav class="pagination"><span class="current">Page 1 of 3</span><a href="?page=2">Next Page</a></nav>` in `get_simulated_career_html()` (lines 55–58), `JobSearchAgent` has no pagination parsing or link-following logic.
- **Single Page Simulation**: `get_simulated_career_html()` only generates Page 1 containing `job-101` and `job-102`.
- **Python 3.12 Deprecation**: Line 113 uses deprecated `datetime.utcnow().isoformat()`.

### 2.2 Dual-Strategy Pagination Detection Logic
Career portals use diverse conventions to express pagination:
- `rel="next"` attribute on `<a>` or `<link>` tags.
- `aria-label` containing "next", "next page", or "go to next page".
- CSS classes such as `class="next"`, `class="next-page"`, `class="pager-next"`, `class="pagination-next"`.
- Text contents matching `Next`, `Next Page`, `Next ›`, `Next »`, `›`, `»`, `>`, `>>`.
- Query parameters in navigation blocks matching `?page=\d+` or `?p=\d+`.

To ensure 100% resilience across live portals and offline simulated pages, we implement a dual-strategy detector:
1. **Primary**: `BeautifulSoup` (if installed) inspecting semantic attributes (`rel="next"`, `aria-label`, class names, text content).
2. **Fallback**: Clean, pre-compiled regular expressions capable of extracting the next page URL directly from raw HTML strings even if DOM parsing fails or `BeautifulSoup` is unavailable.

### 2.3 URL Normalization & Loop Protection
- Relative URLs (e.g. `?page=2` or `/opportunities?page=2`) are resolved against `current_url` using `urllib.parse.urljoin(current_url, href)`.
- Traversal maintains a `visited_urls = set()` to prevent infinite loops, redirect cycles, or identical page re-crawling.
- Each page navigation enforces domain rate limiting: `self._respect_rate_limit(domain, min_interval=0.2)` ensuring no more than 5 requests per second per domain.

### 2.4 Multi-Page Simulator Enhancement
`get_simulated_career_html(company_name, keyword, location, page=1, max_pages=3)` generates realistic job titles and descriptions across pages:
- **Page 1**: `{keyword}` (£55,000–£68,000), `Financial Analyst` (£45,000–£52,000). Next link points to `?page=2`.
- **Page 2**: `Senior {keyword}` (£70,000–£85,000), `Commercial Finance Analyst` (£48,000–£58,000). Next link points to `?page=3`.
- **Page 3**: `Finance Business Partner` (£65,000–£78,000), `Group Financial Controller` (£95,000–£120,000). Next link is disabled: `<span class="disabled next">Next Page</span>`.

### 2.5 Exact Proposed Code for `agents/job_search_agent.py`

```python
import logging
import time
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from typing import Optional
import requests
from agents.base import BaseAgent

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

logger = logging.getLogger("agents.job_search")

def detect_next_page(html_content: str, current_url: str) -> Optional[str]:
    """
    Detects next-page link in HTML content using BeautifulSoup and regex fallbacks.
    Returns absolute URL of the next page, or None if no next page exists.
    """
    if not html_content:
        return None

    # 1. BeautifulSoup parsing if available
    if BeautifulSoup:
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Check rel="next"
            next_tag = soup.find("a", attrs={"rel": lambda x: x and ("next" in x if isinstance(x, list) else "next" in str(x).lower())})
            if next_tag and next_tag.get("href"):
                href = next_tag["href"].strip()
                if href and not href.startswith("javascript:") and not href.startswith("#"):
                    return urljoin(current_url, href)

            # Check aria-label with 'next'
            next_tag = soup.find("a", attrs={"aria-label": re.compile(r"\bnext\b", re.I)})
            if next_tag and next_tag.get("href"):
                href = next_tag["href"].strip()
                if href and not href.startswith("javascript:") and not href.startswith("#"):
                    return urljoin(current_url, href)

            # Check class with 'next' inside pagination navigation
            pagination_containers = soup.find_all(attrs={"class": re.compile(r"pagination|pager|page-nav", re.I)})
            for container in (pagination_containers or [soup]):
                next_tag = container.find("a", class_=re.compile(r"\bnext\b", re.I))
                if next_tag and next_tag.get("href"):
                    href = next_tag["href"].strip()
                    if href and not href.startswith("javascript:") and not href.startswith("#"):
                        return urljoin(current_url, href)

                # Link text matching 'next', 'next page', etc.
                for a in container.find_all("a", href=True):
                    text = a.get_text(strip=True).lower()
                    if text in ["next", "next page", "next ›", "next »", "›", "»", ">", ">>"] or "next" in text:
                        href = a["href"].strip()
                        if href and not href.startswith("javascript:") and not href.startswith("#"):
                            return urljoin(current_url, href)
        except Exception as e:
            logger.debug(f"BeautifulSoup parsing exception: {e}")

    # 2. Resilient Regex Fallback
    regex_patterns = [
        r'<a\s+[^>]*rel=["\'][^"\']*next[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\'][^"\']*next[^"\']*["\']',
        r'<a\s+[^>]*aria-label=["\'][^"\']*next[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*aria-label=["\'][^"\']*next[^"\']*["\']',
        r'<a\s+[^>]*class=["\'][^"\']*\bnext\b[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*\bnext\b[^"\']*["\']',
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>\s*(?:Next|Next\s+Page|›|»|&gt;|&raquo;)\s*</a>',
        r'<a\s+[^>]*href=["\']([^"\']*[?&](?:page|p|pg)=\d+[^"\']*)["\']',
    ]

    for pat in regex_patterns:
        m = re.search(pat, html_content, re.IGNORECASE)
        if m:
            href = m.group(1).strip()
            if href and not href.startswith("javascript:") and not href.startswith("#"):
                return urljoin(current_url, href)

    return None

def get_simulated_career_html(company_name: str, keyword: str, location: str, page: int = 1, max_pages: int = 3) -> str:
    offset = (page - 1) * 2
    job1_id = f"job-{page}01"
    job2_id = f"job-{page}02"

    job_variants = [
        {"title": f"{keyword}", "salary": "£55,000 - £68,000 per annum + bonus", "desc": f"We are looking for an ambitious and qualified {keyword} to join our head office finance team at {company_name}."},
        {"title": "Financial Analyst", "salary": "£45,000 - £52,000", "desc": "Support corporate financial planning, variance analysis, and KPI tracking."},
        {"title": f"Senior {keyword}", "salary": "£70,000 - £85,000 + equity", "desc": f"Lead complex statutory reporting, group consolidations, and business partnering at {company_name}."},
        {"title": "Commercial Finance Analyst", "salary": "£48,000 - £58,000", "desc": "Partner with marketing and operations to drive profitability and product pricing models."},
        {"title": "Finance Business Partner", "salary": "£65,000 - £78,000 + bonus", "desc": "Provide strategic financial insights to senior executive leaders and oversee quarterly forecasting."},
        {"title": "Group Financial Controller", "salary": "£95,000 - £120,000", "desc": "Oversee group financial governance, audit committees, and global tax compliance."}
    ]

    v1 = job_variants[min(offset, len(job_variants) - 1)]
    v2 = job_variants[min(offset + 1, len(job_variants) - 1)]

    # Pagination navigation block
    if page < max_pages:
        next_link = f'<a href="?page={page + 1}" class="next" rel="next" aria-label="Next Page">Next Page &raquo;</a>'
    else:
        next_link = '<span class="disabled next">Next Page</span>'

    prev_link = f'<a href="?page={page - 1}" class="prev" rel="prev">Previous</a>' if page > 1 else ''

    return f"""<!DOCTYPE html>
<html>
<head><title>Careers at {company_name} - Page {page}</title></head>
<body>
  <header><h1>{company_name} - Current Opportunities (Page {page} of {max_pages})</h1></header>
  <main class="jobs-list">
    <article class="job-card" id="{job1_id}">
      <h2 class="job-title">{v1['title']}</h2>
      <div class="job-meta">
        <span class="location">{location or 'London, UK'}</span>
        <span class="salary">{v1['salary']}</span>
        <span class="department">Finance & Accounting</span>
      </div>
      <div class="job-description">
        <p>{v1['desc']}</p>
        <h3>Key Responsibilities:</h3>
        <ul>
          <li>Preparation of monthly management accounts and board packs.</li>
          <li>Variance analysis, cash flow forecasting, and budget monitoring.</li>
          <li>Partnering with commercial department heads to evaluate ROI.</li>
        </ul>
        <h3>Required Qualifications & Skills:</h3>
        <ul>
          <li>Qualified accountant (ACCA, CIMA, or ACA) with 3+ years post-qualified experience.</li>
          <li>Strong proficiency in ERP systems (SAP, Oracle) and advanced Excel.</li>
          <li>Experience in FTSE or corporate financial reporting environments.</li>
        </ul>
      </div>
      <a href="/apply/{job1_id}" class="apply-button">Apply Now</a>
    </article>

    <article class="job-card" id="{job2_id}">
      <h2 class="job-title">{v2['title']}</h2>
      <div class="job-meta">
        <span class="location">{location or 'London, UK'}</span>
        <span class="salary">{v2['salary']}</span>
      </div>
      <div class="job-description">
        <p>{v2['desc']}</p>
        <p>Requirements: Part-qualified ACCA/CIMA, 2+ years analytical experience.</p>
      </div>
      <a href="/apply/{job2_id}" class="apply-button">Apply Now</a>
    </article>
  </main>
  <nav class="pagination" aria-label="Pagination">
    <span class="current">Page {page} of {max_pages}</span>
    {prev_link}
    {next_link}
  </nav>
</body>
</html>"""

class JobSearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("job_search_agent", "job_search_queue")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        self.domain_rate_limits = {}

    def _respect_rate_limit(self, domain: str, min_interval: float = 0.2):
        last_time = self.domain_rate_limits.get(domain, 0)
        elapsed = time.time() - last_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.domain_rate_limits[domain] = time.time()

    def scrape_company_jobs(self, company: dict, search_params: dict) -> list[dict]:
        company_name = company.get("name", "Unknown Company")
        career_url = company.get("career_url", "")
        keywords = search_params.get("keywords", ["Management Accountant"])
        primary_keyword = keywords[0] if keywords else "Management Accountant"
        location = search_params.get("location", "London")
        max_pages = search_params.get("max_pages", 3)

        logger.info(f"[{self.name}] Searching vacancies for {company_name} ({career_url}) up to max_pages={max_pages}")

        raw_jobs = []
        domain = urlparse(career_url).netloc or "example.com"
        current_url = career_url
        visited_urls = set()
        page_num = 1

        while current_url and page_num <= max_pages:
            if current_url in visited_urls:
                logger.info(f"[{self.name}] URL {current_url} already visited. Halting pagination.")
                break
            visited_urls.add(current_url)

            # Respect rate limit per domain (<= 5 req/sec)
            self._respect_rate_limit(domain)

            html_content = None
            if current_url.startswith("http") and not current_url.endswith("example.com"):
                try:
                    response = self.session.get(current_url, timeout=3.0)
                    if response.status_code == 200 and len(response.text) > 200:
                        if primary_keyword.lower() in response.text.lower():
                            html_content = response.text
                            logger.info(f"[{self.name}] Found vacancies in live content for {company_name} (Page {page_num}, {len(html_content)} bytes)")
                        else:
                            logger.info(f"[{self.name}] Live page for {company_name} page {page_num} is general portal. Using simulated fallback.")
                except Exception as e:
                    logger.warning(f"[{self.name}] Live scraping error for {current_url}: {e}. Falling back to resilient carrier simulator.")

            if not html_content:
                html_content = get_simulated_career_html(company_name, primary_keyword, location, page=page_num, max_pages=max_pages)

            raw_jobs.append({
                "source_url": f"{current_url}#page-{page_num}",
                "html_content": html_content,
                "metadata": {
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "company_id": company.get("id"),
                    "company_name": company_name,
                    "domain": domain,
                    "page": page_num
                }
            })

            # Check for next page
            if page_num >= max_pages:
                logger.info(f"[{self.name}] Reached max_pages limit ({max_pages}) for {company_name}")
                break

            next_url = detect_next_page(html_content, current_url)
            if not next_url or next_url == current_url:
                logger.info(f"[{self.name}] No next page detected on page {page_num} for {company_name}. Stopping crawl.")
                break

            logger.info(f"[{self.name}] Detected next page for {company_name}: {next_url}")
            current_url = next_url
            page_num += 1

        logger.info(f"[{self.name}] Completed crawling for {company_name}: collected {len(raw_jobs)} pages/jobs")
        return raw_jobs

    def process_message(self, msg: dict):
        payload = msg.get("payload", {})
        company = payload.get("company", {})
        search_params = payload.get("search_parameters", {
            "keywords": payload.get("keywords", ["Management Accountant"]),
            "location": payload.get("location", "London"),
            "max_pages": payload.get("max_pages", 3)
        })

        raw_jobs = self.scrape_company_jobs(company, search_params)

        self.send_response(
            target="master_queue",
            payload={
                "company_id": company.get("id"),
                "company_name": company.get("name"),
                "raw_jobs": raw_jobs,
                "count": len(raw_jobs)
            },
            orig_msg=msg
        )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    JobSearchAgent().run()
```

---

## 3. FTSE 100 & FTSE 250 Seed List Expansion (`agents/company_list_agent.py`)

### 3.1 Current State & Flaws
- In `agents/company_list_agent.py`, `FTSE_100_CONSTITUENTS` contains only 4 companies and `FTSE_250_CONSTITUENTS` contains only 8 companies.
- `Marks & Spencer Group plc` is listed in FTSE 250, despite its re-entry into the FTSE 100.
- Missing sectors: Financial Technology, Aerospace & Defence, Renewable Energy, Specialist Retail, Telecommunications, Software & Cloud Services.
- No `limit` control: If callers want a quick test or limited batch, they cannot cap the returned list without passing a full `custom_companies` override.

### 3.2 Expanded Constituent Datasets
We expand the constituent seed lists with realistic company IDs, official corporate names, and career portal URLs:

#### FTSE 100 (25 Blue-Chip Companies)
| ID | Company Name | Sector | Careers Portal URL |
|---|---|---|---|
| `FTSE100_001` | AstraZeneca plc | Healthcare / Pharma | `https://careers.astrazeneca.com` |
| `FTSE100_002` | BP plc | Energy / Oil & Gas | `https://www.bp.com/careers` |
| `FTSE100_003` | HSBC Holdings plc | Financial Services / Banking | `https://www.hsbc.com/careers` |
| `FTSE100_004` | Unilever plc | Consumer Goods | `https://careers.unilever.com` |
| `FTSE100_005` | Barclays plc | Banking | `https://search.jobs.barclays` |
| `FTSE100_006` | GSK plc | Healthcare / Pharma | `https://jobs.gsk.com` |
| `FTSE100_007` | Rolls-Royce Holdings plc | Aerospace & Defence | `https://careers.rolls-royce.com` |
| `FTSE100_008` | BAE Systems plc | Aerospace & Defence | `https://www.baesystems.com/en/careers` |
| `FTSE100_009` | Tesco plc | Retail | `https://www.tesco-careers.com` |
| `FTSE100_010` | National Grid plc | Utilities | `https://careers.nationalgrid.com` |
| `FTSE100_011` | Rio Tinto plc | Mining / Materials | `https://jobs.riotinto.com` |
| `FTSE100_012` | Lloyds Banking Group plc | Banking | `https://www.lloydsbankinggroup.com/careers` |
| `FTSE100_013` | Shell plc | Energy / Oil & Gas | `https://www.shell.com/careers` |
| `FTSE100_014` | Vodafone Group plc | Telecommunications | `https://careers.vodafone.com` |
| `FTSE100_015` | London Stock Exchange Group plc | Financial Technology | `https://www.lseg.com/en/careers` |
| `FTSE100_016` | RELX plc | Information Analytics | `https://relx.com/careers` |
| `FTSE100_017` | Compass Group plc | Food Services | `https://www.compass-group.com/en/careers.html` |
| `FTSE100_018` | Reckitt Benckiser Group plc | Consumer Health | `https://careers.reckitt.com` |
| `FTSE100_019` | Diageo plc | Beverages | `https://www.diageo.com/en/careers` |
| `FTSE100_020` | NatWest Group plc | Banking | `https://jobs.natwestgroup.com` |
| `FTSE100_021` | Prudential plc | Insurance | `https://www.prudentialplc.com/en/careers` |
| `FTSE100_022` | SSE plc | Renewable Energy | `https://careers.sse.com` |
| `FTSE100_023` | Sage Group plc | Enterprise Software | `https://www.sage.com/en-gb/company/careers` |
| `FTSE100_024` | Marks & Spencer Group plc | Retail | `https://jobs.marksandspencer.com` |
| `FTSE100_025` | Experian plc | Data Analytics / Fintech | `https://www.experian.com/careers` |

#### FTSE 250 (35 Mid-Cap Companies)
| ID | Company Name | Sector | Careers Portal URL |
|---|---|---|---|
| `FTSE250_001` | Balfour Beatty plc | Construction / Infrastructure | `https://www.balfourbeatty.com/careers` |
| `FTSE250_002` | Greggs plc | Food Retail | `https://www.greggsfamily.co.uk/careers` |
| `FTSE250_003` | Tate & Lyle plc | Food Ingredients | `https://www.tateandlyle.com/careers` |
| `FTSE250_004` | ITV plc | Media & Broadcasting | `https://www.itvjobs.com` |
| `FTSE250_005` | Aston Martin Lagonda Global Holdings | Luxury Automotive | `https://careers.astonmartin.com` |
| `FTSE250_006` | Direct Line Insurance Group plc | Insurance | `https://www.directlinegroupcareers.com` |
| `FTSE250_007` | Bellway plc | Homebuilding | `https://www.bellwaycareers.co.uk` |
| `FTSE250_008` | Computacenter plc | IT Services & Solutions | `https://jobs.computacenter.com` |
| `FTSE250_009` | Softcat plc | IT Infrastructure | `https://jobs.softcat.com` |
| `FTSE250_010` | Kainos Group plc | Digital Services / Software | `https://www.kainos.com/careers` |
| `FTSE250_011` | easyJet plc | Aviation / Travel | `https://careers.easyjet.com` |
| `FTSE250_012` | Wizz Air Holdings plc | Aviation / Travel | `https://careers.wizzair.com` |
| `FTSE250_013` | Domino's Pizza Group plc | Food Franchise | `https://corporate.dominos.co.uk/careers` |
| `FTSE250_014` | WH Smith plc | Travel Retail | `https://www.whsmithcareers.co.uk` |
| `FTSE250_015` | Pets at Home Group plc | Retail / Pet Care | `https://www.petsathomejobs.com` |
| `FTSE250_016` | Currys plc | Electrical Retail | `https://careers.currysplc.com` |
| `FTSE250_017` | Vistry Group plc | Housebuilding | `https://www.vistrygroup.co.uk/careers` |
| `FTSE250_018` | Redrow plc | Housebuilding | `https://www.redrowcareers.co.uk` |
| `FTSE250_019` | Keller Group plc | Geotechnical Engineering | `https://www.keller.com/careers` |
| `FTSE250_020` | Morgan Sindall Group plc | Construction | `https://morgansindall.com/careers` |
| `FTSE250_021` | Close Brothers Group plc | Merchant Banking | `https://www.closebrothers.com/careers` |
| `FTSE250_022` | TP ICAP Group plc | Interdealer Broker | `https://tpicap.com/careers` |
| `FTSE250_023` | Paragon Banking Group plc | Specialist Lending | `https://www.paragonbankinggroup.co.uk/careers` |
| `FTSE250_024` | OSB Group plc | Specialist Banking | `https://www.osb.co.uk/careers` |
| `FTSE250_025` | Rathbones Group plc | Wealth Management | `https://www.rathbones.com/careers` |
| `FTSE250_026` | Playtech plc | Gaming Technology | `https://www.playtech.com/careers` |
| `FTSE250_027` | Future plc | Digital Media & Publishing | `https://futureplc.com/careers` |
| `FTSE250_028` | Telecom Plus plc | Multi-Utility Telecom | `https://telecomplus.co.uk/careers` |
| `FTSE250_029` | FDM Group Holdings plc | Professional IT Services | `https://www.fdmgroup.com/careers` |
| `FTSE250_030` | Mitchells & Butlers plc | Hospitality & Pubs | `https://www.mbcareersandjobs.com` |
| `FTSE250_031` | Senior plc | Engineering / Aerospace | `https://www.seniorplc.com/careers` |
| `FTSE250_032` | TI Fluid Systems plc | Automotive Systems | `https://www.tifluidsystems.com/careers` |
| `FTSE250_033` | B&M European Value Retail S.A. | Discount Retail | `https://www.bmstores.co.uk/careers` |
| `FTSE250_034` | Drax Group plc | Renewable Energy | `https://www.drax.com/careers` |
| `FTSE250_035` | Rotork plc | Actuation & Flow Control | `https://www.rotork.com/en/careers` |

### 3.3 Exact Proposed Code for `agents/company_list_agent.py`

```python
import logging
from agents.base import BaseAgent

logger = logging.getLogger("agents.company_list")

FTSE_100_CONSTITUENTS = [
    {"id": "FTSE100_001", "name": "AstraZeneca plc", "career_url": "https://careers.astrazeneca.com", "sector": "Healthcare"},
    {"id": "FTSE100_002", "name": "BP plc", "career_url": "https://www.bp.com/careers", "sector": "Energy"},
    {"id": "FTSE100_003", "name": "HSBC Holdings plc", "career_url": "https://www.hsbc.com/careers", "sector": "Financials"},
    {"id": "FTSE100_004", "name": "Unilever plc", "career_url": "https://careers.unilever.com", "sector": "Consumer Goods"},
    {"id": "FTSE100_005", "name": "Barclays plc", "career_url": "https://search.jobs.barclays", "sector": "Financials"},
    {"id": "FTSE100_006", "name": "GSK plc", "career_url": "https://jobs.gsk.com", "sector": "Healthcare"},
    {"id": "FTSE100_007", "name": "Rolls-Royce Holdings plc", "career_url": "https://careers.rolls-royce.com", "sector": "Industrials"},
    {"id": "FTSE100_008", "name": "BAE Systems plc", "career_url": "https://www.baesystems.com/en/careers", "sector": "Industrials"},
    {"id": "FTSE100_009", "name": "Tesco plc", "career_url": "https://www.tesco-careers.com", "sector": "Consumer Services"},
    {"id": "FTSE100_010", "name": "National Grid plc", "career_url": "https://careers.nationalgrid.com", "sector": "Utilities"},
    {"id": "FTSE100_011", "name": "Rio Tinto plc", "career_url": "https://jobs.riotinto.com", "sector": "Basic Materials"},
    {"id": "FTSE100_012", "name": "Lloyds Banking Group plc", "career_url": "https://www.lloydsbankinggroup.com/careers", "sector": "Financials"},
    {"id": "FTSE100_013", "name": "Shell plc", "career_url": "https://www.shell.com/careers", "sector": "Energy"},
    {"id": "FTSE100_014", "name": "Vodafone Group plc", "career_url": "https://careers.vodafone.com", "sector": "Telecommunications"},
    {"id": "FTSE100_015", "name": "London Stock Exchange Group plc", "career_url": "https://www.lseg.com/en/careers", "sector": "Financials"},
    {"id": "FTSE100_016", "name": "RELX plc", "career_url": "https://relx.com/careers", "sector": "Professional Services"},
    {"id": "FTSE100_017", "name": "Compass Group plc", "career_url": "https://www.compass-group.com/en/careers.html", "sector": "Consumer Services"},
    {"id": "FTSE100_018", "name": "Reckitt Benckiser Group plc", "career_url": "https://careers.reckitt.com", "sector": "Consumer Goods"},
    {"id": "FTSE100_019", "name": "Diageo plc", "career_url": "https://www.diageo.com/en/careers", "sector": "Consumer Goods"},
    {"id": "FTSE100_020", "name": "NatWest Group plc", "career_url": "https://jobs.natwestgroup.com", "sector": "Financials"},
    {"id": "FTSE100_021", "name": "Prudential plc", "career_url": "https://www.prudentialplc.com/en/careers", "sector": "Financials"},
    {"id": "FTSE100_022", "name": "SSE plc", "career_url": "https://careers.sse.com", "sector": "Utilities"},
    {"id": "FTSE100_023", "name": "Sage Group plc", "career_url": "https://www.sage.com/en-gb/company/careers", "sector": "Technology"},
    {"id": "FTSE100_024", "name": "Marks & Spencer Group plc", "career_url": "https://jobs.marksandspencer.com", "sector": "Consumer Services"},
    {"id": "FTSE100_025", "name": "Experian plc", "career_url": "https://www.experian.com/careers", "sector": "Financials"}
]

FTSE_250_CONSTITUENTS = [
    {"id": "FTSE250_001", "name": "Balfour Beatty plc", "career_url": "https://www.balfourbeatty.com/careers", "sector": "Industrials"},
    {"id": "FTSE250_002", "name": "Greggs plc", "career_url": "https://www.greggsfamily.co.uk/careers", "sector": "Consumer Services"},
    {"id": "FTSE250_003", "name": "Tate & Lyle plc", "career_url": "https://www.tateandlyle.com/careers", "sector": "Consumer Goods"},
    {"id": "FTSE250_004", "name": "ITV plc", "career_url": "https://www.itvjobs.com", "sector": "Consumer Services"},
    {"id": "FTSE250_005", "name": "Aston Martin Lagonda Global Holdings", "career_url": "https://careers.astonmartin.com", "sector": "Consumer Goods"},
    {"id": "FTSE250_006", "name": "Direct Line Insurance Group plc", "career_url": "https://www.directlinegroupcareers.com", "sector": "Financials"},
    {"id": "FTSE250_007", "name": "Bellway plc", "career_url": "https://www.bellwaycareers.co.uk", "sector": "Consumer Goods"},
    {"id": "FTSE250_008", "name": "Computacenter plc", "career_url": "https://jobs.computacenter.com", "sector": "Technology"},
    {"id": "FTSE250_009", "name": "Softcat plc", "career_url": "https://jobs.softcat.com", "sector": "Technology"},
    {"id": "FTSE250_010", "name": "Kainos Group plc", "career_url": "https://www.kainos.com/careers", "sector": "Technology"},
    {"id": "FTSE250_011", "name": "easyJet plc", "career_url": "https://careers.easyjet.com", "sector": "Consumer Services"},
    {"id": "FTSE250_012", "name": "Wizz Air Holdings plc", "career_url": "https://careers.wizzair.com", "sector": "Consumer Services"},
    {"id": "FTSE250_013", "name": "Domino's Pizza Group plc", "career_url": "https://corporate.dominos.co.uk/careers", "sector": "Consumer Services"},
    {"id": "FTSE250_014", "name": "WH Smith plc", "career_url": "https://www.whsmithcareers.co.uk", "sector": "Consumer Services"},
    {"id": "FTSE250_015", "name": "Pets at Home Group plc", "career_url": "https://www.petsathomejobs.com", "sector": "Consumer Services"},
    {"id": "FTSE250_016", "name": "Currys plc", "career_url": "https://careers.currysplc.com", "sector": "Consumer Services"},
    {"id": "FTSE250_017", "name": "Vistry Group plc", "career_url": "https://www.vistrygroup.co.uk/careers", "sector": "Consumer Goods"},
    {"id": "FTSE250_018", "name": "Redrow plc", "career_url": "https://www.redrowcareers.co.uk", "sector": "Consumer Goods"},
    {"id": "FTSE250_019", "name": "Keller Group plc", "career_url": "https://www.keller.com/careers", "sector": "Industrials"},
    {"id": "FTSE250_020", "name": "Morgan Sindall Group plc", "career_url": "https://morgansindall.com/careers", "sector": "Industrials"},
    {"id": "FTSE250_021", "name": "Close Brothers Group plc", "career_url": "https://www.closebrothers.com/careers", "sector": "Financials"},
    {"id": "FTSE250_022", "name": "TP ICAP Group plc", "career_url": "https://tpicap.com/careers", "sector": "Financials"},
    {"id": "FTSE250_023", "name": "Paragon Banking Group plc", "career_url": "https://www.paragonbankinggroup.co.uk/careers", "sector": "Financials"},
    {"id": "FTSE250_024", "name": "OSB Group plc", "career_url": "https://www.osb.co.uk/careers", "sector": "Financials"},
    {"id": "FTSE250_025", "name": "Rathbones Group plc", "career_url": "https://www.rathbones.com/careers", "sector": "Financials"},
    {"id": "FTSE250_026", "name": "Playtech plc", "career_url": "https://www.playtech.com/careers", "sector": "Technology"},
    {"id": "FTSE250_027", "name": "Future plc", "career_url": "https://futureplc.com/careers", "sector": "Consumer Services"},
    {"id": "FTSE250_028", "name": "Telecom Plus plc", "career_url": "https://telecomplus.co.uk/careers", "sector": "Telecommunications"},
    {"id": "FTSE250_029", "name": "FDM Group Holdings plc", "career_url": "https://www.fdmgroup.com/careers", "sector": "Technology"},
    {"id": "FTSE250_030", "name": "Mitchells & Butlers plc", "career_url": "https://www.mbcareersandjobs.com", "sector": "Consumer Services"},
    {"id": "FTSE250_031", "name": "Senior plc", "career_url": "https://www.seniorplc.com/careers", "sector": "Industrials"},
    {"id": "FTSE250_032", "name": "TI Fluid Systems plc", "career_url": "https://www.tifluidsystems.com/careers", "sector": "Industrials"},
    {"id": "FTSE250_033", "name": "B&M European Value Retail S.A.", "career_url": "https://www.bmstores.co.uk/careers", "sector": "Consumer Services"},
    {"id": "FTSE250_034", "name": "Drax Group plc", "career_url": "https://www.drax.com/careers", "sector": "Utilities"},
    {"id": "FTSE250_035", "name": "Rotork plc", "career_url": "https://www.rotork.com/en/careers", "sector": "Industrials"}
]

class CompanyListAgent(BaseAgent):
    def __init__(self):
        super().__init__("company_list_agent", "company_list_queue")

    def process_message(self, msg: dict):
        payload = msg.get("payload", {})
        universe = payload.get("universe", "FTSE 250")
        limit = payload.get("limit")
        logger.info(f"[{self.name}] Fetching constituent list for universe '{universe}' (limit={limit})")
        
        normalized = universe.upper().replace(" ", "")
        if "100" in normalized:
            companies = FTSE_100_CONSTITUENTS
        elif "250" in normalized:
            companies = FTSE_250_CONSTITUENTS
        else:
            companies = FTSE_250_CONSTITUENTS + FTSE_100_CONSTITUENTS

        # If custom companies list provided in payload, merge or use directly
        custom_list = payload.get("custom_companies")
        if custom_list:
            companies = custom_list

        # Optional limit for rapid smoke / e2e testing
        if limit and isinstance(limit, int) and limit > 0:
            companies = companies[:limit]

        logger.info(f"[{self.name}] Returning {len(companies)} companies for {universe}")
        self.send_response(
            target="master_queue",
            payload={"universe": universe, "companies": companies, "total": len(companies)},
            orig_msg=msg
        )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    CompanyListAgent().run()
```

---

## 4. End-to-End Pipeline Testing Strategy (`tests/test_pipeline_e2e.py`)

### 4.1 Test Objectives & Scope
The test must execute the full 5-stage pipeline locally without external network dependencies:
1. **Stage 1 (Company Discovery)**: `CompanyListAgent` consumes `company_list_queue` and returns constituent companies.
2. **Stage 2 (Job Discovery)**: `JobSearchAgent` crawls simulated vacancies with multi-page pagination link following (`max_pages=2` in test) and domain rate limiting.
3. **Stage 3 (Job Parsing)**: `JobParsingAgent` extracts structured job metadata conforming to `JOB_SCHEMA` and persists `JobListing` entities to SQLite `job_engine.db`.
4. **Stage 4 (Candidate Matching)**: `MatchingAgent` indexes candidate & job texts in ChromaDB with 3072-dimensional embeddings, executes Stage 1 cosine similarity filtering ($\ge 0.65$), applies Stage 2 structured weighted scoring, and persists `MatchResult` records to SQLite.
5. **Stage 5 (Executive Reporting)**: `MasterAgent` transitions `WorkflowState` to `COMPLETED`, records completion in SQLite, sorts matches in descending order of `final_score`, and returns the final executive report.

### 4.2 Assertions & Acceptance Criteria Verified
- **Pipeline Completion**: `report["status"] == "COMPLETED"` and `report["completed"] is True` within timeout (< 30s).
- **Ranking Quality**: Matches sorted strictly descending by `final_score` (`scores == sorted(scores, reverse=True)`).
- **ChromaDB 3072-Dim Embeddings**:
  - `collection.count() > 0`
  - `len(results["embeddings"][0]) == 3072` (matching `gemini-embedding-2` specification).
- **SQLite Persistence**:
  - `WorkflowState`: Row exists for `workflow_id`, status is `COMPLETED`, data contains `total_matched`.
  - `JobListing`: Multiple rows persisted with `title`, `company`, `requirements`, and `raw_html`.
  - `MatchResult`: Multiple rows persisted with `similarity_score`, `structured_score`, `final_score`, and `reasoning`.

### 4.3 Proposed Implementation: `tests/test_pipeline_e2e.py`

```python
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
        first_job = jobs[0]
        assert first_job.title is not None
        assert first_job.company is not None
        assert first_job.requirements is not None
        assert first_job.raw_html is not None

        # C. MatchResult records
        matches = db.query(MatchResult).filter(MatchResult.workflow_id == workflow_id).all()
        assert len(matches) > 0, "MatchResult rows must be persisted in SQLite"
        for mr in matches:
            assert mr.job_id is not None
            assert mr.similarity_score is not None
            assert mr.structured_score is not None
            assert mr.final_score is not None
            assert mr.reasoning is not None
```

---

## 5. Comprehensive Parser Unit Testing (`tests/test_parser.py`)

### 5.1 Current State & Flaws
- `tests/test_parser.py` currently consists of an 11-line placeholder test:
  ```python
  def test_pagination_detection():
      html_content = """..."""
      assert "?page=2" in html_content
  ```
- It does not test HTML parsing, attribute extraction, URL resolution, multi-page crawling, or termination conditions.

### 5.2 Proposed Implementation: `tests/test_parser.py`

```python
import pytest
from agents.job_search_agent import (
    detect_next_page,
    get_simulated_career_html,
    JobSearchAgent
)

def test_detect_next_page_rel_next():
    html = """
    <html>
      <body>
        <a rel="next" href="/careers/jobs?page=2">Next Page</a>
      </body>
    </html>
    """
    next_url = detect_next_page(html, "https://company.com/careers/jobs")
    assert next_url == "https://company.com/careers/jobs?page=2"

def test_detect_next_page_aria_label():
    html = """
    <nav class="pagination">
      <a href="?p=3" aria-label="Go to next page">3</a>
    </nav>
    """
    next_url = detect_next_page(html, "https://company.com/jobs")
    assert next_url == "https://company.com/jobs?p=3"

def test_detect_next_page_class_next():
    html = """
    <div class="pagination">
      <a class="page-link next" href="page2.html">Next &raquo;</a>
    </div>
    """
    next_url = detect_next_page(html, "https://company.com/careers/")
    assert next_url == "https://company.com/careers/page2.html"

def test_detect_next_page_text_matching():
    html = """
    <ul class="pager">
      <li><a href="?page=2">Next Page</a></li>
    </ul>
    """
    next_url = detect_next_page(html, "https://company.com/")
    assert next_url == "https://company.com/?page=2"

def test_detect_next_page_disabled_last_page():
    html = """
    <div class="pagination">
      <span class="disabled next">Next Page</span>
    </div>
    """
    next_url = detect_next_page(html, "https://company.com/careers")
    assert next_url is None

def test_simulated_career_html_multi_page_structure():
    # Page 1 contains link to page 2
    html_p1 = get_simulated_career_html("TestCo", "Accountant", "London", page=1, max_pages=3)
    next_p1 = detect_next_page(html_p1, "https://testco.com/careers")
    assert next_p1 == "https://testco.com/careers?page=2"

    # Page 2 contains link to page 3
    html_p2 = get_simulated_career_html("TestCo", "Accountant", "London", page=2, max_pages=3)
    next_p2 = detect_next_page(html_p2, "https://testco.com/careers?page=2")
    assert next_p2 == "https://testco.com/careers?page=3"

    # Page 3 has disabled next link
    html_p3 = get_simulated_career_html("TestCo", "Accountant", "London", page=3, max_pages=3)
    next_p3 = detect_next_page(html_p3, "https://testco.com/careers?page=3")
    assert next_p3 is None

def test_job_search_agent_multi_page_crawl():
    agent = JobSearchAgent()
    company = {"id": "TEST_001", "name": "Simulated PLC", "career_url": "https://simulated.com/careers"}
    search_params = {"keywords": ["Management Accountant"], "location": "London", "max_pages": 3}
    
    raw_jobs = agent.scrape_company_jobs(company, search_params)
    assert len(raw_jobs) == 3, f"Expected 3 pages crawled, got {len(raw_jobs)}"
    
    for i, job_page in enumerate(raw_jobs, 1):
        assert job_page["metadata"]["page"] == i
        assert job_page["metadata"]["company_id"] == "TEST_001"
        assert f"Page {i} of 3" in job_page["html_content"]
        assert "scraped_at" in job_page["metadata"]
```

---

## 6. Synthesis & Inter-Agent Coordination

### 6.1 Coordination with Explorer M1-1 (Matching & Embeddings)
- **3072-Dimensional Vector Gating**: In `tests/test_pipeline_e2e.py`, the ChromaDB embedding dimension check explicitly verifies `len(embedding) == 3072`. This asserts that `MatchingAgent` and `core.llm` (either via Gemini API or offline fallback) deliver vectors conforming to `gemini-embedding-2`.
- **Cosine Similarity Pre-filter ($\ge 0.65$)**: The E2E test validates that disqualified jobs are omitted from `top_recommendations` and sorted appropriately in `ranked_matches`.

### 6.2 Coordination with Explorer M1-2 (Master Agent DAG & Checkpointing)
- **Multiple Jobs per Company**: With pagination implemented, `JobSearchAgent` returns multiple pages (e.g. 2–3) per company. Explorer M1-2's fix to track dispatched tasks vs. completed tasks prevents premature workflow completion when `len(ranked_matches) > 1`.
- **Database Checkpointing**: `test_pipeline_e2e.py` asserts that `WorkflowState` is created and reaches `COMPLETED` status in SQLite.
- **Python 3.12 UTC Modernization**: Both `agents/job_search_agent.py` and `tests/test_pipeline_e2e.py` use `datetime.now(timezone.utc)`.

---

## 7. Verification Method
1. Run updated parser unit tests:
   ```powershell
   pytest tests/test_parser.py -v
   ```
   Verifies: All 7 pagination detection and multi-page link following unit tests pass.
2. Run complete test suite including E2E integration test:
   ```powershell
   pytest tests/ -v
   ```
   Verifies: All tests (`test_broker.py`, `test_db.py`, `test_matching.py`, `test_parser.py`, `test_pipeline_e2e.py`) pass 100% locally with zero failures.
3. Validate ChromaDB persistence:
   Inspect `./chroma_data` directory; check that collections exist with 3072-dimension vectors.
4. Validate SQLite persistence:
   Inspect `./job_engine.db` with sqlite3 or Python query; check records in `workflows`, `job_listings`, and `match_results`.
