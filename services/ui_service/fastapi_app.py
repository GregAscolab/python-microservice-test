from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import exceptions as JinjaExceptions
from pydantic import BaseModel
from typing import List, Dict
import json
import os
import sys
import cantools.database
import can
from datetime import datetime, timezone

# Add the project root to the Python path to allow for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from common.microservice import Microservice

# --- Absolute Path Setup ---
# This ensures that file paths are correct regardless of the working directory
APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "frontend", "static")
TEMPLATES_DIR = os.path.join(APP_DIR, "frontend", "templates")
# Use an absolute path for the main log directory as well
CAN_LOGS_DIR = os.path.abspath("can_logs")

# We use an APIRouter now, which will be included by the main app in service.py
router = APIRouter()

templates = Jinja2Templates(directory=TEMPLATES_DIR)


class ConnectionManager:
    """Manages active WebSocket connections."""
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].remove(websocket)

    async def broadcast(self, message: str, channel: str):
        if channel in self.active_connections:
            for connection in self.active_connections[channel]:
                await connection.send_text(message)

manager = ConnectionManager()

# --- Helper function to get the parent service ---
def get_service(request: Request) -> "UiService":
    return request.app.state.service

# --- HTML Page Routes ---

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/logger", response_class=HTMLResponse)
@router.get("/logger/{path:path}", response_class=HTMLResponse)
async def read_logger_path(request: Request, path: str = ""):
    service = get_service(request)
    try:
        os.makedirs(CAN_LOGS_DIR, exist_ok=True)
        full_path = os.path.normpath(os.path.join(CAN_LOGS_DIR, path))

        # Security check to prevent path traversal
        if not full_path.startswith(CAN_LOGS_DIR):
            return HTMLResponse("Forbidden", status_code=403)

        items = os.listdir(full_path)
        files = {item: os.path.getsize(os.path.join(full_path, item)) for item in items if os.path.isfile(os.path.join(full_path, item))}
        dirs = [item for item in items if os.path.isdir(os.path.join(full_path, item))]
        extensions = list(set(os.path.splitext(f)[1] for f in files))
    except Exception as e:
        service.logger.error(f"Error reading logger path '{path}': {e}")
        files, dirs, extensions = {}, [], []

    return templates.TemplateResponse("logger.html", {"request": request, "files": files, "dirs": dirs, "extensions": extensions, "current_path": path})

@router.get("/manager", response_class=HTMLResponse)
async def read_manager(request: Request):
    """Serves the manager page."""
    return templates.TemplateResponse("manager.html", {"request": request})

@router.get("/{page}", response_class=HTMLResponse)
async def read_page(request: Request, page: str):
    try:
        return templates.TemplateResponse(f"{page}.html", {"request": request})
    except JinjaExceptions.TemplateNotFound:
        return HTMLResponse("Page not found", status_code=404)

# --- WebSocket Endpoints ---

@router.websocket("/ws_data")
async def websocket_data_endpoint(websocket: WebSocket):
    request = websocket
    service = get_service(request)
    await manager.connect(websocket, "can_data")
    try:
        while True:
            data = await websocket.receive_text()
            await service.messaging_client.publish(
                "commands.can_bus_service",
                data.encode()
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket, "can_data")

@router.websocket("/ws_gps")
async def websocket_gps_endpoint(websocket: WebSocket):
    request = websocket
    service = get_service(request)
    await manager.connect(websocket, "gps")
    try:
        while True:
            data = await websocket.receive_text()
            await service.messaging_client.publish(
                "commands.gps_service",
                data.encode()
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket, "gps")

