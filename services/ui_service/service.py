import asyncio
import sys
import os
import uvicorn
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from nats.aio.msg import Msg
import json

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice
from services.ui_service.fastapi_app import router as api_router, manager as connection_manager

class UiService(Microservice):
    """
    The User Interface microservice.
    """

    def __init__(self):
        super().__init__("ui_service")
        self.fastapi_task = None
        self.server = None
        self.app = FastAPI()

        # Mount static files directly on the app instance
        static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend", "static"))
        self.app.mount("/static", StaticFiles(directory=static_dir), name="static")

        self.app.include_router(api_router)
        self.app.state.service = self

    async def _nats_data_handler(self, msg: Msg):
        channel = msg.subject
        data = msg.data.decode()
        await connection_manager.broadcast(data, channel)

    async def _settings_update_handler(self, msg: Msg):
        self.logger.info(f"Received settings update: {msg.data.decode()}")
        await connection_manager.broadcast(msg.data.decode(), "settings")

    async def _handle_ping_command(self, message: str = "pong"):
        self.logger.info(f"Received ping command! Replying with: {message}")
        await asyncio.sleep(1)

    async def _start_logic(self):
        self.logger.info("Waiting for settings...")
        await self.get_settings()

        if self._shutdown_event.is_set():
            return

        self.command_handler.register_command("ping", self._handle_ping_command)

        await self.messaging_client.subscribe("can_data", cb=self._nats_data_handler)
        self.logger.info("Subscribed to 'can_data'")
        await self.messaging_client.subscribe("gps", cb=self._nats_data_handler)
        self.logger.info("Subscribed to 'gps'")
        await self.messaging_client.subscribe("settings.updated", cb=self._settings_update_handler)
        self.logger.info("Subscribed to 'settings.updated'")
        await self._subscribe_to_commands()

        self.logger.info("Starting FastAPI server...")

        logging.getLogger("uvicorn.error").handlers = self.logger.handlers
        logging.getLogger("uvicorn.access").handlers = self.logger.handlers

        config = uvicorn.Config(
            app=self.app,
            host=self.settings.get("host", "0.0.0.0"),
            port=self.settings.get("port", 8000),
            log_config=None,
        )
        self.server = uvicorn.Server(config)

        self.fastapi_task = asyncio.create_task(self.server.serve())
        self.logger.info(f"FastAPI server started on http://{config.host}:{config.port}")

    async def _stop_logic(self):
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
