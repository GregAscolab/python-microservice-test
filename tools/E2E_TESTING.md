# End-to-End Test for Manager Service

This document describes how to run the end-to-end test for the Manager microservice and its UI.

## Purpose

The test script `tools/test_manager_e2e.py` is designed to provide a full, end-to-end verification of the manager service functionality. It automates the process of:
1.  Starting the necessary infrastructure (NATS messaging server).
2.  Running the entire microservice application stack.
3.  Controlling a web browser to interact with the Manager UI.
4.  Sending commands to the manager service and verifying that the UI updates correctly.

## Prerequisites

Before running the test, you must have the following installed:

1.  **Go**: The test script requires Go to be installed to manage the NATS server. You can check if Go is installed by running `go version`. If not, please install it from the official Go website.

2.  **NATS Server**: The script uses a Go-based NATS server. It can be installed with the following command:
    ```bash
    go install github.com/nats-io/nats-server/v2@latest
    ```

3.  **Python Dependencies**: All required Python packages for the project and for the test script must be installed.
    ```bash
    pip install -r requirements.txt
    pip install playwright
    ```

4.  **Playwright Browsers**: The test script uses Playwright to control a browser. You need to install the necessary browser binaries and their system dependencies.
    ```bash
    # Install system dependencies (for Debian/Ubuntu)
    playwright install-deps
    # Install browser binaries
    playwright install
    ```

## How to Run the Test

Once all prerequisites are met, you can execute the test script from the root of the project directory:

```bash
python tools/test_manager_e2e.py
```

The script will print its progress to the console, including the setup, individual test steps, and teardown.

## What the Test Does

The script performs the following sequence of actions:
1.  Starts a local NATS server.
2.  Starts the main microservice application.
3.  Launches a headless Chromium browser.
4.  Sends a `start_all` command to the manager via NATS.
5.  Navigates the browser to the Manager UI page.
6.  Asserts that all services are shown with a "running" status.
7.  Sends a `stop_service` command for a specific service and asserts that its status updates to "stopped".
8.  Sends a `start_service` command for the same service and asserts it returns to "running".
9.  Sends a `stop_all` command and asserts that all services are shown as "stopped".
10. Shuts down all processes gracefully.

## Known Issues

**As of this commit, the test is failing.**

The script fails during the UI verification step. The root cause appears to be that the browser client is not receiving status updates from the server via the WebSocket, even though logging confirms the server's backend is sending them.

The primary purpose of this commit is to allow for debugging this issue in a different, more complete environment. The page content at the time of failure is printed to the console to aid in debugging.
