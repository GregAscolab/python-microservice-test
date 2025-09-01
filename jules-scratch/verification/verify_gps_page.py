from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("http://127.0.0.1:8000/gps")
    # Wait for the map to be visible
    expect(page.locator("#map-gps")).to_be_visible(timeout=10000)
    # Take a screenshot
    page.screenshot(path="jules-scratch/verification/gps_page.png")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
