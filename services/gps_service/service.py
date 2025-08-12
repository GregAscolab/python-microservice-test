import asyncio
import json
import sys
import os
import random

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice
from nats.aio.msg import Msg

if sys.platform == 'linux':
    from common.owa_gps2 import Gps
    import common.utils as utils

class GpsService(Microservice):
    """
    A microservice for providing GPS data.
    """

    def __init__(self):
        super().__init__("gps_service")
        self.hardware_ready = asyncio.Event()
        self.use_owa_hardware = False
        self.gps = None
        self.publisher_task = None

    async def _on_hardware_status(self, msg: Msg):
        """Callback for receiving hardware status messages."""
        try:
            data = json.loads(msg.data)
            if data.get("status") == "ready":
                self.logger.info("Received hardware ready signal. Proceeding with GPS initialization.")
                self.hardware_ready.set()
        except json.JSONDecodeError:
            self.logger.error("Failed to decode hardware status message.")

    async def _start_logic(self):
        """Starts the GPS service logic."""
        try:
            self.logger.info("Waiting for settings...")
            await self.get_settings()

            if self._shutdown_event.is_set(): return

            self.use_owa_hardware = self.settings.get("global", {}).get("hardware_platform") == "owa5x"
            self.logger.info(f"GPS Service starting. Hardware platform: {'owa5x' if self.use_owa_hardware else 'generic'}")

            self.logger.info("Subscribing to OWA hardware status...")
            await self.messaging_client.subscribe("owa.status", cb=self._on_hardware_status)

            try:
                self.logger.info("Waiting for OWA hardware to be ready...")
                await asyncio.wait_for(self.hardware_ready.wait(), timeout=60.0)
            except asyncio.TimeoutError:
                self.logger.critical("Timed out waiting for OWA hardware. GPS service will not start.")
                return

            if self.use_owa_hardware:
                self.logger.info("Initializing real GPS...")
                try:
                    self.gps = Gps(nats=self.messaging_client)
                    self.gps.gps_init(modem_type="owa5x")
                except Exception as e:
                    self.logger.error(f"Error initializing GPS: {e}", exc_info=True)
                    self.gps = None
            else:
                self.logger.info("Running on a generic platform. Fake GPS data will be used.")

            self.publisher_task = asyncio.create_task(self._gps_publisher_loop())
            self.logger.info("GPS data publisher started.")
        except Exception as e:
            self.logger.error(f"An error occurred during GPS service startup: {e}", exc_info=True)
            # Ensure the service stops if startup fails
            await self.stop()


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
        while True:
            try:
                await self._publish_gps_data()
                await asyncio.sleep(1)
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
        # Pad with empty data to match the structure
        for _ in range(sv_in_view, 64):
            sv_data.append({"SV_Id": 0, "SV_Elevation": 0, "SV_Azimuth": 0, "SV_SNR": 0})
        return {"SV_InView": sv_in_view, "SV": sv_data}

    async def _publish_gps_data(self):
        """Fetches and publishes GPS data."""
        payload = {}
        if self.gps and self.use_owa_hardware:
            update_flag, _ = self.gps.getFullGPSPosition()
            if self.gps.gps_pos_ok and update_flag:
                r, d = self.gps.GPS_GetSV_inView()
                payload = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [self.gps.lastCoord.LonDecimal, self.gps.lastCoord.LatDecimal]
                    },
                    "properties": {
                        "lastCoord": utils.getdict(self.gps.lastCoord),
                        "SV": utils.getdict(d)
                    }
                }
        else:
            fake_lat = 45.5257585 + random.uniform(-0.001, 0.001)
            fake_lon = 4.9240768 + random.uniform(-0.001, 0.001)
            payload = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [fake_lon, fake_lat]
                },
                "properties": {
                    "lastCoord": {
                        "PosValid": 1,
                        "OldValue": 0,
                        "Latitude": {"Degrees": 45, "Minutes": 31, "Seconds": 32.73, "Dir": "N"},
                        "Longitude": {"Degrees": 4, "Minutes": 55, "Seconds": 26.68, "Dir": "E"},
                        "Altitude": random.uniform(150, 250),
                        "NavStatus": "G3",
                        "HorizAccu": random.uniform(0.5, 1.5),
                        "VertiAccu": random.uniform(1, 2),
                        "Speed": random.uniform(0, 5),
                        "Course": random.uniform(0, 360),
                        "HDOP": random.uniform(0.8, 1.2),
                        "VDOP": random.uniform(1, 1.5),
                        "TDOP": random.uniform(1.2, 1.8),
                        "numSvs": 12,
                        "LatDecimal": fake_lat,
                        "LonDecimal": fake_lon,
                    },
                    "SV": self._generate_fake_sv_data(),
                    "fake": True,
                }
            }

        if payload:
            await self.messaging_client.publish("gps", json.dumps(payload, indent=None, separators=(',',':')).encode())
            self.logger.debug(f"Published GPS data: {payload}")
