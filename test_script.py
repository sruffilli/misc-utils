from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
    page.on("pageerror", lambda err: print(f"Browser Error: {err.message}"))
    page.goto("http://localhost:8000/subnet-calculator.html")
    page.wait_for_selector(".cursor-pointer") # Wait for the row to load
    page.click(".cursor-pointer")
    page.wait_for_timeout(1000)
    print("Widget present:", page.locator("text=Subnet Details").count() > 0)
    browser.close()
