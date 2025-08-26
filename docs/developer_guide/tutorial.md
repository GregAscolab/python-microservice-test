# Tutorial: Creating a New "Dummy" Service

## Introduction

This tutorial will guide you through the process of creating a new microservice from scratch. We will create a `dummy_service` that demonstrates all the core functionalities of a typical service:

-   Inheriting from the `Microservice` base class.
-   Having a configurable setting in `config/settings.json`.
-   Publishing a message to a NATS subject periodically.
-   Responding to a command sent from another service.
-   Displaying its data and being controlled from the web UI.

By the end of this tutorial, you will have a fully functional service that is properly integrated into the rest of the application.

## Step 1: Create the Service Directory and Files

The `manager` discovers services by scanning the `services/` directory. Let's create the folder and the essential Python files for our new service.

In your terminal, from the root of the project, run:

```bash
mkdir services/dummy_service
touch services/dummy_service/__init__.py
touch services/dummy_service/main.py
touch services/dummy_service/service.py
```

-   `services/dummy_service/`: The directory itself, which defines the service's name.
-   `__init__.py`: An empty file that marks the directory as a Python package.
-   `main.py`: The entry point script that the `manager` will execute.
-   `service.py`: The file where our main service logic will reside.

## Step 2: Create the `main.py` Entry Point

This is the boilerplate code that instantiates your service and starts its main loop. The `manager` process will call this script.

Copy the following code into `services/dummy_service/main.py`:

```python
import asyncio
import os
import sys

# Add the project root to the Python path so this script can find other modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import our yet-to-be-created service class
from services.dummy_service.service import DummyService

if __name__ == "__main__":
    # Instantiate the service
    service = DummyService()
    # Start the service's lifecycle
    asyncio.run(service.run())
```

## Step 3: Create the Basic Service Class

Now, let's write the core of our service in `service.py`. It will inherit from `Microservice` and implement the two required abstract methods, `_start_logic` and `_stop_logic`.

Copy the following code into `services/dummy_service/service.py`:

```python
import asyncio
import json
from datetime import datetime
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

class DummyService(Microservice):
    def __init__(self):
        # Call the parent constructor with the official service name
        super().__init__("dummy_service")
        self.counter = 0
        self.publisher_task = None # We'll store our background task here

    async def _start_logic(self):
        """This is called when the service starts."""
        self.logger.info("Dummy service starting up...")
        # We will add more logic here in the next steps.

    async def _stop_logic(self):
        """This is called when the service is shutting down."""
        self.logger.info("Dummy service shutting down...")
        # Ensure our background task is cancelled
        if self.publisher_task:
            self.publisher_task.cancel()
```

At this point, you could run `python main.py`, and the manager would start your service, which would print its startup message and then do nothing.

## Step 4: Add a Custom Setting

Let's make the service's update interval configurable via the central settings file.

Open `config/settings.json` and add a new key for `dummy_service` (make sure to add a comma after the preceding block if necessary):

```json
  "dummy_service": {
    "update_interval": 5
  },
```

Now, modify `service.py` to read this setting during startup.

```python
# In services/dummy_service/service.py, inside the DummyService class

    async def _start_logic(self):
        """This is called when the service starts."""
        self.logger.info("Dummy service starting up...")
        # Get settings from the settings_service
        await self.get_settings()
        # The settings are now available in self.settings
        self.logger.info(f"My settings: {self.settings}")
```

## Step 5: Implement a Periodic Publisher

Now for the main logic. We'll create a background task that periodically increments a counter and publishes it to a NATS subject.

Modify `service.py` to add the publisher task.

```python
# In services/dummy_service/service.py

# ... inside the DummyService class ...
    async def _start_logic(self):
        self.logger.info("Dummy service starting up...")
        await self.get_settings()
        self.logger.info(f"My settings: {self.settings}")

        # Start our publisher as a background task
        self.publisher_task = asyncio.create_task(self._publish_counter())
        self.logger.info("Publisher task started.")

    async def _publish_counter(self):
        # Use the setting we defined, with a default fallback value
        update_interval = self.settings.get("update_interval", 5)
        while True:
            try:
                await asyncio.sleep(update_interval)
                self.counter += 1
                payload = {
                    "message": "Hello from the dummy service!",
                    "count": self.counter,
                    "timestamp": datetime.now().isoformat()
                }
                # Publish the data to a unique NATS subject
                await self.messaging_client.publish(
                    "dummy.data",
                    json.dumps(payload).encode()
                )
                self.logger.info(f"Published message: {payload}")
            except asyncio.CancelledError:
                self.logger.info("Publisher task was cancelled.")
                break
```

## Step 6: Add a Command Handler

To make our service interactive, let's add a command to reset the counter.

Modify `service.py` again to register and implement the command handler.

