import asyncio
import json
from nats.aio.msg import Msg
from common.microservice import Microservice

class SettingsService(Microservice):
    """
    The Settings Management Microservice.
    It loads settings from a JSON file and provides them to other
    microservices via NATS.
    """

    def __init__(self):
        super().__init__("settings_service")
        self.settings_path = "config/settings.json"
        self.all_settings = {}

    async def _load_settings(self):
        """Loads settings from the JSON file."""
        print(f"[{self.service_name}] Loading settings from {self.settings_path}...")
        try:
            with open(self.settings_path, 'r') as f:
                self.all_settings = json.load(f)
            print(f"[{self.service_name}] Settings loaded successfully.")
        except FileNotFoundError:
            print(f"[{self.service_name}] Error: {self.settings_path} not found.")
            self.all_settings = {}
        except json.JSONDecodeError:
            print(f"[{self.service_name}] Error: Could not decode JSON from {self.settings_path}.")
            self.all_settings = {}

    async def _settings_request_handler(self, msg: Msg):
        """
        Handles requests for settings.
        The subject is expected to be 'settings.get.<service_name>' or 'settings.get.all'.
        """
        subject = msg.subject
        reply = msg.reply
        service_key = subject.split('.')[-1]

        if service_key == "all":
            response = self.all_settings
        else:
            response = self.all_settings.get(service_key, {})

        if reply:
            await self.nc.publish(reply, json.dumps(response).encode())
            print(f"[{self.service_name}] Sent settings for '{service_key}' to {reply}")

    async def _start_logic(self):
        """
        Starts the settings service logic.
        Loads settings and subscribes to NATS subjects for settings requests.
        """
        await self._load_settings()

        # Subscribe to requests for all settings
        await self.nc.subscribe("settings.get.all", cb=self._settings_request_handler)
        print(f"[{self.service_name}] Subscribed to 'settings.get.all'")

        # Subscribe to requests for specific service settings
        await self.nc.subscribe("settings.get.*", cb=self._settings_request_handler)
        print(f"[{self.service_name}] Subscribed to 'settings.get.*'")


    async def _stop_logic(self):
        """Stops the settings service logic."""
        # No special cleanup needed for this service
        print(f"[{self.service_name}] Stop logic executed.")
        pass
