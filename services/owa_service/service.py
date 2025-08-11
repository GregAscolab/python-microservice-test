import asyncio
import json
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

if sys.platform == 'linux':
    from common.owa_rtu import Rtu
    from common.owa_io import Io

class OwaService(Microservice):
    """
    A microservice to manage Owasys hardware initialization and shutdown.
    """

    def __init__(self):
        super().__init__("owa_service")
        self.rtu = None
        self.io = None

    async def _start_logic(self):
        self.logger.info("Starting OWA hardware initialization...")

        if sys.platform == 'linux':
            try:
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

                # Publish hardware ready status
                self.logger.info("Publishing hardware ready status to 'owa.status'")
                await self.messaging_client.publish("owa.status", json.dumps({"status": "ready"}).encode())
                self.logger.info("OWA hardware is ready.")

            except Exception as e:
                self.logger.error(f"Error during OWA hardware initialization: {e}", exc_info=True)
        else:
            self.logger.warning("Not on Linux platform. Skipping OWA hardware initialization.")
            # On non-Linux platforms, we can simulate the hardware being ready
            self.logger.info("Publishing simulated hardware ready status to 'owa.status'")
            await self.messaging_client.publish("owa.status", json.dumps({"status": "ready"}).encode())


    async def _stop_logic(self):
        self.logger.info("Stopping OWA hardware...")
        if sys.platform == 'linux':
            if self.io:
                self.io.finalize()
                self.logger.info("Owasys IO finalized.")
            if self.rtu:
                self.rtu.finalize()
                self.logger.info("Owasys RTU finalized.")
        else:
            self.logger.info("Not on Linux platform. Skipping OWA hardware finalization.")