```python
# In services/dummy_service/service.py

# ... inside the DummyService class ...
    async def _start_logic(self):
        # ... (existing code from previous steps) ...
        await self.get_settings()

        # 1. Register the command
        self.command_handler.register_command("reset_counter", self._handle_reset_counter)
        # 2. Subscribe to the command subject
        await self._subscribe_to_commands()

        self.publisher_task = asyncio.create_task(self._publish_counter())
        self.logger.info("Publisher task started.")

    async def _handle_reset_counter(self):
        self.logger.info("Counter reset command received!")
        self.counter = 0
        # It's good practice to return a confirmation
        return {"status": "ok", "message": "Counter has been reset to 0"}

    # The _publish_counter method remains the same
    async def _publish_counter(self):
        # ...
```

## Step 7: Integrate with the UI

Finally, let's display the dummy data on the UI and add a button to call our new command. This involves creating a new JavaScript module that follows the application's frontend patterns and modifying the main HTML template to include the new page and script.

**1. Create the JavaScript Module**

Create a new file at `services/ui_service/frontend/static/js/dummy.js`. This script will be responsible for initializing and cleaning up the "Dummy" page. It will subscribe to NATS subjects and handle user interaction.

Copy the following code into `dummy.js`. Note how it uses the `ConnectionManager` and exports `initDummyPage` and `cleanupDummyPage` functions.

```javascript
import ConnectionManager from './connection_manager.js';

// Module-level state variables
let dummySub;
let dummyDataElement;
let resetButton;

/**
 * Event handler for the reset button click.
 */
function handleResetClick() {
    console.log('Sending reset_counter command to dummy_service...');
    const command = {
        command: 'reset_counter'
    };
    // Publish the command using the shared ConnectionManager
    ConnectionManager.publish('commands.dummy_service', command);
}

/**
 * Initializes the Dummy page elements and subscriptions.
 */
function initDummyPage() {
    console.log("Initializing Dummy page...");

    // 1. Get references to UI elements
    dummyDataElement = document.getElementById('dummy-data');
    resetButton = document.getElementById('reset-dummy-counter');

    if (!dummyDataElement || !resetButton) {
        console.error("Dummy page UI elements not found! Cannot initialize page.");
        return;
    }

    // 2. Set up NATS subscription for dummy data
    ConnectionManager.subscribe('dummy.data', (m) => {
        const data = ConnectionManager.jsonCodec.decode(m.data);
        if (dummyDataElement) {
            // Update the UI with the received data
            dummyDataElement.textContent = JSON.stringify(data, null, 2);
        }
    }).then(sub => {
        // Store the subscription object so we can unsubscribe later
        dummySub = sub;
    });

    // 3. Add event listener for the reset button
    resetButton.addEventListener('click', handleResetClick);
}

/**
 * Cleans up resources used by the Dummy page.
 */
function cleanupDummyPage() {
    console.log("Cleaning up Dummy page...");

    // 1. Unsubscribe from NATS to prevent memory leaks
    if (dummySub) {
        dummySub.unsubscribe();
        dummySub = null;
    }

    // 2. Remove event listener from the button
    if (resetButton) {
        resetButton.removeEventListener('click', handleResetClick);
        resetButton = null;
    }

    // 3. Clear references to DOM elements
    dummyDataElement = null;
}

// Expose the init and cleanup functions to the global window object
// so that app.js can call them when navigating between pages.
window.initDummyPage = initDummyPage;
window.cleanupDummyPage = cleanupDummyPage;
```

**2. Modify the Main HTML Template**

Now, open `services/ui_service/frontend/templates/index.html` to add the new navigation link and the content placeholder for our page.

-   **Add a new link to the sidebar navigation.** Find the `<ul>` inside the `<nav class="sidebar">` and add a new list item for "Dummy":
    ```html
    <!-- ... other list items ... -->
    <li><a href="/manager">Manager</a></li>
    <li><a href="/dummy">Dummy</a></li>
    ```

-   **Add the content `div` for the new page.** Inside the `<main id="content">` element, add the HTML structure for the dummy page. It must have the `page-content` class and a unique `id` that matches the link's `href` (e.g., `page-dummy`).
    ```html
    <!-- ... other page divs ... -->
    <div id="page-manager" class="page-content" style="display: none;">
        <!-- ... manager content ... -->
    </div>

    <div id="page-dummy" class="page-content" style="display: none;">
        <h2>Dummy Service</h2>
        <p>This tab displays live data from the dummy_service and allows interaction.</p>
        <button id="reset-dummy-counter" class="btn btn-warning mb-3">Reset Counter</button>
        <pre><code id="dummy-data" class="text-white">Waiting for data...</code></pre>
    </div>
    ```

-   **Include the new JavaScript file.** At the bottom of the `<body>`, add a script tag for `dummy.js`. It's important to load it as a `module`.
    ```html
    <!-- ... other page-specific scripts ... -->
    <script type="module" src="/static/js/manager.js"></script>
    <script type="module" src="/static/js/dummy.js"></script>
    ```

## Conclusion

You have now successfully created a new service and integrated it into the application, following the established frontend and backend patterns.

Run the application with `python main.py`. The `dummy_service` will be discovered and started automatically. Open the web UI at `http://localhost:8000`, navigate to the "Dummy" page using the sidebar link, and you will see the live counter data. Clicking the "Reset Counter" button will send a command to the service and reset the count to zero. Congratulations!