@router.websocket("/ws_settings")
async def websocket_settings_endpoint(websocket: WebSocket):
    request = websocket
    service = get_service(request)
    await manager.connect(websocket, "settings")

    all_settings_payload = {"settings": service.settings}
    await websocket.send_text(json.dumps(all_settings_payload, indent=None, separators=(',',':')))

    try:
        while True:
            data = await websocket.receive_text()
            service.logger.info(f"Received settings update from client: {data}")
            try:
                updates = json.loads(data)
                for key, setting_data in updates.items():
                    command = {
                        "command": "update_setting",
                        "group": setting_data["group"],
                        "key": key,
                        "value": setting_data["value"]
                    }
                    await service.messaging_client.publish(
                        "commands.settings_service",
                        json.dumps(command).encode()
                    )
            except Exception as e:
                service.logger.error(f"Error processing settings update from client: {e}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, "settings")

@router.websocket("/ws_manager")
async def websocket_manager_endpoint(websocket: WebSocket):
    """WebSocket endpoint for the manager page."""
    service = get_service(websocket)
    await manager.connect(websocket, "manager")
    service.logger.info("Manager client connected to WebSocket.")
    try:
        while True:
            # This is where we receive commands from the UI
            data = await websocket.receive_text()
            try:
                command = json.loads(data)
                # Forward the command to the manager service via NATS
                await service.messaging_client.publish(
                    "commands.manager",
                    json.dumps(command).encode()
                )
                service.logger.info(f"Forwarded command to manager service: {command}")
            except json.JSONDecodeError:
                service.logger.error(f"Received invalid JSON from manager websocket: {data}")
            except Exception as e:
                service.logger.error(f"Error processing command from manager websocket: {e}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, "manager")
        service.logger.info("Manager client disconnected from WebSocket.")

# --- API Endpoints ---

LOGS_DIR = os.path.abspath("logs")

@router.get("/api/logs/{service_name}", response_class=HTMLResponse)
async def get_service_logs(service_name: str, request: Request):
    """Reads and returns the last N lines of a service's log file."""
    service = get_service(request)
    try:
        # Ensure the logs directory exists
        os.makedirs(LOGS_DIR, exist_ok=True)

        log_file_path = os.path.normpath(os.path.join(LOGS_DIR, f"{service_name}.log"))

        # Security check to prevent path traversal
        if not os.path.abspath(log_file_path).startswith(LOGS_DIR):
            return HTMLResponse("Forbidden: Access to this path is not allowed.", status_code=403)

        if not os.path.exists(log_file_path):
            return HTMLResponse(f"Log file for '{service_name}' not found.", status_code=404)

        # Read the last part of the file to avoid large transfers
        file_size = os.path.getsize(log_file_path)
        read_size = 16384 # Read last 16KB

        with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
            if file_size > read_size:
                f.seek(file_size - read_size)
                # Read a bit more to ensure we start on a new line, then split
                f.readline()

            content = f.read()
            return HTMLResponse(content, media_type="text/plain")

    except Exception as e:
        service.logger.error(f"Error reading log for service '{service_name}': {e}", exc_info=True)
        return HTMLResponse(f"An error occurred while trying to read the log file.", status_code=500)


@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    full_path = os.path.normpath(os.path.join(CAN_LOGS_DIR, file_path))
    if not full_path.startswith(CAN_LOGS_DIR):
        return HTMLResponse("Forbidden", status_code=403)

    if os.path.exists(full_path):
        return FileResponse(full_path, filename=os.path.basename(full_path))
    return HTMLResponse("File not found", status_code=404)

class FileToConvert(BaseModel):
    name: str
    folder: str

class TimeSeriesData(BaseModel):
    name: str
    timestamps: List[str]
    values: List[float]

@router.post("/convert", response_model=List[TimeSeriesData])
def convert_file(file_content: FileToConvert, request: Request):
    service = get_service(request)
    service.logger.info(f"Converting file: {file_content.name} in folder {file_content.folder}")

    try:
        db_path = os.path.abspath("config/db-full.dbc")
        db = cantools.database.load_file(db_path)
        file_path = os.path.join(CAN_LOGS_DIR, file_content.folder, file_content.name)

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

        return time_series_data
    except Exception as e:
        service.logger.error(f"Error during file conversion: {e}", exc_info=True)
        return []
