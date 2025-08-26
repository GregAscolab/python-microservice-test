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
        await self.get_settings()
        self.logger.info(f"My settings: {self.settings}")

        # 1. Register the command
        self.command_handler.register_command("reset_counter", self._handle_reset_counter)
        # 2. Subscribe to the command subject
        await self._subscribe_to_commands()

        # Start our publisher as a background task
        self.publisher_task = asyncio.create_task(self._publish_counter())
        self.logger.info("Publisher task started.")

    async def _stop_logic(self):
        """This is called when the service is shutting down."""
        self.logger.info("Dummy service shutting down...")
        # Ensure our background task is cancelled
        if self.publisher_task:
            self.publisher_task.cancel()

    async def _handle_reset_counter(self):
        self.logger.info("Counter reset command received!")
        self.counter = 0
        # It's good practice to return a confirmation
        return {"status": "ok", "message": "Counter has been reset to 0"}

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
