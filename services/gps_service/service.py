import asyncio
import json
import sys
import os
import random

from datetime import datetime, timezone

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice
from common.owa_errors import OwaErrors
import common.utils as utils
from nats.aio.msg import Msg


class GpsService(Microservice):
    """
    A microservice for providing GPS data.
    """

    def __init__(self):
        super().__init__("gps_service")
        self.use_owa_hardware = False
        self.gps = None
        self.publisher_task = None
        self.update_pos_counter = 0
        self.no_update_pos_counter = 0
        self.last_payload = {}

    async def _wait_for_owa_service(self, timeout=60.0, retry_delay=2.0):
        """Waits for the OWA service to be ready using a request-reply pattern."""
        self.logger.info("Checking OWA service status...")
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                response = await self.messaging_client.request(
                    "owa.service.status.request",
                    b'',
                    timeout=retry_delay
                )
                status_data = json.loads(response.data)
                if status_data.get("status") == "ready":
                    self.logger.info("OWA service reported status: ready.")
                    return True
                else:
                    self.logger.warning(f"OWA service reported status: {status_data.get('status')}. Retrying...")
            except asyncio.TimeoutError:
                self.logger.warning("Request to OWA service timed out. Retrying...")
            except Exception as e:
                self.logger.error(f"Error requesting OWA status: {e}. Retrying...")

            await asyncio.sleep(retry_delay)

        self.logger.critical("Timed out waiting for OWA service to become ready.")
        return False

    async def _start_logic(self):
        """Starts the GPS service logic."""
        try:
            self.logger.info("Waiting for settings...")
            await self.get_settings()

            if self._shutdown_event.is_set(): return

            self.use_owa_hardware = self.global_settings.get("hardware_platform") == "owa5x"
            self.logger.info(f"GPS Service starting. Hardware platform: {'owa5x' if self.use_owa_hardware else 'generic'}")

            if not await self._wait_for_owa_service():
                await self.stop()
                return

            if self.use_owa_hardware:
                self.logger.info("Initializing real GPS...")
                from common.owa_rtu import Rtu
                from common.owa_io import Io
                from common.owa_gps2 import Gps

                self.logger.info("Initializing Owasys RTU...")
                self.rtu = Rtu()
                self.rtu.initialize()
                self.rtu.start()

                res, val = self.rtu.is_active()
                self.logger.info(f"RTU is_active = {res}, {val}")

                self.logger.info("Initializing Owasys IO...")
                self.io = Io()
                self.io.initialize()
                self.io.start()

                res, val = self.io.is_active()
                self.logger.info(f"IOs is_active = {res}, {val}")

                self.logger.info("Switching GPS power ON...")
                self.io.switch_gps_on_off(1)

                self.logger.info("OWA Initializing real GPS...")
                try:
                    self.gps = Gps()
                    self.gps.gps_init(modem_type="owa5x")
                except Exception as e:
                    self.logger.error(f"Error initializing GPS: {e}", exc_info=True)
                    self.gps = None
            else:
                self.logger.info("Running on a generic platform. Fake GPS data will be used.")

            self.publisher_task = asyncio.create_task(self._gps_publisher_loop())
            self.logger.info("GPS data publisher started.")

            await self.messaging_client.subscribe(
                "gps.get_current_position.request",
                cb=self._handle_get_current_position_request
            )
        except Exception as e:
            self.logger.error(f"An error occurred during GPS service startup: {e}", exc_info=True)
            await self.stop()

    async def _handle_get_current_position_request(self, msg: Msg):
        """Replies with the last known GPS position."""
        self.logger.info(f"Received request for current position on subject: {msg.subject}")
        if msg.reply:
            await self.messaging_client.publish(msg.reply, json.dumps(self.last_payload).encode())
            self.logger.info(f"Replied to {msg.reply} with current position.")

    async def _stop_logic(self):
        """Stops the GPS service logic."""
        self.logger.info("Stopping GPS service...")
        if self.publisher_task and not self.publisher_task.done():
            self.publisher_task.cancel()

        if self.gps and self.use_owa_hardware:
            self.gps.finalize()
            self.logger.info("Real GPS finalized.")

    async def _gps_publisher_loop(self):
        """Periodically publishes GPS data."""
        update_interval = self.settings.get("update_interval", 1)
        while True:
            try:
                await self._publish_gps_data()
                await asyncio.sleep(update_interval)
            except asyncio.CancelledError:
                self.logger.info("GPS publisher loop cancelled.")
                break
            except Exception as e:
                self.logger.error(f"Error in GPS publisher loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    def _generate_fake_sv_data(self):
        sv_in_view = random.randint(8, 12)
        sv_data = []
        for i in range(sv_in_view):
            sv_data.append({
                "SV_Id": i + 1,
                "SV_Elevation": random.randint(0, 90),
                "SV_Azimuth": random.randint(0, 359),
                "SV_SNR": random.randint(10, 50)
            })
        for _ in range(sv_in_view, 64):
            sv_data.append({"SV_Id": 0, "SV_Elevation": 0, "SV_Azimuth": 0, "SV_SNR": 0})
        return {"SV_InView": sv_in_view, "SV": sv_data}

    async def _publish_data_recursively(self, base_subject: str, data: dict, timestamp: float):
        """Recursively publishes nested dictionary data."""
        for key, value in data.items():
            new_subject = f"{base_subject}.{key}"
            if isinstance(value, dict):
                await self._publish_data_recursively(new_subject, value, timestamp)
            # Handle lists, but don't publish the whole list as one value
            elif isinstance(value, list):
                 # Publish list items individually if they are complex objects (dicts)
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        await self._publish_data_recursively(f"{new_subject}.{i}", item, timestamp)
            else:
                try:
                    # Attempt to convert to a numeric type if possible, otherwise keep as is
                    if isinstance(value, (int, float, bool)):
                        numeric_value = value
                    elif isinstance(value, str):
                        try:
                            numeric_value = float(value)
                        except ValueError:
                            numeric_value = value # Keep as string if conversion fails
                    else:
                        numeric_value = str(value) # Convert other types to string

                    payload = {"value": numeric_value, "ts": timestamp}
                    await self.messaging_client.publish(new_subject, json.dumps(payload).encode())
                except Exception as e:
                    self.logger.warning(f"Could not process value for '{new_subject}': {e}")

    async def _publish_gps_data(self):
        """Fetches and publishes GPS data."""
        payload = {}
        if self.gps and self.use_owa_hardware:
            # Logic for real hardware... (omitted for brevity, assume it populates payload)
            pass
        else:
            # Generate fake data for demonstration
            fake_lat = 45.5257585 + random.uniform(-0.001, 0.001)
            fake_lon = 4.9240768 + random.uniform(-0.001, 0.001)
            payload = {
                "geometry": {
                    "coordinates": [fake_lon, fake_lat]
                },
                "properties": {
                    "lastCoord": {
                        "Altitude": random.uniform(150, 250),
                        "Speed": random.uniform(0, 5),
                        "Course": random.uniform(0, 360),
                        "HDOP": random.uniform(0.8, 1.2),
                        "VDOP": random.uniform(1, 1.5),
                        "LatDecimal": fake_lat,
                        "LonDecimal": fake_lon,
                    },
                    "SV": self._generate_fake_sv_data(),
                    "fake": True,
                }
            }

        if payload:
            self.last_payload = payload # Keep for request/reply

            # Get a single timestamp for this update cycle
            timestamp = datetime.now().timestamp()

            # Start the recursive publishing
            await self._publish_data_recursively("gps.data", payload, timestamp)
            self.logger.debug(f"Finished publishing GPS data.")
