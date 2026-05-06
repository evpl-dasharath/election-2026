#!/usr/bin/env python3
"""
ECI Results Scraper — Test Script
==================================
Tests against Bihar (Nov 2025) data to validate parsing before Kerala results day.

Usage:
    # Single constituency (quick test)
    python scrape_eci_test.py --ac 187

    # All Bihar constituencies (stress test)
    python scrape_eci_test.py --all

    # Save output to JSON
    python scrape_eci_test.py --ac 187 --json

    # Test multiple specific ACs
    python scrape_eci_test.py --ac 1 --ac 50 --ac 100 --ac 187 --ac 243

Install deps first:
    pip install requests beautifulsoup4 lxml
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import argparse
import sys
from datetime import datetime

# Try to import playwright; fall back to requests with a warning
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# ─── CONFIG ──────────────────────────────────────────────────────────────────

# For testing: Bihar Nov 2025
TEST_CONFIG = {
    "base_url": "https://results.eci.gov.in/ResultAcGenNov2025",
    "state_code": "S04",
    "total_acs": 243,
    "state_name": "Bihar",
}

# For Kerala May 2026 (switch to this on results day)
KERALA_CONFIG = {
    "base_url": "https://results.eci.gov.in/ResultAcGenMay2026",
    "state_code": "S11",
    "total_acs": 140,
    "state_name": "Kerala",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://results.eci.gov.in/",
}

# ─── SCRAPER ─────────────────────────────────────────────────────────────────

def make_session(config):
    """
    Requests fallback: create a Session pre-seeded with homepage cookies.
    Used only when Playwright is unavailable.
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        seed_url = config["base_url"] + "/index.htm"
        session.get(seed_url, timeout=15)
    except requests.RequestException:
        pass
    return session


def make_playwright_context(playwright_instance, config):
    """
    Launch a headless Chromium browser, navigate to the ECI homepage to
    seed cookies/JS state, then return the (browser, page) tuple.
    """
    browser = playwright_instance.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=HEADERS["User-Agent"],
        locale="en-IN",
        extra_http_headers={
            "Accept-Language": "en-IN,en;q=0.9",
        },
    )
    page = context.new_page()
    # Seed cookies by visiting the index page first
    try:
        seed_url = config["base_url"] + "/index.htm"
        page.goto(seed_url, timeout=20000, wait_until="domcontentloaded")
    except Exception:
        pass  # Non-fatal
    return browser, page


