import asyncio
import json
from datetime import datetime
import sys
import os
import cantools
import logging

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice
from services.digital_twin_service.excavator_model import Excavator

class DigitalTwinService(Microservice):
    def __init__(self):
        # Call the parent constructor with the official service name
        super().__init__("digital_twin_service")
        self.publisher_task = None
        self.excavator = None
        self.db = None
        self.sensor_state = {}
        # self.logger.setLevel(logging.DEBUG)
        # for handler in self.logger.handlers:
        #     handler.setLevel(logging.DEBUG)

    async def _start_logic(self):
        """This is called when the service starts."""
        self.logger.info("Digital Twin service starting up...")
        await self.get_settings()

        self.excavator = Excavator(
            self.settings.get("excavator", {}),
            self.settings.get("signal_mapping", {})
        )

        # Load DBC file to initialize sensor state
        if dbc_file := self.settings.get("dbc_file"):
            try:
                self.logger.info(f"Loading DBC file from {dbc_file}...")
                self.db = cantools.db.load_file(dbc_file)
                for message in self.db.messages:
                    for signal in message.signals:
                        self.sensor_state[signal.name] = 0
                        # if signal.name == "PF_BOOM_PFAngGF":
                        #     self.logger.info(f"PF_BOOM_PFAngGF exist <<<<<<")
                self.logger.info(f"Initialized sensor state with {len(self.sensor_state)} signals.")
            except FileNotFoundError:
                self.logger.error(f"DBC file not found at {dbc_file}")
        else:
            self.logger.warning("No dbc_file configured for digital_twin_service.")

        # Subscribe to all CAN data signals
        await self.messaging_client.subscribe("can.data.*", self._handle_can_data)
        self.logger.info("Subscribed to all CAN data signals via 'can.data.*'")

        self.command_handler.register_command("get_height", self._handle_get_height)
        self.command_handler.register_command("get_radius", self._handle_get_radius)
        await self._subscribe_to_commands()

        # Start our publisher as a background task
        self.publisher_task = asyncio.create_task(self._publish_data())
        self.logger.info("Publisher task started.")

    async def _stop_logic(self):
        """This is called when the service is shutting down."""
        self.logger.info("Digital Twin service shutting down...")
        if self.publisher_task:
            self.publisher_task.cancel()

    async def _handle_can_data(self, msg):
        """Handles incoming CAN data messages and updates the internal sensor state."""
        try:
            # The sensor name is the last part of the subject, e.g., "can.data.EngineSpeed" -> "EngineSpeed"
            sensor_name = msg.subject.split('.')[-1]

            if sensor_name in self.sensor_state:
                # The new payload is a JSON object with a "value" key
                data = json.loads(msg.data.decode())
                value = data.get("value")
                if value is not None:
                    self.sensor_state[sensor_name] = value
                    self.logger.debug(f"Updated sensor {sensor_name} to {value}")
                else:
                    self.logger.warning(f"Received message for {sensor_name} but 'value' key was missing.")
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON from subject '{msg.subject}'")
        except IndexError:
            self.logger.error(f"Could not extract sensor name from subject '{msg.subject}'")
        except Exception as e:
            self.logger.error(f"Error handling CAN data for subject '{msg.subject}': {e}", exc_info=True)

    async def _publish_data_recursively(self, base_subject: str, data: dict, timestamp: float):
        """Recursively publishes nested dictionary data."""
        for key, value in data.items():
            new_subject = f"{base_subject}.{key}"
            if isinstance(value, dict):
                await self._publish_data_recursively(new_subject, value, timestamp)
            else:
                try:
                    # Ensure value is a float for consistency
                    numeric_value = float(value)
                    payload = {"value": numeric_value, "ts": timestamp}
                    await self.messaging_client.publish(new_subject, json.dumps(payload).encode())
                except (ValueError, TypeError):
                    self.logger.warning(f"Could not convert value for '{new_subject}' to float. Skipping.")

    async def _publish_data(self):
        update_interval = self.settings.get("update_interval", 1)
        while True:
            try:
                if self.excavator:
                    # Update model and get its data representation
                    self.excavator.update_from_sensors(self.sensor_state)
                    model_data = self.excavator.get_3d_representation()

                    # Get a single timestamp for this entire update cycle
                    timestamp = datetime.now().timestamp()

                    # Recursively publish all data points
                    await self._publish_data_recursively("digital_twin.data", model_data, timestamp)

                    self.logger.debug("Finished publishing digital twin data.")

                await asyncio.sleep(update_interval)
            except asyncio.CancelledError:
                self.logger.info("Publisher task was cancelled.")
                break
            except Exception as e:
                self.logger.error(f"Error in publisher loop: {e}", exc_info=True)
                await asyncio.sleep(5) # Avoid fast error loops

    async def _handle_get_height(self):
        if self.excavator:
            self.excavator.update_from_sensors(self.sensor_state)
            return {"height": self.excavator.get_height()}
        return {"error": "Excavator model not initialized"}

    async def _handle_get_radius(self):
        if self.excavator:
            self.excavator.update_from_sensors(self.sensor_state)
            return {"radius": self.excavator.get_radius()}
        return {"error": "Excavator model not initialized"}
