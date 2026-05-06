import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()

from core.eci_scraper import _fetch_html, BIHAR_TEST_BASE_URL, BIHAR_STATE_CODE, _cleanup_playwright

_cleanup_playwright()

url = f"{BIHAR_TEST_BASE_URL}/Constituencywise{BIHAR_STATE_CODE}171.htm"
html, err = _fetch_html(url, BIHAR_TEST_BASE_URL)

if err:
    print(f"Error: {err}")
else:
    with open("debug_html.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved HTML to debug_html.html")

_cleanup_playwright()
