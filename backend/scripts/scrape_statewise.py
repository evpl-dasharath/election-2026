#!/usr/bin/env python3
"""
scrape_statewise.py
====================
Scrapes ECI statewise results pages (statewiseS111.htm ... statewiseS117.htm)
to bulk-update all 140 Kerala constituencies' RESULT_DECLARED status.

Uses AC No to match -- NO candidate matching needed.
Only flips LiveResult.status to RESULT_DECLARED when ECI says so,
and does a PARTIAL Firebase update (ref.update) so candidate data is preserved.

Usage (from backend/ directory):
    python scrape_statewise.py            # live update
    python scrape_statewise.py --dry-run  # parse only, no DB/RTDB writes
"""

import os, sys, re, time, argparse, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from core.models import Constituency, LiveResult
from django.utils import timezone

BASE_URL   = "https://results.eci.gov.in/ResultAcGenMay2026"
STATE_CODE = "S11"
NUM_PAGES  = 7   # statewiseS111.htm to statewiseS117.htm

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://results.eci.gov.in/",
}


# -- Scrape -------------------------------------------------------------------

def scrape_all_pages():
    from playwright.sync_api import sync_playwright

    all_rows = []
    with sync_playwright() as pw:
        # headless=False is REQUIRED to bypass Akamai WAF
        browser = pw.chromium.launch(headless=False)
        ctx = browser.new_context(
            user_agent=REQUEST_HEADERS["User-Agent"],
            locale="en-IN",
            extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
        )
        page = ctx.new_page()

        # Seed cookies / WAF state
        try:
            page.goto(f"{BASE_URL}/index.htm", timeout=15000, wait_until="domcontentloaded")
        except Exception:
            pass

        for pnum in range(1, NUM_PAGES + 1):
            url = f"{BASE_URL}/statewise{STATE_CODE}{pnum}.htm"
            print(f"  [{pnum}/{NUM_PAGES}] {url}")
            try:
                page.goto(url, timeout=25000, wait_until="networkidle")
                try:
                    page.wait_for_selector("table", timeout=6000)
                except Exception:
                    pass
                html = page.content()
            except Exception as e:
                print(f"    [FAIL] {e}")
                continue

            rows = _parse_page(html, pnum)
            all_rows.extend(rows)
            print(f"    -> {len(rows)} rows parsed")

            if pnum < NUM_PAGES:
                time.sleep(1.2)

        browser.close()

    return all_rows


# -- Parse --------------------------------------------------------------------

def _parse_page(html, page_num):
    """
    Parse one ECI statewise page.

    ECI May 2026 table columns (0-indexed, DIRECT td children only):
      0: Constituency Name
      1: Const. No  (AC number)
      2: Leading Candidate
      3: Leading Party  -- contains nested <table> for tooltip
      4: Trailing Candidate
      5: Trailing Party -- contains nested <table> for tooltip
      6: Margin
      7: Round  (e.g. "17/17")
      8: Status  (e.g. "Result Declared" / "Result in Progress")

    Key: use recursive=False when finding tds so that the nested tooltip
    tables inside the party cells don't produce phantom extra columns.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    results = []

    tables = soup.find_all("table")
    if not tables:
        print(f"    [WARN] No table found on page {page_num}")
        return results

    # Pick the widest top-level table (the main results table)
    table = max(tables, key=lambda t: len(t.find_all("tr")))
    rows = table.find_all("tr")

    for row in rows:
        # Skip header rows
        if row.find("th"):
            continue

        # Only get DIRECT <td> children - this skips nested tooltip tables
        tds = row.find_all("td", recursive=False)
        if len(tds) < 9:
            continue

        # AC Number is column 1
        ac_raw = tds[1].get_text(strip=True)
        m = re.search(r"\d+", ac_raw)
        if not m:
            continue
        ac_no = int(m.group())
        if ac_no < 1 or ac_no > 140:
            continue

        # Status is column 8 -- no nested tables here, clean text
        status_text = tds[8].get_text(strip=True).lower()
        if "declared" in status_text:
            status = "RESULT_DECLARED"
        else:
            status = "IN_PROGRESS"

        results.append({"ac_no": ac_no, "status": status})

    return results


# -- Commit to DB + partial RTDB update --------------------------------------

def commit(rows, dry_run=False):
    from firebase_admin import db as rtdb

    updated_declared = 0
    already_declared = 0
    in_progress = 0

    for row in rows:
        ac_no    = row["ac_no"]
        is_final = row["status"] == "RESULT_DECLARED"

        try:
            constituency = Constituency.objects.get(number=ac_no)
        except Constituency.DoesNotExist:
            print(f"  [SKIP] AC {ac_no} -- not in DB")
            continue

        if dry_run:
            label = "DECLARED" if is_final else "in progress"
            print(f"  [DRY] AC {ac_no:3d} {constituency.name:<28} {label}")
            if is_final:
                updated_declared += 1
            else:
                in_progress += 1
            continue

        live, _ = LiveResult.objects.get_or_create(constituency=constituency)

        if is_final and live.status != "RESULT_DECLARED":
            # Update DB
            live.status = "RESULT_DECLARED"
            live.save()

            # PARTIAL RTDB update -- ref.update() NOT ref.set()
            # ref.set() would WIPE the entire node including candidates!
            try:
                ref = rtdb.reference(f"/live/{ac_no}")
                ref.update({
                    "status":       "RESULT_DECLARED",
                    "last_updated": timezone.now().isoformat(),
                })
            except Exception as e:
                print(f"  [RTDB ERR] AC {ac_no}: {e}")

            print(f"  [DECLARED] AC {ac_no:3d} {constituency.name:<28}")
            updated_declared += 1

        elif is_final:
            already_declared += 1
        else:
            in_progress += 1

    if not dry_run:
        try:
            from firebase_rtdb import update_rtdb_meta
            update_rtdb_meta()
        except Exception as e:
            print(f"  [META ERR] {e}")

    print(
        f"\n  Done -- {updated_declared} newly declared, "
        f"{already_declared} already declared, {in_progress} in progress\n"
    )
    return updated_declared


# -- Main ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ECI Statewise Scraper - Kerala 2026"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and print only -- no writes")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  ECI Statewise Scraper -- Kerala 2026")
    print(f"  Mode : {'DRY RUN' if args.dry_run else 'LIVE UPDATE'}")
    print(f"{'='*60}\n")

    rows = scrape_all_pages()
    total = len(rows)
    print(f"\n  Total rows scraped: {total}")

    if not total:
        print("  Nothing to commit. Check network/WAF access.")
        sys.exit(1)

    declared_count = sum(1 for r in rows if r["status"] == "RESULT_DECLARED")
    print(f"  Declared: {declared_count} | In Progress: {total - declared_count}\n")

    commit(rows, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
