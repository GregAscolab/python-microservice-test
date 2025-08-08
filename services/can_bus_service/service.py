import asyncio
import json
import time
import sys
import os
import cantools
import can

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

class CanBusService(Microservice):
    """
    The CAN Bus data decoding and logging microservice.
    """

    def __init__(self):
        super().__init__("can_bus_service")
        self.can_bus = None
        self.db = None
        self.listener_task = None

    async def _start_logic(self):
        """
        Acquires settings, initializes the CAN bus, and starts the listener.
        """
        self.logger.info("Waiting for settings...")
        await self.get_settings()

        # If shutdown is signaled during settings retrieval, exit gracefully.
        if self._shutdown_event.is_set():
            return

        self.logger.info("Initializing...")

        can_settings = self.settings
        interface = can_settings.get("interface", "virtual")
        channel = can_settings.get("channel", "vcan0")
        bitrate = can_settings.get("bitrate", 500000)
        dbc_file = can_settings.get("dbc_file")

        if not dbc_file:
            self.logger.error("'dbc_file' not specified in settings. Service will not start CAN listener.")
            return

        try:
            self.logger.info(f"Loading DBC file from {dbc_file}...")
            self.db = cantools.db.load_file(dbc_file)
        except FileNotFoundError:
            self.logger.error(f"DBC file not found at {dbc_file}")
            return

        try:
            self.logger.info(f"Initializing CAN bus: interface={interface}, channel={channel}")
            self.can_bus = can.interface.Bus(channel=channel, bustype=interface, bitrate=bitrate)
        except Exception as e:
            self.logger.error(f"Error initializing CAN bus: {e}", exc_info=True)
            return

        # Subscribe to commands after we have a NATS connection.
        await self._subscribe_to_commands()

        self.listener_task = asyncio.create_task(self._message_listener())
        self.logger.info("CAN message listener started.")

    async def _stop_logic(self):
        """
        Stops the message listener and shuts down the CAN bus.
        """
        self.logger.info("Stopping...")
        if self.listener_task and not self.listener_task.done():
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass

        if self.can_bus:
            self.can_bus.shutdown()
            self.logger.info("CAN bus shut down.")

    async def _message_listener(self):
        """
        Listens for CAN messages, decodes them, and publishes them.
        """
        reader = can.AsyncBufferedReader()
        notifier = can.Notifier(self.can_bus, [reader])

        try:
            while True:
                msg = await reader.get_message()
                try:
                    decoded_message = self.db.decode_message(msg.arbitration_id, msg.data)

                    for signal_name, signal_value in decoded_message.items():
                        payload = {
                            'name': signal_name,
                            'value': round(float(signal_value), 3),
                            'ts': time.time()
                        }
                        payload_json = json.dumps(payload).encode()
                        await self.messaging_client.publish("can_data", payload_json)
                        self.logger.debug(f"Published decoded signal: {payload}")

                except KeyError:
                    pass
                except Exception as e:
                    self.logger.error(f"Error decoding or publishing message: {e}", exc_info=True)

        except asyncio.CancelledError:
            self.logger.info("Message listener cancelled.")
        finally:
            notifier.stop()
