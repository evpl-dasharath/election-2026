# backend/core/eci_scraper.py
"""
ECI Results Scraper — Service Module
=====================================
Fetches and parses HTML from results.eci.gov.in.
Returns structured data; does NOT touch the database.
Database writes happen in admin_views.py / scraper_views.py.

Uses Playwright (headless Chromium) to bypass ECI's Akamai WAF.
Falls back to plain requests if Playwright is unavailable.
"""

import re
from datetime import datetime

# ─── Optional Playwright import ──────────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

import requests

# ─── CONFIG ──────────────────────────────────────────────────────────────────

# Switch base URL on results day if ECI uses a different folder name
ECI_BASE_URL = "https://results.eci.gov.in/ResultAcGenMay2026"
KERALA_STATE_CODE = "S11"

# For testing against Bihar Nov 2025 results
BIHAR_TEST_BASE_URL = "https://results.eci.gov.in/ResultAcGenNov2025"
BIHAR_STATE_CODE = "S04"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://results.eci.gov.in/",
}
REQUEST_TIMEOUT = 20  # seconds


# ─── BROWSER MANAGEMENT ─────────────────────────────────────────────────────

import threading
_pw_local = threading.local()

def _get_playwright_page(base_url):
    """
    Return a reusable Playwright page bound to the current thread.
    On first call per thread (or if manually closed), it launches Chromium.
    """
    # Check if we have a cached page, it's for the same base URL, and it HAS NOT been closed by the user
    if hasattr(_pw_local, 'pw_page'):
        try:
            if getattr(_pw_local, 'seeded_base', None) == base_url and not _pw_local.pw_page.is_closed():
                return _pw_local.pw_page
        except Exception:
            pass  # If is_closed() throws an error (e.g. browser disconnected), fall through to recreate

    # Clean up any broken/closed instance in this thread
    _cleanup_playwright()

    _pw_local.pw_instance = sync_playwright().start()
    _pw_local.pw_browser = _pw_local.pw_instance.chromium.launch(headless=False)
    context = _pw_local.pw_browser.new_context(
        user_agent=REQUEST_HEADERS["User-Agent"],
        locale="en-IN",
        extra_http_headers={
            "Accept-Language": "en-IN,en;q=0.9",
        },
    )
    _pw_local.pw_page = context.new_page()
    _pw_local.seeded_base = base_url
    
    return _pw_local.pw_page


def _cleanup_playwright():
    if hasattr(_pw_local, 'pw_browser'):
        try:
            _pw_local.pw_browser.close()
        except Exception:
            pass
        delattr(_pw_local, 'pw_browser')
        
    if hasattr(_pw_local, 'pw_instance'):
        try:
            _pw_local.pw_instance.stop()
        except Exception:
            pass
        delattr(_pw_local, 'pw_instance')
        
    if hasattr(_pw_local, 'pw_page'):
        delattr(_pw_local, 'pw_page')
    if hasattr(_pw_local, 'seeded_base'):
        delattr(_pw_local, 'seeded_base')


# ─── FETCH HTML ──────────────────────────────────────────────────────────────

def _fetch_html(url, base_url):
    """
    Fetch HTML from a URL. Uses Playwright if available (bypasses WAF),
    falls back to requests.
    """
    if HAS_PLAYWRIGHT:
        try:
            page = _get_playwright_page(base_url)
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            # ECI renders the results table via JS — wait for it to appear
            try:
                page.wait_for_selector("table", timeout=5000)
            except Exception:
                pass  # Proceed anyway, parse will catch missing table
            return page.content(), None
        except Exception as e:
            return None, f"Playwright fetch failed: {e}"

    # Fallback to requests
    try:
        session = requests.Session()
        session.headers.update(REQUEST_HEADERS)
        # Seed cookies
        try:
            session.get(base_url + "/index.htm", timeout=15)
        except Exception:
            pass
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text, None
    except requests.exceptions.Timeout:
        return None, f"Timeout fetching {url}"
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP {e.response.status_code}"
    except requests.exceptions.RequestException as e:
        return None, str(e)


# ─── PARSE HTML ──────────────────────────────────────────────────────────────

