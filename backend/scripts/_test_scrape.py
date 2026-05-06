import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()

from core.eci_scraper import scrape_constituency, BIHAR_TEST_BASE_URL, BIHAR_STATE_CODE, _cleanup_playwright

# Force fresh browser (clear cached page from previous run)
_cleanup_playwright()

print("Testing Bihar AC 171 with Playwright (waiting for table)...")
r = scrape_constituency(171, base_url=BIHAR_TEST_BASE_URL, state_code=BIHAR_STATE_CODE)

if r['success']:
    print(f"SUCCESS!")
    print(f"  Constituency: {r['constituency_name']}")
    print(f"  Rounds: {r['rounds_completed']}/{r['total_rounds']}")
    print(f"  Final: {r['is_final']}")
    print(f"  Candidates: {len(r['candidates'])}")
    for c in r['candidates'][:5]:
        print(f"    {c['name']} ({c['party']}) - {c['total_votes']:,} votes {'[LEADING]' if c['is_leading'] else ''}")
else:
    print(f"FAILED: {r['error']}")
    print(f"  URL: {r.get('source_url', 'N/A')}")

_cleanup_playwright()
