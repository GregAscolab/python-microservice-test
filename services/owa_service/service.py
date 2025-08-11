import asyncio
import json
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

class OwaService(Microservice):
    """
    A microservice to manage Owasys hardware initialization and shutdown.
    """

    def __init__(self):
        super().__init__("owa_service")
        self.rtu = None
        self.io = None
        self.use_owa_hardware = False

    async def _start_logic(self):
        self.logger.info("Waiting for settings...")
        await self.get_settings()

        if self._shutdown_event.is_set(): return

        self.use_owa_hardware = self.settings.get("global", {}).get("hardware_platform") == "owa5x"

        self.logger.info(f"OWA Service starting. Hardware platform: {'owa5x' if self.use_owa_hardware else 'generic'}")

        if self.use_owa_hardware:
            try:
                from common.owa_rtu import Rtu
                from common.owa_io import Io

                # Owasys RTU initialization to be done first
                self.logger.info("Initializing Owasys RTU...")
                self.rtu = Rtu()
                self.rtu.initialize()
                self.rtu.start()
                res, val = self.rtu.is_active()
                self.logger.info(f"RTU is_active = {res}, {val}")

                # IO initialization (To be done before GPS init !)
                self.logger.info("Initializing Owasys IO...")
                self.io = Io()
                self.io.initialize()
                self.io.start()
                res, val = self.io.is_active()
                self.logger.info(f"IO is_active = {res}, {val}")

                # Switch on GPS power
                self.logger.info("Switching GPS power ON...")
                res = self.io.switch_gps_on_off(1)
                self.logger.info(f"Switch ON GPS result = {res}")

                self.logger.info("OWA hardware is ready.")

            except Exception as e:
                self.logger.error(f"Error during OWA hardware initialization: {e}", exc_info=True)
                # If hardware fails, we should not say it's ready
                return
        else:
            self.logger.info("Running on a generic platform. Skipping OWA hardware initialization.")

        # Always publish a ready status so other services can start
        self.logger.info("Publishing hardware ready status to 'owa.status'")
        await self.messaging_client.publish("owa.status", json.dumps({"status": "ready"}).encode())


    async def _stop_logic(self):
        self.logger.info("Stopping OWA hardware...")
        if self.use_owa_hardware:
            if self.io:
                self.io.finalize()
                self.logger.info("Owasys IO finalized.")
            if self.rtu:
                self.rtu.finalize()
                self.logger.info("Owasys RTU finalized.")
        else:
            self.logger.info("Running on a generic platform. Skipping OWA hardware finalization.")
