import time
from playwright.sync_api import sync_playwright

url = "https://results.eci.gov.in/ResultAcGenMay2026/statewiseS111.htm"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale="en-IN"
    )
    page = ctx.new_page()
    try:
        page.goto("https://results.eci.gov.in/ResultAcGenMay2026/index.htm", timeout=20000, wait_until="domcontentloaded")
    except Exception:
        pass
    
    page.goto(url, wait_until="networkidle", timeout=30000)
    time.sleep(5)
    
    html = page.content()
    page.screenshot(path="debug_screenshot.png")
    
    with open("debug_eci.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"Saved {len(html)} bytes to debug_eci.html and screenshot to debug_screenshot.png")
    browser.close()
