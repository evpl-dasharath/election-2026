import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()

from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    )
    page = context.new_page()
    # Go DIRECTLY to the AC page
    page.goto('https://results.eci.gov.in/ResultAcGenNov2025/ConstituencywiseS04171.htm')
    print('Title:', page.title())
    if 'Access Denied' in page.content():
        print('Blocked by Akamai!')
    else:
        print('Success!')
