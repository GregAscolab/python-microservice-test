import asyncio
import json
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice
from nats.aio.msg import Msg

class OwaService(Microservice):
    """
    A microservice to manage Owasys hardware initialization and shutdown.
    """

    def __init__(self):
        super().__init__("owa_service")
        self.rtu = None
        self.io = None
        self.use_owa_hardware = False
        self.status = "initializing"

    async def _handle_status_request(self, msg: Msg):
        """Handles requests for the service's status."""
        self.logger.info(f"Received status request on subject '{msg.subject}'")
        if msg.reply:
            status_payload = json.dumps({"status": self.status}).encode()
            await self.messaging_client.publish(msg.reply, status_payload)
            self.logger.info(f"Responded to status request with status: {self.status}")

    async def _start_logic(self):
        self.logger.info("Waiting for settings...")
        await self.get_settings()

        if self._shutdown_event.is_set(): return

        # Subscribe to status requests
        await self.messaging_client.subscribe("owa.service.status.request", cb=self._handle_status_request)
        self.logger.info("Subscribed to status requests on 'owa.service.status.request'")

        self.use_owa_hardware = self.settings.get("global", {}).get("hardware_platform") == "owa5x"
        self.logger.info(f"OWA Service starting. Hardware platform: {'owa5x' if self.use_owa_hardware else 'generic'}")

        if self.use_owa_hardware:
            try:
                from common.owa_rtu import Rtu
                from common.owa_io import Io

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

                self.logger.info("OWA hardware is ready.")
                self.status = "ready"
            except Exception as e:
                self.logger.error(f"Error during OWA hardware initialization: {e}", exc_info=True)
                self.status = "error"
                return
        else:
            self.logger.info("Running on a generic platform. Skipping OWA hardware initialization.")
            self.status = "ready"

        # Publish a broadcast message that the service is ready
        await self.messaging_client.publish("owa.status", json.dumps({"status": self.status}).encode())


    async def _stop_logic(self):
        self.logger.info("Stopping OWA hardware...")
        if self.use_owa_hardware:
            if self.io:
                self.io.finalize()
                self.logger.info("Owasys IO finalized.")
            if self.rtu:
                self.rtu.finalize()
                self.logger.info("Owasys RTU finalized.")
        self.status = "stopped"
        self.logger.info("OWA service stopped.")
