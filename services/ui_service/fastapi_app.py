from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import exceptions as JinjaExceptions
import json
import os
import sys
import base64
from typing import List, Dict, Any

# Add project root to Python path for absolute imports.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from common.microservice import Microservice

# --- Constants and Setup ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(APP_DIR, "frontend", "templates")
CAN_LOGS_DIR = os.path.abspath("can_logs")

router = APIRouter()

# Initialize Jinja2 templates and add a custom filter for base64 encoding.
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.filters["b64encode"] = lambda s: base64.b64encode(s.encode("utf-8")).decode("utf-8")

class ConnectionManager:
    """Manages active WebSocket connections."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def broadcast_channel(self, channel: str, data: Any):
        """Broadcasts a message to all clients on a specific channel."""
        payload = json.dumps({"channel": channel, "data": data})
        await self.broadcast(payload)

manager = ConnectionManager()

def get_service(request: Request) -> Microservice:
    """Helper to get the parent service instance from the request."""
    return request.app.state.service

# --- HTML Page Routes ---

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main App Shell."""
    return templates.TemplateResponse("index.html", {"request": request})

def render_template(request: Request, template_name: str, context: Dict, content_only: bool = False):
    """
    Renders a Jinja2 template, supporting content-only rendering for the App Shell.
    If content_only is True, it sets a variable that templates can use to extend
    a different base template.
    """
    if content_only:
        context["is_content_only"] = True
    return templates.TemplateResponse(template_name, context)

@router.get("/logger/{path:path}", response_class=HTMLResponse)
async def read_logger_path(request: Request, path: str = "", content_only: bool = Query(False)):
    """Serves the logger page, listing files and directories."""
    service = get_service(request)
    files, dirs, extensions = {}, [], []
    try:
        # File system logic to list contents of the CAN logs directory.
        os.makedirs(CAN_LOGS_DIR, exist_ok=True)
        full_path = os.path.normpath(os.path.join(CAN_LOGS_DIR, path))
        if not full_path.startswith(CAN_LOGS_DIR):
            return HTMLResponse("Forbidden", status_code=403)
        items = sorted(os.listdir(full_path))
        files = {item: os.path.getsize(os.path.join(full_path, item)) for item in items if os.path.isfile(os.path.join(full_path, item))}
        dirs = [item for item in items if os.path.isdir(os.path.join(full_path, item))]
        extensions = sorted(list(set(os.path.splitext(f)[1] for f in files)))
    except Exception as e:
        service.logger.error(f"Error reading logger path '{path}': {e}")
    context = {"request": request, "files": files, "dirs": dirs, "extensions": extensions, "current_path": path}
    return render_template(request, "logger.html", context, content_only)

@router.get("/{page}", response_class=HTMLResponse)
async def read_page(request: Request, page: str, content_only: bool = Query(False)):
    """Serves dynamic pages based on the URL path."""
    try:
        context = {"request": request}
        return render_template(request, f"{page}.html", context, content_only)
    except JinjaExceptions.TemplateNotFound:
        return HTMLResponse("Page not found", status_code=404)

# --- Unified WebSocket Endpoint ---

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    The single WebSocket endpoint for all real-time communication.
    It receives messages from the client, routes them to the appropriate
    backend service via NATS based on the 'channel' field.
    """
    service = get_service(websocket)
    await manager.connect(websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                message = json.loads(raw_data)
                channel = message.get("channel")
                data = message.get("data", {})

                # Route messages to the correct NATS subject based on the channel.
                if channel == "can_data":
                    await service.messaging_client.publish("commands.can_bus_service", json.dumps(data).encode())
                elif channel == "gps":
                    await service.messaging_client.publish("commands.gps_service", json.dumps(data).encode())
                elif channel == "settings":
                    # Handle settings requests (get all) and updates.
                    if data.get("command") == "get_all_settings":
                        response = await service.messaging_client.request("settings.get.all", b'', timeout=2.0)
                        all_settings = {"settings": json.loads(response.data)}
                        await manager.broadcast_channel('settings', all_settings)
                    else:
                        for key, setting_data in data.items():
                            command = {"command": "update_setting", "group": setting_data["group"], "key": key, "value": setting_data["value"]}
                            await service.messaging_client.publish("commands.settings_service", json.dumps(command).encode())
                elif channel == "manager":
                    await service.messaging_client.publish("commands.manager", json.dumps(data).encode())
                elif channel == "heartbeat":
                    pass # Client-side keep-alive.

            except json.JSONDecodeError:
                service.logger.error(f"Received invalid JSON from websocket: {raw_data}")
            except Exception as e:
                service.logger.error(f"Error processing command from websocket: {e}", exc_info=True)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        service.logger.info("Client disconnected from WebSocket.")

# --- API Endpoints ---
# (These endpoints handle RESTful requests, e.g., for file downloads and log viewing)

@router.get("/api/logs/{service_name}", response_class=HTMLResponse)
async def get_service_logs(service_name: str, request: Request):
    # ... (existing code)
    pass

@router.get("/download/{file_path_b64:path}")
async def download_file(file_path_b64: str):
    # ... (existing code)
    pass

class FileToConvert(BaseModel):
    name: str
    folder: str

@router.post("/convert")
async def convert_file(file_to_convert: FileToConvert, request: Request):
    # ... (existing code)
    pass
