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
    It loads settings from a file, serves them to other services,
    handles update requests, persists changes, and broadcasts updates.
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
            self.logger.error(f"'{self.settings_path}' not found. Starting with empty settings.")
            self.all_settings = {}
        except json.JSONDecodeError:
            self.logger.error(f"Could not decode JSON from '{self.settings_path}'. Starting with empty settings.")
            self.all_settings = {}

    def _save_settings(self):
        """Saves the current settings to the JSON file."""
        self.logger.info(f"Saving settings to {self.settings_path}...")
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.all_settings, f, indent=4)
            self.logger.info("Settings saved successfully.")
        except IOError as e:
            self.logger.error(f"Could not save settings to file: {e}")

    async def _settings_request_handler(self, msg: Msg):
        """Handles read requests for settings."""
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

    async def _handle_update_setting_command(self, group: str, key: str, value: any):
        """Handles the 'update_setting' command."""
        self.logger.info(f"Received update for setting '{group}.{key}' with value '{value}'")

        if group not in self.all_settings:
            self.all_settings[group] = {}

        # Check if setting is read-only
        if key in self.all_settings[group] and self.all_settings[group][key].get('ro', False):
            self.logger.warning(f"Attempted to modify read-only setting: {group}.{key}")
            return

        # Update the setting
        if key not in self.all_settings[group]:
             self.all_settings[group][key] = {}
        self.all_settings[group][key]['value'] = value

        # Persist the changes
        self._save_settings()

        # Broadcast the change to all services
        update_payload = {
            "group": group,
            "key": key,
            "value": value
        }
        await self.messaging_client.publish("settings.updated", json.dumps(update_payload).encode())
        self.logger.info(f"Broadcasted update for {group}.{key}")

    async def _start_logic(self):
        """
        Connects, loads settings, and subscribes to requests and commands.
        """
        await self._load_settings()

        if not await self.connect():
            self.logger.error("Could not connect to NATS, shutting down.")
            await self.stop()
            return

        # Register handlers
        self.logger.info("Subscribing to settings requests...")
        await self.messaging_client.subscribe("settings.get.*", cb=self._settings_request_handler)
        self.logger.info("Subscribed to 'settings.get.*'")

        self.command_handler.register_command("update_setting", self._handle_update_setting_command)
        await self._subscribe_to_commands()

    async def _stop_logic(self):
        self.logger.info("Stop logic executed.")
        pass
