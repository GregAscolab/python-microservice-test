import asyncio
import json
import time
import sys
import os
import cantools
import can
import boto3
from datetime import datetime, timezone
import glob
from typing import List

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

class CanBusService(Microservice):
    """
    The CAN Bus data decoding and logging microservice.
    """

    def __init__(self):
        super().__init__("can_bus_service")
        self.can_bus = None
        self.db = None
        self.listener_task = None
        self.can_logger: can.Logger | None = None
        self.current_log_path_pattern: str | None = None
        self.notifier: can.Notifier | None = None

    async def _start_logic(self):
        self.logger.info("Waiting for settings...")
        await self.get_settings()

        if self._shutdown_event.is_set(): return

        self.logger.info("Initializing...")

        interface = self.settings.get("interface", "virtual")
        channel = self.settings.get("channel", "vcan0")
        if channel == "" : channel=None

        try:
            self.logger.info(f"Initializing CAN bus: interface={interface}, channel={channel}")
            self.can_bus = can.interface.Bus(channel=channel, interface=interface)
        except Exception as e:
            self.logger.error(f"Error initializing CAN bus: {e}", exc_info=True)
            return

        if dbc_file := self.settings.get("dbc_file"):
            try:
                self.logger.info(f"Loading DBC file from {dbc_file}...")
                self.db = cantools.db.load_file(dbc_file)
            except FileNotFoundError:
                self.logger.error(f"DBC file not found at {dbc_file}")

        self.command_handler.register_command("startRecording", self._handle_start_recording)
        self.command_handler.register_command("stopRecording", self._handle_stop_recording)
        await self._subscribe_to_commands()

        self.listener_task = asyncio.create_task(self._message_listener())
        self.logger.info("CAN message listener started.")

    async def _stop_logic(self):
        self.logger.info("Stopping...")
        if self.can_logger:
            await self._handle_stop_recording()

        if self.listener_task and not self.listener_task.done():
            self.listener_task.cancel()

        if self.can_bus:
            self.can_bus.shutdown()
            self.logger.info("CAN bus shut down.")

    async def _message_listener(self):
        reader = can.AsyncBufferedReader()
        self.notifier = can.Notifier(self.can_bus, [reader], loop=asyncio.get_running_loop())

        try:
            while True:
                msg = await reader.get_message()
                if not self.db: continue
                try:
                    decoded = self.db.decode_message(msg.arbitration_id, msg.data)
                    for name, value in decoded.items():
                        current_time = int(msg.timestamp * 1000)
                        payload = {'name': name, 'value': round(float(value), 3), 'ts': current_time}
                        await self.messaging_client.publish(f"can_data", json.dumps(payload, indent=None, separators=(',',':')).encode())
                        self.logger.debug(f"Published decoded signal: {payload}")
                except Exception:
                    pass
        except asyncio.CancelledError:
            self.logger.info("Message listener cancelled.")
        finally:
            if self.notifier:
                self.notifier.stop()

    async def _upload_to_s3(self, file_path_pattern: str):
        self.logger.info(f"Starting S3 upload for files matching: {file_path_pattern}*")
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=self.settings.get("s3_endpoint_url"),
                aws_access_key_id=self.settings.get("s3_access_key"),
                aws_secret_access_key=self.settings.get("s3_secret_key")
            )
            bucket_name = self.settings.get("s3_bucket")

            for file_to_upload in glob.glob(f"{file_path_pattern}*"):
                file_name = os.path.basename(file_to_upload)
                self.logger.info(f"Uploading {file_name} to S3 bucket '{bucket_name}'...")
                s3_client.upload_file(file_to_upload, bucket_name, file_name)
                self.logger.info(f"Successfully uploaded {file_name}.")
        except Exception as e:
            self.logger.error(f"S3 upload failed: {e}", exc_info=True)

    async def _handle_start_recording(self):
        if self.can_logger:
            self.logger.warning("Recording is already in progress.")
            return

        log_dir = self.settings.get("log_dir", "can_logs")
        os.makedirs(log_dir, exist_ok=True)

        file_format = self.settings.get("log_file_format", ".blf")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        self.current_log_path_pattern = os.path.join(log_dir, f"can_log_{timestamp}")
        log_path_with_ext = f"{self.current_log_path_pattern}{file_format}"

        self.logger.info(f"Starting CAN recording to {log_path_with_ext}")

        try:
            file_size = self.settings.get("log_file_size", 0)
            if file_size and file_size > 0:
                self.can_logger = can.SizedRotatingLogger(log_path_with_ext, max_bytes=file_size)
            else:
                self.can_logger = can.Logger(log_path_with_ext)

            if self.notifier:
                self.notifier.add_listener(self.can_logger)
        except Exception as e:
            self.logger.error(f"Failed to start CAN logger: {e}", exc_info=True)
            self.can_logger = None

    async def _handle_stop_recording(self):
        if not self.can_logger:
            self.logger.warning("Recording is not in progress.")
            return

        self.logger.info("Stopping CAN recording...")
        if self.notifier:
            self.notifier.remove_listener(self.can_logger)
        self.can_logger.stop()
        self.can_logger = None

        await self._upload_to_s3(self.current_log_path_pattern)
        self.current_log_path_pattern = None
