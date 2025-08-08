import json
import sys
import os
from nats.aio.msg import Msg

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

class SettingsService(Microservice):
    """
    The Settings Management Microservice.
    """

    def __init__(self):
        super().__init__("settings_service")
        self.settings_path = "config/settings.json"
        self.all_settings = {}

    async def _load_settings(self):
        """Loads settings from the JSON file."""
        self.logger.info(f"Loading settings from {self.settings_path}...")
        try:
            with open(self.settings_path, 'r') as f:
                self.all_settings = json.load(f)
            self.logger.info("Settings loaded successfully.")
        except FileNotFoundError:
            self.logger.error(f"{self.settings_path} not found.")
            self.all_settings = {}
        except json.JSONDecodeError:
            self.logger.error(f"Could not decode JSON from {self.settings_path}.")
            self.all_settings = {}

    async def _settings_request_handler(self, msg: Msg):
        """
        Handles requests for settings.
        """
        subject = msg.subject
        reply = msg.reply
        service_key = subject.split('.')[-1]

        if service_key == "all":
            response_data = self.all_settings
        else:
            response_data = self.all_settings.get(service_key, {})

        response_json = json.dumps(response_data)

        if reply:
            await self.messaging_client.publish(reply, response_json.encode())
            self.logger.debug(f"Sent settings for '{service_key}' to {reply}")

    async def _start_logic(self):
        """
        Connects to the messaging bus, loads its own settings from a file,
        and subscribes to handle settings requests from other services.
        """
        await self._load_settings()

        # The settings service must connect to NATS to serve others.
        # It retries internally until successful.
        if not await self.connect():
            self.logger.error("Could not connect to NATS, shutting down.")
            await self.stop()
            return

        self.logger.info("Subscribing to settings requests...")
        await self.messaging_client.subscribe("settings.get.*", cb=self._settings_request_handler)
        self.logger.info("Subscribed to 'settings.get.*'")

        # Also subscribe to the commands for this service
        await self._subscribe_to_commands()

    async def _stop_logic(self):
        """Stops the settings service logic."""
        self.logger.info("Stop logic executed.")
        pass
