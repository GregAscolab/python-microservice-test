import json
import sys
import os
from datetime import datetime
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

        response_json = json.dumps(response_data, indent=None, separators=(',',':'))

        if reply:
            await self.messaging_client.publish(reply, response_json.encode())
            self.logger.debug(f"Sent settings for '{service_key}' to {reply}")

    def _get_nested_dict_val(self, dict: dict, keys: list):
        for key in keys:
            if type(dict) is list:
                key = int(key)
            else :
                if key not in dict:
                    dict[key] = {}
            dict = dict[key]
        return dict
    
    def _set_nested_dict_val(self, val:int|float|str, dict: dict, keys: list):
        for key in keys:
            if type(dict) is list:
                key = int(key)
            else :
                if key not in dict:
                    dict[key] = {}
            
            if (isinstance(dict[key], int) or isinstance(dict[key], float) or isinstance(dict[key], str)) :
                dict[key] = val
                return True, dict[key]
            else:
                dict = dict[key]
        return False, dict
            


    async def _handle_update_setting_command(self, key: str, value: any):
        """Handles the 'update_setting' command."""
        self.logger.info(f"Received update for setting '{key}' with value '{value}'")

        # Check if setting is read-only
        # if key in self.all_settings[group] and self.all_settings[group][key].get('ro', False):
        #     self.logger.warning(f"Attempted to modify read-only setting: {group}.{key}")
        #     return

        # Try to convert text to number
        try:
            if str(value).isdigit():
                converted_val = int(value)
            else:
                converted_val = float(value)
        except ValueError:
            converted_val = value

        # Extract the list of succesive keys (path) in the object
        list_of_keys = key.split('.')
        # Update the setting
        ret, val = self._set_nested_dict_val(converted_val, self.all_settings, list_of_keys)

        if ret:
            # Persist the changes
            self._save_settings()

            # Broadcast the change to all services
            update_payload = {
                "key": key,
                "value": converted_val
            }
            await self.messaging_client.publish("settings.updated", json.dumps(update_payload, indent=None, separators=(',',':')).encode())
            self.logger.info(f"Broadcasted update for {key}")
        else:
            self.logger.error(f"Impossible to save the key:{key} with value:{value}!")

    async def _handle_import_settings_command(self, data: str):
        """Handles the 'import_settings' command."""
        self.logger.info("Received import settings command.")
        try:
            # Backup the current settings file
            if os.path.exists(self.settings_path):
                timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                backup_path = f"{self.settings_path}.{timestamp}.bak"
                os.rename(self.settings_path, backup_path)
                self.logger.info(f"Backed up current settings to {backup_path}")

            # Write the new settings
            with open(self.settings_path, 'w') as f:
                # The data is expected to be a JSON string, so we parse and dump it
                # to ensure it's well-formed and nicely formatted.
                parsed_data = json.loads(data)
                json.dump(parsed_data, f, indent=4)

            self.logger.info("New settings file written successfully.")

            # Reload settings and notify other services
            await self._load_settings()
            await self.messaging_client.publish("settings.reloaded", b'')
            self.logger.info("Broadcasted settings.reloaded")

        except Exception as e:
            self.logger.error(f"Error importing settings: {e}", exc_info=True)

    async def _handle_load_settings_from_file_command(self, filename: str):
        """Handles the 'load_settings_from_file' command."""
        self.logger.info(f"Received request to load settings from '{filename}'")

        # Security: ensure the file is within the config directory
        config_dir = os.path.abspath("config")
        requested_path = os.path.abspath(os.path.join(config_dir, filename))

        if not requested_path.startswith(config_dir) or not requested_path.endswith('.json'):
            self.logger.warning(f"Attempted to access an unauthorized file: {filename}")
            return

        self.settings_path = os.path.join("config", filename)
        await self._load_settings()
        await self.messaging_client.publish("settings.reloaded", b'')
        self.logger.info(f"Loaded settings from {self.settings_path} and broadcasted settings.reloaded")

    async def _list_config_files_handler(self, msg: Msg):
        """Handles requests for listing available .json config files."""
        reply = msg.reply
        try:
            config_dir = "config"
            files = [f for f in os.listdir(config_dir) if f.endswith('.json') and os.path.isfile(os.path.join(config_dir, f))]
            response = json.dumps(files)
            await self.messaging_client.publish(reply, response.encode())
        except Exception as e:
            self.logger.error(f"Error listing config files: {e}", exc_info=True)
            # Optionally send an error response
            await self.messaging_client.publish(reply, b'[]')

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
        await self.messaging_client.subscribe("settings.list_configs", cb=self._list_config_files_handler)
        self.logger.info("Subscribed to 'settings.get.*' and 'settings.list_configs'")

        self.command_handler.register_command("update_setting", self._handle_update_setting_command)
        self.command_handler.register_command("import_settings", self._handle_import_settings_command)
        self.command_handler.register_command("load_settings_from_file", self._handle_load_settings_from_file_command)
        await self._subscribe_to_commands()

    async def _stop_logic(self):
        self.logger.info("Stop logic executed.")
        pass
