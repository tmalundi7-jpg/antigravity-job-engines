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
