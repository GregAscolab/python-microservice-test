import asyncio
import json
import os
import sys
from datetime import datetime, timezone
import uuid
import boto3
import glob

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

class AppLoggerService(Microservice):
    """
    The application logger service.
    """

    def __init__(self):
        super().__init__("app_logger_service")
        self.is_running = False
        self.start_date = None
        self.start_position = None
        self.log_data = {}
        self.log_filename = None
        self.log_dir = "app_logs"

    async def _start_logic(self):
        self.logger.info("Waiting for settings...")
        await self.get_settings()

        if self._shutdown_event.is_set():
            return

        os.makedirs(self.log_dir, exist_ok=True)

        self.command_handler.register_command("start", self._handle_start)
        self.command_handler.register_command("stop", self._handle_stop)
        await self._subscribe_to_commands()

        await self.messaging_client.subscribe(
            "app_logger.get_status",
            cb=self._handle_get_status_request
        )

        self.logger.info("App logger service started.")
        await self._publish_status()

    async def _stop_logic(self):
        self.logger.info("Stopping app logger service...")
        if self.is_running:
            await self._handle_stop()

    async def _handle_get_status_request(self, msg):
        """Replies with the current status."""
        self.logger.info("Received request for current status.")
        if msg.reply:
            status = {
                "isRunning": self.is_running,
                "startDate": self.start_date.isoformat() if self.start_date else None,
                "startPosition": self.start_position
            }
            await self.messaging_client.publish(msg.reply, json.dumps(status).encode())

    async def _publish_status(self):
        """Publishes the current status of the logger."""
        status = {
            "isRunning": self.is_running,
            "startDate": self.start_date.isoformat() if self.start_date else None,
            "startPosition": self.start_position
        }
        await self.messaging_client.publish("app_logger.status", json.dumps(status).encode())

    async def _handle_start(self):
        if self.is_running:
            self.logger.warning("Logger is already running.")
            return

        self.is_running = True
        self.start_date = datetime.now(timezone.utc)
        self.logger.info(f"Starting app logger at {self.start_date.isoformat()}")

        # Generate a unique filename
        timestamp = self.start_date.strftime("%Y%m%d_%H%M%S")
        self.log_filename = f"app_log_{timestamp}.json"
        self.log_data = {
            "startDate": self.start_date.isoformat(),
            "startPosition": None,
            "canBusLogs": []
        }

        # Get GPS position
        try:
            gps_response_msg = await self.messaging_client.request(
                "gps.get_current_position.request",
                b'',
                timeout=5.0
            )
            self.start_position = json.loads(gps_response_msg.data)
            self.log_data["startPosition"] = self.start_position
            self.logger.info(f"Received start position: {self.start_position}")
        except asyncio.TimeoutError:
            self.logger.error("Request to gps_service timed out.")
        except Exception as e:
            self.logger.error(f"Error getting GPS position: {e}", exc_info=True)

        # Start CAN bus recording
        can_log_basename = os.path.splitext(self.log_filename)[0]
        await self.messaging_client.publish(
            "commands.can_bus_service",
            json.dumps({"command": "startRecording", "filename": can_log_basename}).encode()
        )
        self.logger.info(f"Sent startRecording command to can_bus_service with filename {can_log_basename}")

        # Write initial log file
        self._write_log_file()

        await self._publish_status()

    async def _handle_stop(self):
        if not self.is_running:
            self.logger.warning("Logger is not running.")
            return

        self.logger.info("Stopping app logger...")

        # Stop CAN bus recording and get file list
        can_files_future = asyncio.Future()
        async def can_files_handler(msg):
            can_files_future.set_result(json.loads(msg.data))

        sub = await self.messaging_client.subscribe("can_bus.files.logged", cb=can_files_handler)

        await self.messaging_client.publish(
            "commands.can_bus_service",
            json.dumps({"command": "stopRecording"}).encode()
        )

        try:
            can_files_data = await asyncio.wait_for(can_files_future, timeout=10.0)
            self.log_data["canBusLogs"] = can_files_data.get("files", [])
            self.logger.info(f"Received CAN log files: {self.log_data['canBusLogs']}")
        except asyncio.TimeoutError:
            self.logger.error("Timed out waiting for CAN log files.")
        finally:
            await sub.unsubscribe()

        # Write final log file
        self._write_log_file()

        # Upload to S3
        await self._upload_to_s3(os.path.join(self.log_dir, self.log_filename))

        # Reset state
        self.is_running = False
        self.start_date = None
        self.start_position = None
        self.log_data = {}
        self.log_filename = None

        await self._publish_status()

    def _write_log_file(self):
        """Writes the log data to the JSON file."""
        if not self.log_filename:
            return

        log_path = os.path.join(self.log_dir, self.log_filename)
        try:
            with open(log_path, 'w') as f:
                json.dump(self.log_data, f, indent=4)
            self.logger.info(f"Wrote log data to {log_path}")
        except Exception as e:
            self.logger.error(f"Error writing log file {log_path}: {e}", exc_info=True)

    async def _upload_to_s3(self, file_path: str):
        self.logger.info(f"Starting S3 upload for file: {file_path}")
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=self.global_settings.get("s3_endpoint_url"),
                aws_access_key_id=self.global_settings.get("s3_access_key"),
                aws_secret_access_key=self.global_settings.get("s3_secret_key")
            )
            bucket_name = self.global_settings.get("s3_bucket")
            file_name = os.path.basename(file_path)

            self.logger.info(f"Uploading {file_name} to S3 bucket '{bucket_name}'...")
            s3_client.upload_file(file_path, bucket_name, file_name)
            self.logger.info(f"Successfully uploaded {file_name}.")
        except Exception as e:
            self.logger.error(f"S3 upload failed: {e}", exc_info=True)
