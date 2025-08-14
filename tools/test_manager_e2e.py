import asyncio
import subprocess
import sys
import os
import time
import nats
from playwright.async_api import async_playwright, Page, Browser, Playwright

# Ensure the project root is in the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class ManagerE2ETest:
    def __init__(self):
        self.nats_server_process: subprocess.Popen = None
        self.app_process: subprocess.Popen = None
        self.nats_client: nats.NATS = None
        self.playwright: Playwright = None
        self.browser: Browser = None
        self.page: Page = None

    async def setup(self):
        """Starts the NATS server, the main application, and the browser."""
        print("--- Setting up E2E test environment ---")

        # Start NATS server
        nats_server_path = os.path.expanduser("~/go/bin/nats-server")
        if not os.path.exists(nats_server_path):
            raise FileNotFoundError("NATS server not found. Please run `go install github.com/nats-io/nats-server/v2@latest`")

        print("Starting NATS server...")
        self.nats_server_process = subprocess.Popen([nats_server_path, "-p", "4222"])
        await asyncio.sleep(2) # Give it a moment to start

        # Start the main application
        print("Starting main application...")
        main_script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'main.py'))
        self.app_process = subprocess.Popen([sys.executable, main_script_path])
        await asyncio.sleep(5) # Give services time to start up

        # Connect NATS client
        print("Connecting NATS client for test commands...")
        self.nats_client = await nats.connect("nats://localhost:4222")

        # Start Playwright
        print("Starting Playwright...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()

    async def teardown(self):
        """Stops all background processes."""
        print("\n--- Tearing down E2E test environment ---")

        if self.browser:
            await self.browser.close()
            print("Browser closed.")
        if self.playwright:
            await self.playwright.stop()
            print("Playwright stopped.")

        if self.nats_client:
            await self.nats_client.close()
            print("NATS client disconnected.")

        if self.app_process:
            self.app_process.terminate()
            self.app_process.wait()
            print("Main application terminated.")

        if self.nats_server_process:
            self.nats_server_process.terminate()
            self.nats_server_process.wait()
            print("NATS server terminated.")

    async def get_service_status(self, service_name: str) -> str:
        """Uses Playwright to find a service card and return its status."""
        try:
            card_selector = f"//h2[text()='{service_name}']/ancestor::div[contains(@class, 'bg-white')]"
            # Wait for the card itself to be visible first, with a generous timeout.
            await self.page.wait_for_selector(card_selector, timeout=15000)
            card = self.page.locator(card_selector)

            status_element = card.locator("span.rounded-full")
            await status_element.wait_for(timeout=5000) # Wait for the status span to be ready
            status = await status_element.inner_text()
            return status.lower()
        except Exception as e:
            print(f"Error getting status for {service_name}: {e}")
            print("Page content on failure:")
            print(await self.page.content())
            return "not_found"

    async def run_tests(self):
        """Runs the actual test cases."""
        print("\n--- Running tests ---")

        # 1. Start All command
        print("\n[TEST] Sending 'start_all' command...")
        await self.nats_client.publish("commands.manager", b'{"command": "start_all"}')
        print("  - Waiting for services to start...")
        await asyncio.sleep(8) # Give all services ample time to start

        # 2. Navigate to UI and check initial running state
        print("\n[TEST] Navigating to UI and checking running states...")
        await self.page.goto("http://localhost:8000/manager")
        await asyncio.sleep(2) # Wait for page to load and connect WebSocket

        running_services = ["settings_service", "ui_service", "can_bus_service", "gps_service", "owa_service"]
        for service in running_services:
            status = await self.get_service_status(service)
            assert status == "running", f"Expected {service} to be running, but it was {status}"
            print(f"  - {service} is running: PASSED")

        # 3. Stop One Service
        print("\n[TEST] Sending 'stop_service' for 'gps_service'...")
        await self.nats_client.publish("commands.manager", b'{"command": "stop_service", "service_name": "gps_service"}')
        await asyncio.sleep(3)

        stop_one_gps_status = await self.get_service_status("gps_service")
        assert stop_one_gps_status == "stopped", f"Expected gps_service to be stopped, but it was {stop_one_gps_status}"
        print("  - gps_service is stopped: PASSED")

        # 4. Start One Service
        print("\n[TEST] Sending 'start_service' for 'gps_service'...")
        await self.nats_client.publish("commands.manager", b'{"command": "start_service", "service_name": "gps_service"}')
        await asyncio.sleep(3)

        start_one_gps_status = await self.get_service_status("gps_service")
        assert start_one_gps_status == "running", f"Expected gps_service to be running, but it was {start_one_gps_status}"
        print("  - gps_service is running: PASSED")

        # 5. Stop All
        print("\n[TEST] Sending 'stop_all' command...")
        await self.nats_client.publish("commands.manager", b'{"command": "stop_all"}')
        await asyncio.sleep(5)

        for service in running_services:
            status = await self.get_service_status(service)
            assert status == "stopped", f"Expected {service} to be stopped, but it was {status}"
            print(f"  - {service} is stopped: PASSED")

        print("\n--- All tests passed! ---")

async def main():
    test_runner = ManagerE2ETest()
    try:
        await test_runner.setup()
        await test_runner.run_tests()
    except Exception as e:
        print(f"An error occurred during the test run: {e}", file=sys.stderr)
    finally:
        await test_runner.teardown()

if __name__ == "__main__":
    asyncio.run(main())