def _parse_constituency_html(html, ac_number):
    """
    Parse the ECI constituency results page HTML.
    Returns a dict with structured candidate data.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")

    # ── Constituency name
    constituency_name = f"AC {ac_number}"
    h2 = soup.find("h2")
    if h2:
        match = re.search(r"Constituency\s+\d+\s*[-–]\s*(.+?)(?:\s*\(|$)", h2.get_text())
        if match:
            constituency_name = match.group(1).strip()

    # ── Round status
    rounds_completed = 0
    total_rounds = 0

    for tag in soup.find_all(["h2", "h3", "p", "div", "span"]):
        text = tag.get_text(strip=True)
        if "Round" in text and "/" in text:
            match = re.search(r"Round[,\s]+(\d+)\s*/\s*(\d+)", text)
            if match:
                rounds_completed = int(match.group(1))
                total_rounds = int(match.group(2))
                # Don't break, keep searching for "Result Declared"

    # Check for explicit "Result Declared" text (ECI often uses this)
    is_final = False
    if rounds_completed > 0 and rounds_completed == total_rounds:
        is_final = True
    
    # Also scan the page text for "Result Declared"
    page_text = soup.get_text().lower()
    if "result declared" in page_text:
        is_final = True

    # ── Last updated
    eci_last_updated = ""
    for text_node in soup.find_all(string=re.compile(r"Last Updated", re.I)):
        eci_last_updated = text_node.strip()
        break

    # ── Candidate table
    table = soup.find("table")
    if not table:
        return None, f"No results table found for AC {ac_number} — page may not be live yet"

    candidates = []
    for row in table.find_all("tr")[1:]:  # skip header
        cols = [td.get_text(strip=True) for td in row.find_all("td")]

        if len(cols) < 6:
            continue
        if cols[1].lower() in ("candidate", "total", ""):
            continue

        try:
            name = cols[1].strip()
            party = cols[2].strip()
            evm_votes    = int(re.sub(r"[,\s]", "", cols[3]) or "0")
            postal_votes = int(re.sub(r"[,\s]", "", cols[4]) or "0")
            total_votes  = int(re.sub(r"[,\s]", "", cols[5]) or "0")
            vote_pct     = float(cols[6]) if len(cols) > 6 and cols[6] else 0.0

            candidates.append({
                "name":            name,
                "party":           party,
                "evm_votes":       evm_votes,
                "postal_votes":    postal_votes,
                "total_votes":     total_votes,
                "vote_percentage": vote_pct,
                "is_nota":         name.upper() == "NOTA",
                "is_leading":      False,
            })
        except (ValueError, IndexError):
            continue

    if not candidates:
        return None, f"Table found but no candidates parsed for AC {ac_number}"

    # Mark leader (highest votes among non-NOTA)
    non_nota = [c for c in candidates if not c["is_nota"]]
    if non_nota:
        non_nota.sort(key=lambda x: x["total_votes"], reverse=True)
        non_nota[0]["is_leading"] = True

    return {
        "constituency_name": constituency_name,
        "rounds_completed":  rounds_completed,
        "total_rounds":      total_rounds,
        "is_final":          is_final,
        "eci_last_updated":  eci_last_updated,
        "candidates":        candidates,
    }, None


# ─── MAIN FUNCTION ───────────────────────────────────────────────────────────

def scrape_constituency(ac_number, base_url=None, state_code=None):
    """
    Scrape a single constituency from ECI results website.

    Args:
        ac_number:  Integer, 1–140 for Kerala
        base_url:   Override ECI_BASE_URL (e.g. for testing with Bihar)
        state_code: Override KERALA_STATE_CODE

    Returns:
        dict with keys:
            success (bool)
            error (str, only if success=False)
            ac_number, constituency_name
            rounds_completed, total_rounds, is_final
            eci_last_updated
            candidates (list of dicts)
            source_url

        Each candidate dict:
            name, party, evm_votes, postal_votes,
            total_votes, vote_percentage, is_nota, is_leading
    """
    base_url = base_url or ECI_BASE_URL
    state_code = state_code or KERALA_STATE_CODE

    url = f"{base_url}/Constituencywise{state_code}{ac_number}.htm"

    # ── Fetch
    html, fetch_error = _fetch_html(url, base_url)
    if fetch_error:
        return {"success": False, "error": fetch_error, "source_url": url}

    # ── Parse
    result, parse_error = _parse_constituency_html(html, ac_number)
    if parse_error:
        return {"success": False, "error": parse_error, "source_url": url}

    return {
        "success":           True,
        "ac_number":         ac_number,
        "constituency_name": result["constituency_name"],
        "rounds_completed":  result["rounds_completed"],
        "total_rounds":      result["total_rounds"],
        "is_final":          result["is_final"],
        "eci_last_updated":  result["eci_last_updated"],
        "candidates":        result["candidates"],
        "source_url":        url,
    }


def scrape_multiple(ac_numbers, base_url=None, state_code=None, delay=1.5, progress_callback=None):
    """
    Scrape multiple constituencies with a polite delay between requests.

    Args:
        ac_numbers:        List of AC numbers
        delay:             Seconds between requests
        progress_callback: Optional fn(ac_number, result) called after each fetch

    Returns:
        dict { ac_number: result_dict, ... }
    """
    import time
    results = {}
    for i, ac_num in enumerate(ac_numbers):
        if i > 0:
            time.sleep(delay)
        result = scrape_constituency(ac_num, base_url=base_url, state_code=state_code)
        results[ac_num] = result
        if progress_callback:
            progress_callback(ac_num, result)
    return results
