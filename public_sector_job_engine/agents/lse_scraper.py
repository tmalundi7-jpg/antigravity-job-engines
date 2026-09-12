"""
LSE Constituent Scraper
=======================
Uses Playwright (sync API) to scrape company constituent tables from the
London Stock Exchange website for any of the 16 supported FTSE indices.

Falls back gracefully — callers receive an empty list and a warning log,
then use the built-in static registry instead.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger("agents.lse_scraper")


class LSEScrapingError(RuntimeError):
    pass


# ── Index slug mapping ─────────────────────────────────────────────────────────
# Maps canonical display names (and common aliases) to the LSE URL slug used in:
#   https://www.londonstockexchange.com/indices/<SLUG>/constituents/table
INDEX_SLUG_MAP: dict[str, str] = {
    # FTSE 100
    "FTSE 100":                    "ftse-100",
    "FTSE100":                     "ftse-100",
    # FTSE 250
    "FTSE 250":                    "ftse-250",
    "FTSE250":                     "ftse-250",
    # FTSE 350
    "FTSE 350":                    "ftse-350",
    "FTSE350":                     "ftse-350",
    # FTSE All-Share
    "FTSE All-Share":              "ftse-all-share",
    "FTSE ALL SHARE":              "ftse-all-share",
    "FTSE All Share":              "ftse-all-share",
    # FTSE AIM UK 50
    "FTSE AIM UK 50 Index":        "ftse-aim-uk-50-index",
    "FTSE AIM UK 50":              "ftse-aim-uk-50-index",
    # FTSE AIM 100
    "FTSE AIM 100 Index":          "ftse-aim-100-index",
    "FTSE AIM 100":                "ftse-aim-100-index",
    # FTSE AIM All-Share
    "FTSE AIM All-Share":          "ftse-aim-all-share",
    "FTSE AIM All Share":          "ftse-aim-all-share",
    # FTSE MID 250
    "FTSE MID 250 (ex IT)":        "ftse-mid-250",
    "FTSE MID 250":                "ftse-mid-250",
    # FTSE 350 High Yield
    "FTSE 350 High Yield":         "ftse-350-high-yield",
    # FTSE 350 Low Yield
    "FTSE 350 Low Yield":          "ftse-350-low-yield",
    # FTSE 350 (ex IT)
    "FTSE 350 (ex IT)":            "ftse-350-ex-investment-trusts",
    "FTSE 350 ex IT":              "ftse-350-ex-investment-trusts",
    # FTSE All-Share (ex IT)
    "FTSE All-Share (ex IT)":      "ftse-all-share-ex-investment-trusts",
    "FTSE All Share (ex IT)":      "ftse-all-share-ex-investment-trusts",
    # FTSE 4Good indices
    "FTSE 4Good UK Idx":           "ftse4good-uk-index",
    "FTSE 4Good UK":               "ftse4good-uk-index",
    "FTSE 4Good USA Idx":          "ftse4good-usa-index",
    "FTSE 4Good USA":              "ftse4good-usa-index",
    "FTSE 4Good Global Idx":       "ftse4good-global-100-index",
    "FTSE 4Good Global":           "ftse4good-global-100-index",
    "FTSE 4Good Europe Idx":       "ftse4good-europe-index",
    "FTSE 4Good Europe":           "ftse4good-europe-index",
}

LSE_BASE = "https://www.londonstockexchange.com/indices/{slug}/constituents/table"


def _resolve_slug(index_name: str) -> Optional[str]:
    """Return the LSE URL slug for a given index name (case-insensitive)."""
    # Exact match first
    if index_name in INDEX_SLUG_MAP:
        return INDEX_SLUG_MAP[index_name]
    # Case-insensitive match
    lower = index_name.lower()
    for key, slug in INDEX_SLUG_MAP.items():
        if key.lower() == lower:
            return slug
    return None


def scrape_lse_constituents(index_name: str, timeout_ms: int = 30_000) -> list[dict]:
    """
    Scrape the constituent table for *index_name* from the LSE website.

    Returns a list of dicts:
        {name, ticker, sector, index_tags: [index_name]}

    Raises LSEScrapingError on any failure so callers can fall back gracefully.
    """
    slug = _resolve_slug(index_name)
    if not slug:
        raise LSEScrapingError(f"Unknown index name: '{index_name}'. No LSE slug mapping found.")

    url = LSE_BASE.format(slug=slug)
    logger.info(f"[LSEScraper] Scraping '{index_name}' from {url}")

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        raise LSEScrapingError("playwright is not installed. Run: pip install playwright && playwright install chromium")

    companies: list[dict] = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()

            # Set a realistic user-agent to reduce bot-detection chance
            page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            })

            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            # Wait for the constituent table to appear (LSE renders it via JS)
            try:
                page.wait_for_selector("table tbody tr, [data-module='table'] tbody tr", timeout=timeout_ms)
            except PWTimeout:
                browser.close()
                raise LSEScrapingError(
                    f"Timed out waiting for constituent table on {url}. "
                    "The page may require JS execution that failed or the index has no constituents."
                )

            html = page.content()
            browser.close()

        # Parse the HTML with BeautifulSoup
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise LSEScrapingError("beautifulsoup4 is not installed.")

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            raise LSEScrapingError(f"No <table> found in rendered HTML for {url}")

        rows = table.find("tbody").find_all("tr") if table.find("tbody") else []
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if not cells:
                continue
            name = cells[0] if len(cells) > 0 else "Unknown"
            ticker = cells[1] if len(cells) > 1 else ""
            sector = cells[2] if len(cells) > 2 else "Unknown"
            if name and name.lower() not in ("name", "company"):
                companies.append({
                    "name": name,
                    "ticker": ticker,
                    "sector": sector,
                    "index_tags": [index_name],
                })

        logger.info(f"[LSEScraper] Scraped {len(companies)} companies for '{index_name}'")

    except LSEScrapingError:
        raise
    except Exception as exc:
        raise LSEScrapingError(f"Unexpected error scraping {url}: {exc}") from exc

    return companies


def get_all_supported_indices() -> list[str]:
    """Return the canonical list of supported index names."""
    seen, result = set(), []
    for key in INDEX_SLUG_MAP:
        slug = INDEX_SLUG_MAP[key]
        if slug not in seen:
            seen.add(slug)
            result.append(key)
    return result
