import asyncio
import signal
from abc import ABC, abstractmethod
import nats
from nats.aio.client import Client as NATS

class Microservice(ABC):
    """
    Abstract base class for a microservice.
    Provides a common structure for connecting to NATS,
    handling settings, and managing the service lifecycle.
    """

    def __init__(self, service_name: str, nats_url: str = "nats://localhost:4222"):
        self.service_name = service_name
        self.nats_url = nats_url
        self.nc: NATS = None
        self.is_running = False
        self.settings = {}

    async def connect(self):
        """Connects to the NATS server."""
        try:
            self.nc = await nats.connect(self.nats_url)
            print(f"[{self.service_name}] Connected to NATS at {self.nats_url}")
        except Exception as e:
            print(f"[{self.service_name}] Error connecting to NATS: {e}")
            raise

    async def disconnect(self):
        """Disconnects from the NATS server."""
        if self.nc and not self.nc.is_closed:
            print(f"[{self.service_name}] Disconnecting from NATS...")
            await self.nc.close()

    async def get_settings(self):
        """
        Requests settings from the settings service.
        This is a placeholder and should be implemented
        to fetch settings via NATS.
        """
        print(f"[{self.service_name}] Requesting settings...")
        # In a real implementation, this would involve a NATS request
        # to the settings service. For now, we'll use a placeholder.
        self.settings = {"default_setting": "default_value"}
        print(f"[{self.service_name}] Settings received: {self.settings}")


    async def run(self):
        """
        The main entry point for the microservice.
        Connects to NATS, gets settings, starts the service logic,
        and handles graceful shutdown.
        """
        self.is_running = True
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        try:
            await self.connect()
            await self.get_settings()
            await self._start_logic()

            print(f"[{self.service_name}] Service is running.")
            while self.is_running:
                await asyncio.sleep(1)

        except Exception as e:
            print(f"[{self.service_name}] An error occurred during run: {e}")
        finally:
            await self.disconnect()
            print(f"[{self.service_name}] Service has stopped.")

    async def stop(self):
        """Stops the microservice."""
        if not self.is_running:
            return

        print(f"[{self.service_name}] Stopping service...")
        self.is_running = False
        await self._stop_logic()


    @abstractmethod
    async def _start_logic(self):
        """
        Abstract method for service-specific startup logic.
        This is where you would set up NATS subscriptions, etc.
        """
        pass

    @abstractmethod
    async def _stop_logic(self):
        """
        Abstract method for service-specific shutdown logic.
        This is where you would clean up resources.
        """
        pass
