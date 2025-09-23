import asyncio
import sys
import os
import json
import cantools.database
import can
from datetime import datetime, timezone
from nats.aio.msg import Msg

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

CAN_LOGS_DIR = os.path.abspath("can_logs")
CONVERTED_LOGS_DIR = os.path.abspath("converted_logs")
os.makedirs(CONVERTED_LOGS_DIR, exist_ok=True)

class ConvertService(Microservice):
    """
    The Converter microservice.
    """

    def __init__(self):
        super().__init__("convert_service")
        self.is_converting = False

    async def _start_logic(self):
        self.logger.info("Waiting for settings...")
        await self.get_settings()

        if self._shutdown_event.is_set():
            return

        self.command_handler.register_command("blfToTimeseries", self.blf_to_timeseries)

        await self._subscribe_to_commands()

        # Specific subscription for request-reply pattern
        await self.messaging_client.subscribe(
            "commands.convert_service.get_conversion_status",
            cb=self._handle_get_conversion_status_request
        )

        self.logger.info("Converter service started and subscribed to commands.")

    async def _stop_logic(self):
        pass

    async def _handle_get_conversion_status_request(self, msg: Msg):
        """Handles request for conversion status and replies."""
        try:
            data = json.loads(msg.data.decode())
            path = data.get("path", "")
            self.logger.info(f"Received request for conversion status for path: {path}")

            status_data = await self.get_conversion_status(path)

            if msg.reply:
                await self.messaging_client.publish(msg.reply, json.dumps(status_data).encode())
                self.logger.info(f"Replied to {msg.reply} with conversion status.")
        except Exception as e:
            self.logger.error(f"Error handling get_conversion_status request: {e}", exc_info=True)

    async def get_conversion_status(self, path=""):
        """
        Get the conversion status of BLF files in a given path.
        """
        try:
            target_path = os.path.join(CAN_LOGS_DIR, path)
            items = os.listdir(target_path)

            response_data = []
            for item in items:
                item_path = os.path.join(target_path, item)
                if os.path.isdir(item_path):
                    response_data.append({"name": item, "type": "dir"})
                elif item.lower().endswith(".blf"):
                    json_filename = os.path.splitext(item)[0] + ".json"
                    converted_file_path = os.path.join(CONVERTED_LOGS_DIR, path, json_filename)

                    status = "converted" if os.path.exists(converted_file_path) else "not_converted"

                    response_data.append({
                        "name": item,
                        "type": "file",
                        "size": os.path.getsize(item_path),
                        "status": status
                    })
            return {"path": path, "contents": response_data}
        except Exception as e:
            self.logger.error(f"Error getting conversion status for path '{path}': {e}", exc_info=True)
            return {"error": str(e)}

    async def blf_to_timeseries(self, filename, folder, force=False):
        if self.is_converting:
            await self.messaging_client.publish(
                "conversion.results",
                json.dumps({"status": "busy", "filename": filename}).encode()
            )
            return

        self.is_converting = True
        try:
            self.logger.info(f"Converting file: {filename} in folder {folder}")

            json_filename = os.path.splitext(filename)[0] + ".json"
            converted_folder_path = os.path.join(CONVERTED_LOGS_DIR, folder)
            os.makedirs(converted_folder_path, exist_ok=True)
            converted_file_path = os.path.join(converted_folder_path, json_filename)

            if os.path.exists(converted_file_path) and not force:
                await self.messaging_client.publish(
                    "conversion.results",
                    json.dumps({"status": "already_converted", "filename": filename}).encode()
                )
                return

            await self.messaging_client.publish(
                "conversion.results",
                json.dumps({"status": "started", "filename": filename}).encode()
            )

            db_path = os.path.abspath("config/db-full.dbc")
            db = cantools.database.load_file(db_path)
            file_path = os.path.join(CAN_LOGS_DIR, folder, filename)

            time_series_data = []
            signals_cache = {}
            with can.LogReader(file_path) as reader:
                for msg in reader:
                    try:
                        decoded = db.decode_message(msg.arbitration_id, msg.data, decode_choices=False)
                        utc_time_str = datetime.fromtimestamp(msg.timestamp, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                        for k, v in decoded.items():
                            if k not in signals_cache:
                                signals_cache[k] = {"name": k, 'timestamps': [], "values": []}
                            signals_cache[k]['timestamps'].append(utc_time_str)
                            signals_cache[k]['values'].append(v)
                    except Exception:
                        continue

            for data in signals_cache.values():
                time_series_data.append(data)

            with open(converted_file_path, 'w') as f:
                json.dump(time_series_data, f)

            self.logger.info(f"Conversion successful for {filename}. Saved to {converted_file_path}")
            await self.messaging_client.publish(
                "conversion.results",
                json.dumps({"status": "success", "filename": filename, "converted_filename": json_filename}).encode()
            )

        except Exception as e:
            self.logger.error(f"Error during file conversion: {e}", exc_info=True)
            await self.messaging_client.publish(
                "conversion.results",
                json.dumps({"status": "error", "filename": filename, "message": str(e)}).encode()
            )
        finally:
            self.is_converting = False
