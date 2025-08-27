import asyncio
import json
from datetime import datetime
import sys
import os
import cantools

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

    async def _start_logic(self):
        """This is called when the service starts."""
        self.logger.info("Digital Twin service starting up...")
        await self.get_settings()
        self.logger.info(f"My settings: {self.settings}")

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
                self.logger.info(f"Initialized sensor state with {len(self.sensor_state)} signals.")
            except FileNotFoundError:
                self.logger.error(f"DBC file not found at {dbc_file}")
        else:
            self.logger.warning("No dbc_file configured for digital_twin_service.")

        # Subscribe to can_data
        await self.messaging_client.subscribe("can_data", self._handle_can_data)

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
        try:
            data = json.loads(msg.data.decode())
            sensor_name = data.get("name")
            if sensor_name in self.sensor_state:
                self.sensor_state[sensor_name] = data.get("value")
                self.logger.debug(f"Updated sensor {sensor_name} to {data.get('value')}")
        except json.JSONDecodeError:
            self.logger.error("Failed to decode CAN data message")

    async def _publish_data(self):
        update_interval = self.settings.get("update_interval", 1)
        while True:
            try:
                if self.excavator:
                    # Update model and get representation in one call
                    self.excavator.update_from_sensors(self.sensor_state)
                    payload = self.excavator.get_3d_representation()
                    await self.messaging_client.publish(
                        "digital_twin.data",
                        json.dumps(payload).encode()
                    )
                    self.logger.debug(f"Published digital twin data: {payload}")
                    await asyncio.sleep(update_interval)
            except asyncio.CancelledError:
                self.logger.info("Publisher task was cancelled.")
                break

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
