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

Finally, let's display the dummy data on the UI and add a button to call our new command.

**1. Create a new JavaScript file** for our service's UI logic. Create the file `services/ui_service/frontend/static/js/dummy.js` and add this code:

```javascript
document.addEventListener('DOMContentLoaded', function() {
    const nats = window.nats;
    const dummyDataElement = document.getElementById('dummy-data');
    const resetButton = document.getElementById('reset-dummy-counter');

    // 1. Subscribe to the data subject from our dummy service
    nats.subscribe('dummy.data', (msg) => {
        const data = JSON.parse(new TextDecoder().decode(msg.data));
        dummyDataElement.textContent = JSON.stringify(data, null, 2);
    });

    // 2. Add a click listener for our reset button
    resetButton.addEventListener('click', () => {
        // Construct the command payload
        const command = {
            command: 'reset_counter'
            // No arguments needed for this command
        };
        // Publish the command to the dummy service's command subject
        nats.publish('commands.dummy_service', JSON.stringify(command));
        console.log('Sent reset_counter command to dummy_service');
    });
});
```

**2. Modify the main HTML file** to include our new UI elements. Open `services/ui_service/frontend/templates/index.html`.

-   **Add a new tab link** in the left-hand navigation list (the `div` with `id="v-pills-tab"`):
    ```html
    <a class="nav-link" id="v-pills-dummy-tab" data-bs-toggle="pill" href="#v-pills-dummy" role="tab" aria-controls="v-pills-dummy" aria-selected="false">Dummy</a>
    ```

-   **Add the content pane for the new tab** inside the `div` with `id="v-pills-tabContent"`:
    ```html
    <div class="tab-pane fade" id="v-pills-dummy" role="tabpanel" aria-labelledby="v-pills-dummy-tab">
        <h3>Dummy Service</h3>
        <p>This tab displays live data from the dummy_service and allows interaction.</p>
        <button id="reset-dummy-counter" class="btn btn-warning mb-3">Reset Counter</button>
        <pre><code id="dummy-data" class="text-white">Waiting for data...</code></pre>
    </div>
    ```

-   **Include the new JavaScript file** at the very bottom of the `<body>` section, with the other scripts:
    ```html
    <script src="{{ url_for('static', path='/js/dummy.js') }}"></script>
    ```

## Conclusion

You have now successfully created and integrated a new service.

Run the application with `python main.py`. The `dummy_service` will be discovered and started automatically. Open the web UI at `http://localhost:8000`, navigate to the "Dummy" tab, and you will see the live counter data. Clicking the "Reset Counter" button will send a command to the service and reset the count to zero. Congratulations!