def scrape_constituency(ac_number, config, fetch):
    """
    Scrape a single constituency from ECI results page.
    Returns a dict with parsed data, or None on failure.

    `fetch` is either:
      - a Playwright Page object  (preferred, bypasses Akamai)
      - a requests.Session object (fallback)

    URL pattern: {base_url}/Constituencywise{STATE_CODE}{ac_number}.htm
    Example:     .../ResultAcGenNov2025/ConstituencywiseS04187.htm
    """
    url = f"{config['base_url']}/Constituencywise{config['state_code']}{ac_number}.htm"

    try:
        if HAS_PLAYWRIGHT and hasattr(fetch, 'goto'):
            # Playwright path
            fetch.goto(url, timeout=20000, wait_until="domcontentloaded")
            html = fetch.content()
        else:
            # requests fallback
            resp = fetch.get(url, timeout=15)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        print(f"  [FAIL] AC {ac_number}: Fetch failed -- {e}")
        return None

    soup = BeautifulSoup(html, "lxml")

    # ── Constituency name ────────────────────────────────────────────────────
    constituency_name = "Unknown"
    h2 = soup.find("h2")
    if h2:
        # e.g. "Assembly Constituency 187 - MANER (Bihar)"
        match = re.search(r"Constituency\s+\d+\s*[-–]\s*(.+?)\s*\(", h2.get_text())
        if match:
            constituency_name = match.group(1).strip()

    # ── Round status ─────────────────────────────────────────────────────────
    rounds_completed = 0
    total_rounds = 0
    is_final = False

    # "Status as on Round, 31/31"
    for tag in soup.find_all(["h2", "h3", "p", "div", "span"]):
        text = tag.get_text()
        if "Round" in text and "/" in text:
            match = re.search(r"Round[,\s]+(\d+)\s*/\s*(\d+)", text)
            if match:
                rounds_completed = int(match.group(1))
                total_rounds = int(match.group(2))
                is_final = rounds_completed == total_rounds and total_rounds > 0
                break

    # ── Last updated time ────────────────────────────────────────────────────
    last_updated = None
    for tag in soup.find_all(string=re.compile(r"Last Updated", re.I)):
        last_updated = tag.strip()
        break

    # ── Candidate table ──────────────────────────────────────────────────────
    # ECI uses a plain <table> with columns:
    # S.N. | Candidate | Party | EVM Votes | Postal Votes | Total Votes | % of Votes
    table = soup.find("table")
    if not table:
        print(f"  [FAIL] AC {ac_number}: No table found")
        return None

    candidates = []
    total_valid_votes = 0

    for row in table.find_all("tr")[1:]:  # skip header row
        cols = [td.get_text(strip=True) for td in row.find_all("td")]

        # Skip empty rows, header repeats, and the Total row
        if len(cols) < 6:
            continue
        if cols[1].lower() in ("candidate", "total", ""):
            continue

        try:
            name = cols[1].strip()
            party = cols[2].strip()

            # Remove commas from vote numbers: "1,10,798" → 110798
            evm_votes = int(re.sub(r"[,\s]", "", cols[3]) or "0")
            postal_votes = int(re.sub(r"[,\s]", "", cols[4]) or "0")
            total_votes = int(re.sub(r"[,\s]", "", cols[5]) or "0")
            vote_pct = float(cols[6]) if len(cols) > 6 and cols[6] else 0.0

            candidates.append({
                "name": name,
                "party": party,
                "evm_votes": evm_votes,
                "postal_votes": postal_votes,
                "total_votes": total_votes,
                "vote_percentage": vote_pct,
                "is_nota": name.upper() == "NOTA",
                "is_leading": False,
                "is_winner": False,
            })

            if name.upper() != "NOTA":
                total_valid_votes += total_votes

        except (ValueError, IndexError) as e:
            # Silently skip malformed rows
            continue

    if not candidates:
        print(f"  [FAIL] AC {ac_number}: No candidates parsed")
        return None

    # ── Determine leader / winner ─────────────────────────────────────────────
    non_nota = [c for c in candidates if not c["is_nota"]]
    win_reason = None

    if non_nota:
        non_nota.sort(key=lambda x: x["total_votes"], reverse=True)
        leader = non_nota[0]
        leader["is_leading"] = True

        margin = leader["total_votes"] - (non_nota[1]["total_votes"] if len(non_nota) >= 2 else 0)

        # Estimate how many votes are still to be counted for this constituency.
        # We use the round ratio as a proxy: if 8 of 16 rounds are done, roughly
        # half the votes are still outstanding.
        if rounds_completed > 0 and total_rounds > 0:
            votes_so_far = total_valid_votes
            estimated_total  = int(votes_so_far * (total_rounds / rounds_completed))
            votes_remaining  = max(0, estimated_total - votes_so_far)
        else:
            votes_remaining = 0

        # Condition 1 — ALL rounds counted (ECI official final)
        if is_final:
            leader["is_winner"] = True
            win_reason = "all_rounds_complete"

        # Condition 2 — Leader has > 50 % of votes cast: mathematically unbeatable
        elif total_valid_votes > 0 and leader["total_votes"] > total_valid_votes / 2:
            leader["is_winner"] = True
            win_reason = "fifty_percent_majority"

        # Condition 3 — Insurmountable lead: even if runner-up gets every
        #               remaining ballot they still can't overtake the leader
        elif votes_remaining > 0 and margin > votes_remaining:
            leader["is_winner"] = True
            win_reason = "insurmountable_lead"

    else:
        margin = 0
        votes_remaining = 0

    return {
        "ac_number": ac_number,
        "constituency_name": constituency_name,
        "state": config["state_name"],
        "rounds_completed": rounds_completed,
        "total_rounds": total_rounds,
        "is_final": is_final,
        "total_valid_votes": total_valid_votes,
        "margin": margin,
        "votes_remaining_estimate": votes_remaining if rounds_completed > 0 else None,
        "win_reason": win_reason,       # None = still leading, string = won + why
        "last_updated": last_updated,
        "candidates": candidates,
        "source_url": url,
        "scraped_at": datetime.now().isoformat(),
    }


# ─── DISPLAY ─────────────────────────────────────────────────────────────────

def display_result(data):
    """Pretty-print a single constituency result."""
    if data["is_final"]:
        status = "[FINAL — all rounds complete]"
    elif data.get("win_reason") == "fifty_percent_majority":
        status = f"[WON — 50%+ majority] Round {data['rounds_completed']}/{data['total_rounds']}"
    elif data.get("win_reason") == "insurmountable_lead":
        rem = data.get("votes_remaining_estimate", 0)
        status = f"[WON — margin {data['margin']:,} > ~{rem:,} remaining] Round {data['rounds_completed']}/{data['total_rounds']}"
    else:
        status = f"[Leading] Round {data['rounds_completed']}/{data['total_rounds']}"

    print(f"\n{'═' * 70}")
    print(f"  AC {data['ac_number']} — {data['constituency_name']} ({data['state']})")
    print(f"  Status : {status}")
    print(f"  Votes  : {data['total_valid_votes']:,}  |  Margin: {data['margin']:,}", end="")
    if data.get("votes_remaining_estimate") is not None:
        print(f"  |  Est. remaining: ~{data['votes_remaining_estimate']:,}", end="")
    print()
    if data["last_updated"]:
        print(f"  Updated: {data['last_updated']}")
    print(f"{'─' * 70}")
    print(f"  {'#':<4} {'Candidate':<40} {'Party':<28} {'Votes':>8}  {'%':>6}")
    print(f"  {'─'*4} {'─'*40} {'─'*28} {'─'*8}  {'─'*6}")

    for i, c in enumerate(sorted(data["candidates"], key=lambda x: x["total_votes"], reverse=True)):
        marker = ""
        if c["is_winner"]:
            marker = " [WIN]"
        elif c["is_leading"]:
            marker = " [+]"
        elif c["is_nota"]:
            marker = " [NOTA]"

        print(f"  {i+1:<4} {c['name']:<40} {c['party']:<28} {c['total_votes']:>8,}  {c['vote_percentage']:>5.1f}%{marker}")

    print(f"{'═' * 70}\n")


