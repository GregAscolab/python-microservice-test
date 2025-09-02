import unittest
import asyncio
import os
import sys
import json
from unittest.mock import patch, MagicMock, AsyncMock

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.settings_service.service import SettingsService

class TestSettingsService(unittest.TestCase):

    def setUp(self):
        """Set up a new SettingsService instance and a temporary settings file."""
        self.service = SettingsService()
        self.service.logger.disabled = True

        # Create a dummy settings file
        self.test_settings_path = "config/test_settings.json"
        self.service.settings_path = self.test_settings_path
        self.initial_settings = {
            "compute_service": {
                "ui_publish_interval": 1.0,
                "computations": [],
                "triggers": []
            },
            "global": {
                "some_key": "some_value"
            }
        }
        with open(self.test_settings_path, 'w') as f:
            json.dump(self.initial_settings, f, indent=4)

        # Load the initial settings into the service instance
        asyncio.run(self.service._load_settings())

    def tearDown(self):
        """Remove the temporary settings file."""
        if os.path.exists(self.test_settings_path):
            os.remove(self.test_settings_path)

    def test_update_setting_block_command(self):
        """Test that the update_setting_block command can save a complex object."""

        new_computations = [
            {"source_signal": "can.speed", "computation_type": "RunningAverage", "output_name": "speed_avg"}
        ]

        # Mock the save and publish methods so we don't interact with files or NATS
        self.service._save_settings = MagicMock()
        self.service.messaging_client = MagicMock()
        self.service.messaging_client.publish = AsyncMock()

        async def run_test():
            await self.service._handle_update_setting_block_command(
                key="compute_service.computations",
                value=new_computations
            )

            # 1. Verify that the in-memory settings were updated
            self.assertEqual(
                self.service.all_settings['compute_service']['computations'],
                new_computations
            )

            # 2. Verify that the settings were saved to disk
            self.service._save_settings.assert_called_once()

            # 3. Verify that the update was broadcast
            self.service.messaging_client.publish.assert_called_once()

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
