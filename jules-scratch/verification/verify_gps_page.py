from playwright.sync_api import Page, expect, sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        # Navigate to the home page.
        page.goto("http://localhost:8000/")

        # Click on the GPS link in the sidebar.
        page.get_by_role("link", name="GPS").click()

        # Wait for the map element to be visible.
        expect(page.locator("#map")).to_be_visible(timeout=10000)

        # Take a screenshot.
        page.screenshot(path="jules-scratch/verification/gps_page.png")

        print("Screenshot taken successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
        page.screenshot(path="jules-scratch/verification/error.png")

    finally:
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
