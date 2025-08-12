import asyncio
import signal
import json
import logging
from abc import ABC, abstractmethod
from nats.aio.msg import Msg

from common.messaging import MessagingClient, NatsMessagingClient
from common.command_handler import CommandHandler
from common.logging_setup import setup_logging

class Microservice(ABC):
    """
    Abstract base class for a microservice.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = setup_logging(service_name)
        self.settings = {}
        self._shutdown_event = asyncio.Event()
        self.messaging_client: MessagingClient = NatsMessagingClient()
        self.command_handler = CommandHandler(self.service_name, self.logger)
        self.nats_url = "nats://localhost:4222"

    def _signal_handler(self, *args):
        self.logger.info("Shutdown signal received.")
        self._shutdown_event.set()

    async def connect(self):
        """Connects to the messaging server."""
        try:
            nats_url = self.settings.get("global", {}).get("nats_url", self.nats_url)
            await self.messaging_client.connect(nats_url)
            self.logger.info(f"Connected to messaging server at {nats_url}")
            return True
        except Exception as e:
            self.logger.error(f"Error connecting to messaging server: {e}")
            return False

    async def disconnect(self):
        if self.messaging_client:
            self.logger.info("Disconnecting from messaging server...")
            await self.messaging_client.disconnect()

    async def get_settings(self, retry_interval: int = 5):
        """
        Retrieves settings from the settings service, with retries.
        """
        while not self._shutdown_event.is_set():
            try:
                self.logger.info("Attempting to connect to NATS for settings...")
                # Use a temporary client for settings retrieval to not interfere
                # with the main client's state if it's already connected.
                settings_client = NatsMessagingClient()
                await settings_client.connect(self.nats_url)

                subject = f"settings.get.all"
                self.logger.info(f"Requesting settings on subject: {subject}")
                response = await settings_client.request(subject, b'', timeout=2.0)
                await settings_client.disconnect()

                self.settings = json.loads(response.data)
                self.logger.info(f"Settings received successfully: {self.settings}")

                # Now connect the main client with the correct URL
                await self.connect()
                return # Exit the loop on success

            except Exception as e:
                self.logger.warning(f"Could not get settings: {e}. Retrying in {retry_interval}s...")

            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=retry_interval)
            except asyncio.TimeoutError:
                pass

    async def _subscribe_to_commands(self):
        """Subscribes to the command stream for this service."""
        subject = f"commands.{self.service_name}"
        self.logger.info(f"Subscribing to command subject: {subject}")

        async def command_message_handler(msg: Msg):
            await self.command_handler.handle_message(msg.data)

        await self.messaging_client.subscribe(subject, cb=command_message_handler)

    async def run(self):
        """
        The main entry point for the microservice.
        This method sets up signal handling and runs the service's main logic.
        """
        self.logger.info("Service starting...")
        loop = asyncio.get_running_loop()
        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self._signal_handler)
        except NotImplementedError:
            self.logger.warning("loop.add_signal_handler not implemented. Using signal.signal().")
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            # The service's main logic, including dependency acquisition,
            # is now handled in _start_logic.
            await self._start_logic()

            self.logger.info("Service is running. Waiting for shutdown signal.")
            await self._shutdown_event.wait()
        except (asyncio.CancelledError, KeyboardInterrupt):
            self.logger.info("Run cancelled.")
        except Exception as e:
            self.logger.critical(f"An unhandled error occurred during run: {e}", exc_info=True)
        finally:
            self.logger.info("Shutting down...")
            await self._stop_logic()
            await self.disconnect()
            self.logger.info("Service has stopped.")

    async def stop(self):
        self.logger.info("Programmatic stop called.")
        self._shutdown_event.set()

    @abstractmethod
    async def _start_logic(self):
        pass

    @abstractmethod
    async def _stop_logic(self):
        pass
