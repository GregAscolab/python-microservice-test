from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Capture console logs
        page.on('console', lambda msg: print(f"Browser console: {msg.text}"))

        try:
            # Navigate to the GPS page
            page.goto("http://localhost:8000/gps", timeout=10000)

            # Wait for the map and chart to be rendered
            page.wait_for_selector("#map", state="visible", timeout=5000)
            page.wait_for_selector("#skyviewChart", state="visible", timeout=5000)

            # Wait for a short period to allow data to arrive via WebSocket
            print("Waiting for WebSocket data...")
            page.wait_for_timeout(5000) # Increased wait time

            # Take a screenshot
            screenshot_path = "jules-scratch/verification/gps_page.png"
            page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    run()