def display_summary(results):
    """Show a quick summary table for multiple constituencies."""
    print(f"\n{'═' * 90}")
    print(f"  {'AC':<5} {'Constituency':<25} {'Winner/Leader':<30} {'Party':<20} {'Margin':>8}  Status")
    print(f"  {'─'*5} {'─'*25} {'─'*30} {'─'*20} {'─'*8}  {'─'*10}")
    for data in results:
        non_nota = [c for c in data["candidates"] if not c["is_nota"]]
        leader = next((c for c in non_nota if c["is_leading"]), None)
        if leader:
            status = "FINAL" if data["is_final"] else f"Rd {data['rounds_completed']}/{data['total_rounds']}"
            print(f"  {data['ac_number']:<5} {data['constituency_name']:<25} {leader['name'][:29]:<30} {leader['party'][:19]:<20} {data['margin']:>8,}  {status}")
    print(f"{'═' * 90}\n")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ECI Results Scraper — Test Mode (Bihar)")
    parser.add_argument("--ac", type=int, action="append", metavar="N",
                        help="AC number to scrape (can repeat: --ac 1 --ac 50)")
    parser.add_argument("--all", action="store_true", help="Scrape all ACs for the state")
    parser.add_argument("--kerala", action="store_true", help="Use Kerala config instead of Bihar test config")
    parser.add_argument("--json", action="store_true", help="Save results to JSON file")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Delay between requests in seconds (default: 1.5)")
    args = parser.parse_args()

    config = KERALA_CONFIG if args.kerala else TEST_CONFIG

    print(f"\n[ECI Scraper] {config['state_name']} ({config['state_code']})")
    print(f"   Base URL : {config['base_url']}")
    print(f"   Mode     : {'Kerala 2026' if args.kerala else 'Bihar test (Nov 2025)'}")

    # Determine which ACs to scrape
    if args.all:
        ac_list = list(range(1, config["total_acs"] + 1))
        print(f"   Scraping : ALL {len(ac_list)} constituencies")
    elif args.ac:
        ac_list = args.ac
        print(f"   Scraping : AC(s) {ac_list}")
    else:
        # Default: sample of 5 Bihar ACs
        ac_list = [1, 50, 100, 187, 243]
        print(f"   Scraping : Default sample {ac_list}")
        print(f"   (Use --ac N to specify, --all to scrape everything)")

    print()

    results = []
    failed = []

    if HAS_PLAYWRIGHT:
        print("  Using Playwright (headless Chromium) to bypass ECI WAF...")
        with sync_playwright() as pw:
            browser, page = make_playwright_context(pw, config)
            print("  Browser ready.\n")

            for i, ac_num in enumerate(ac_list):
                if i > 0:
                    time.sleep(args.delay)

                print(f"  Fetching AC {ac_num}/{config['total_acs']}...", end=" ", flush=True)
                data = scrape_constituency(ac_num, config, page)

                if data:
                    results.append(data)
                    leader = next((c for c in data["candidates"] if c["is_leading"] and not c["is_nota"]), None)
                    leader_str = f"{leader['name']} ({leader['party'][:15]})" if leader else "unknown"
                    status = "FINAL" if data["is_final"] else f"Rd {data['rounds_completed']}/{data['total_rounds']}"
                    print(f"[OK] {data['constituency_name']} -- {leader_str} -- {status}")
                else:
                    failed.append(ac_num)

            browser.close()
    else:
        print("  WARNING: playwright not installed. Falling back to requests (may hit 403).")
        print("  Install with: pip install playwright; python -m playwright install chromium\n")
        session = make_session(config)

        for i, ac_num in enumerate(ac_list):
            if i > 0:
                time.sleep(args.delay)

            print(f"  Fetching AC {ac_num}/{config['total_acs']}...", end=" ", flush=True)
            data = scrape_constituency(ac_num, config, session)

            if data:
                results.append(data)
                leader = next((c for c in data["candidates"] if c["is_leading"] and not c["is_nota"]), None)
                leader_str = f"{leader['name']} ({leader['party'][:15]})" if leader else "unknown"
                status = "FINAL" if data["is_final"] else f"Rd {data['rounds_completed']}/{data['total_rounds']}"
                print(f"[OK] {data['constituency_name']} -- {leader_str} -- {status}")
            else:
                failed.append(ac_num)

    # Display results
    if len(results) == 1:
        display_result(results[0])
    elif results:
        display_summary(results)
        # Also show full detail for first result
        print("\nFull detail for first result:")
        display_result(results[0])

    # Stats
    print(f"\n[Done] {len(results)} scraped, {len(failed)} failed")
    if failed:
        print(f"   Failed ACs: {failed}")

    # Save to JSON if requested
    if args.json and results:
        filename = f"eci_results_{config['state_code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n[Saved] {filename}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
