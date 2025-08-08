import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

class UiService(Microservice):
    """
    Placeholder for the User Interface microservice.
    """

    def __init__(self):
        super().__init__("ui_service")

    async def _handle_ping_command(self, message: str = "pong"):
        """Handles the 'ping' command."""
        self.logger.info(f"Received ping command! Replying with: {message}")
        await asyncio.sleep(1)

    async def _start_logic(self):
        """
        Service-specific startup logic for the UI service.
        """
        self.logger.info("Waiting for settings...")
        await self.get_settings()

        if self._shutdown_event.is_set():
            return

        self.logger.info("Starting logic. Would start FastAPI server here.")

        # Subscribe to commands after we have a NATS connection.
        await self._subscribe_to_commands()

        self.command_handler.register_command("ping", self._handle_ping_command)

    async def _stop_logic(self):
        """
        Service-specific shutdown logic for the UI service.
        """
        self.logger.info("Stop logic executed. Would gracefully shut down FastAPI server here.")
        pass
