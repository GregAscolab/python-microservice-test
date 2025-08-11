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
        self.logger.info("Waiting for OWA hardware to be ready...")
        await self.messaging_client.subscribe("owa.status", cb=self._on_hardware_status)

        try:
            # Wait for the hardware to be ready, with a timeout to avoid waiting forever
            await asyncio.wait_for(self.hardware_ready.wait(), timeout=60.0)
        except asyncio.TimeoutError:
            self.logger.critical("Timed out waiting for OWA hardware. GPS service will not start.")
            return

        if sys.platform == 'linux':
            self.logger.info("Initializing real GPS...")
            try:
                self.gps = Gps(nats=self.messaging_client)
                # The modem_type should ideally come from settings
                self.gps.gps_init(modem_type="owa5x")
            except Exception as e:
                self.logger.error(f"Error initializing GPS: {e}", exc_info=True)
                self.gps = None # Ensure gps is None if init fails
        else:
            self.logger.info("Not on Linux. Fake GPS data will be used.")
            # No specific initialization needed for fake GPS

        self.publisher_task = asyncio.create_task(self._gps_publisher_loop())
        self.logger.info("GPS data publisher started.")


    async def _stop_logic(self):
        """Stops the GPS service logic."""
        self.logger.info("Stopping GPS service...")
        if self.publisher_task and not self.publisher_task.done():
            self.publisher_task.cancel()

        if self.gps and sys.platform == 'linux':
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
                await asyncio.sleep(5) # Wait a bit longer after an error

    async def _publish_gps_data(self):
        """Fetches and publishes GPS data."""
        payload = {}
        if self.gps and sys.platform == 'linux':
            # Get real GPS data
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
            # Generate fake GPS data
            fake_lat = 45.5257585 + random.uniform(-0.001, 0.001)
            fake_lon = 4.9240768 + random.uniform(-0.001, 0.001)
            payload = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [fake_lon, fake_lat]
                },
                "properties": {
                    "fake": True,
                    "quality": "Good",
                    "satellites": 12,
                    "altitude": random.uniform(150, 250)
                }
            }

        if payload:
            await self.messaging_client.publish("gps", json.dumps(payload, indent=None, separators=(',',':')).encode())
            self.logger.debug(f"Published GPS data: {payload}")
