import asyncio
import sys
import os
import uvicorn
import logging
from fastapi import FastAPI
from nats.aio.msg import Msg
import json

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice
from services.ui_service.fastapi_app import router as api_router, manager as connection_manager

class UiService(Microservice):
    """
    The User Interface microservice.
    This service runs a FastAPI server to provide the user interface.
    """

    def __init__(self):
        super().__init__("ui_service")
        self.fastapi_task = None
        self.server = None
        self.app = FastAPI()
        self.app.include_router(api_router)
        self.app.state.service = self

    async def _nats_data_handler(self, msg: Msg):
        """Broadcasts data from 'can_data' and 'gps' to websockets."""
        channel = msg.subject
        data = msg.data.decode()
        await connection_manager.broadcast(data, channel)

    async def _settings_update_handler(self, msg: Msg):
        """Handles broadcasted settings updates and forwards them to the UI."""
        self.logger.info(f"Received settings update: {msg.data.decode()}")
        await connection_manager.broadcast(msg.data.decode(), "settings")

    async def _handle_ping_command(self, message: str = "pong"):
        """Handles the 'ping' command."""
        self.logger.info(f"Received ping command! Replying with: {message}")
        await asyncio.sleep(1)

    async def _start_logic(self):
        """
        Acquires settings, subscribes to data topics, and starts the FastAPI server.
        """
        self.logger.info("Waiting for settings...")
        await self.get_settings()

        if self._shutdown_event.is_set():
            return

        # Register command handlers BEFORE subscribing
        self.command_handler.register_command("ping", self._handle_ping_command)

        # Subscribe to topics
        await self.messaging_client.subscribe("can_data", cb=self._nats_data_handler)
        self.logger.info("Subscribed to 'can_data'")
        await self.messaging_client.subscribe("gps", cb=self._nats_data_handler)
        self.logger.info("Subscribed to 'gps'")
        await self.messaging_client.subscribe("settings.updated", cb=self._settings_update_handler)
        self.logger.info("Subscribed to 'settings.updated'")
        await self._subscribe_to_commands()

        self.logger.info("Starting FastAPI server...")

        # Redirect Uvicorn's loggers to our configured logger
        logging.getLogger("uvicorn.error").handlers = self.logger.handlers
        logging.getLogger("uvicorn.access").handlers = self.logger.handlers

        config = uvicorn.Config(
            app=self.app,
            host=self.settings.get("host", "0.0.0.0"),
            port=self.settings.get("port", 8000),
            log_config=None, # Prevent uvicorn from setting up its own loggers
        )
        self.server = uvicorn.Server(config)

        self.fastapi_task = asyncio.create_task(self.server.serve())
        self.logger.info(f"FastAPI server started on http://{config.host}:{config.port}")

    async def _stop_logic(self):
        """
        Stops the FastAPI server.
        """
        self.logger.info("Stopping FastAPI server...")
        if self.server:
            self.server.should_exit = True

        if self.fastapi_task:
            try:
                await asyncio.wait_for(self.fastapi_task, timeout=5.0)
            except asyncio.TimeoutError:
                self.logger.warning("FastAPI server did not shut down gracefully.")
            except asyncio.CancelledError:
                pass

        self.logger.info("FastAPI server stopped.")
