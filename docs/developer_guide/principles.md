# Core Principles for Developers

## 1. Introduction

This document outlines the fundamental principles and patterns to follow when developing a new microservice for this application. Adhering to these conventions ensures that your new service will integrate smoothly into the existing architecture, be manageable by the `manager` service, and communicate correctly with other services.

## 2. The `Microservice` Base Class

Every service in this application **must** inherit from the `common.microservice.Microservice` abstract base class. This class provides a significant amount of boilerplate functionality out-of-the-box, including:

-   **Service Naming and Logging:** Automatically sets up a structured logger (`self.logger`) that logs to both the console and a file (`logs/<service_name>.log`).
-   **Settings Management:** Provides the `self.get_settings()` coroutine to automatically and safely retrieve configuration from the `settings_service`.
-   **NATS Connection:** Manages the connection and disconnection to the NATS server via the `self.messaging_client` object.
-   **Graceful Shutdown:** Handles operating system signals (`SIGINT`, `SIGTERM`) to trigger a graceful shutdown, allowing your service to clean up resources.
-   **Command Handling:** Includes a `self.command_handler` instance (`common.CommandHandler`) to easily register and handle commands sent from other services.

## 3. Abstract Methods You Must Implement

When you inherit from `Microservice`, you are required to implement two abstract methods:

-   `async def _start_logic(self):`
    This is where the main logic of your service begins. This method is called by the base class's `run()` method. Your implementation should typically:
    1.  Call `await self.get_settings()` to fetch configuration.
    2.  Register any command handlers using `self.command_handler.register_command(...)`.
    3.  Call `await self._subscribe_to_commands()` if you registered any commands.
    4.  Subscribe to any other NATS subjects your service needs to listen to.
    5.  Start any background tasks using `asyncio.create_task()`.

-   `async def _stop_logic(self):`
    This is where you clean up all resources used by your service. This method is called during a graceful shutdown. Your implementation must:
    1.  Cancel any background tasks created in `_start_logic`.
    2.  Close any open file handles or network connections.
    3.  Perform any other necessary cleanup before the service exits.

## 4. Service Discovery

The `manager` service automatically discovers any new service at startup. For a directory to be recognized as a valid, runnable service, it must meet these criteria:

1.  It **must** be a subdirectory inside the top-level `services/` directory.
2.  The directory name becomes the official name of the service (e.g., `services/my_new_service` means the service is named `my_new_service`). This name is used for logging, settings, and NATS subjects.
3.  It **must** contain a `main.py` file, which serves as the entry point for the `manager` to start the service process.

## 5. The `main.py` Entry Point

Every service directory must contain a `main.py` file. The purpose of this file is simply to instantiate your service class and call its `run()` method. The `run()` method is defined in the base class and contains the main application loop.

A typical `main.py` looks like this:

```python
# In: services/my_new_service/main.py
import asyncio
import os
import sys

# This boilerplate allows the script to find the 'common' and 'services' modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import your service class from its file (e.g., service.py)
from services.my_new_service.service import MyNewService

if __name__ == "__main__":
    service = MyNewService()
    # The run() method starts the service lifecycle
    asyncio.run(service.run())
```

## 6. Communication via NATS

-   **No Direct Communication:** Services must never communicate directly with each other (e.g., via HTTP requests or direct function calls). All inter-service communication **must** go through the NATS message bus.
-   **Use the Client:** Interact with NATS using the provided client: `self.messaging_client`.
-   **Follow Naming Conventions:** Adhere to the subject naming conventions outlined in `docs/architecture/communication.md`. This is critical for maintainability.
-   **Publish/Subscribe for Events:** Use `self.messaging_client.publish()` to broadcast data or events that multiple services might be interested in (e.g., `gps.data`).
-   **Request/Reply for Queries:** Use `self.messaging_client.request()` when your service needs a direct response from another service (e.g., getting settings).
-   **Commands for Actions:** To make your service controllable, register functions with `self.command_handler` and subscribe to your command subject. This allows other services to trigger actions in your service.
