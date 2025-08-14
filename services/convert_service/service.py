import asyncio
import sys
import os
import json
import cantools.database
import can
from datetime import datetime, timezone

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

CAN_LOGS_DIR = os.path.abspath("can_logs")

class ConvertService(Microservice):
    """
    The Converter microservice.
    """

    def __init__(self):
        super().__init__("convert_service")

    async def _start_logic(self):
        self.logger.info("Waiting for settings...")
        await self.get_settings()

        if self._shutdown_event.is_set():
            return

        self.command_handler.register_command("blfToTimeseries", self.blf_to_timeseries)

        await self._subscribe_to_commands()
        self.logger.info("Converter service started and subscribed to commands.")

    async def _stop_logic(self):
        pass

    async def blf_to_timeseries(self, filename, folder):
        self.logger.info(f"Converting file: {filename} in folder {folder}")

        try:
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

            self.logger.info(f"Conversion successful for {filename}. Found {len(time_series_data)} signals.")
            await self.messaging_client.publish(
                "conversion.results",
                json.dumps({"status": "success", "filename": filename, "data": time_series_data}).encode()
            )

        except Exception as e:
            self.logger.error(f"Error during file conversion: {e}", exc_info=True)
            await self.messaging_client.publish(
                "conversion.results",
                json.dumps({"status": "error", "filename": filename, "message": str(e)}).encode()
            )
