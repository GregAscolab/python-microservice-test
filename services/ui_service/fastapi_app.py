from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import exceptions as JinjaExceptions
import json
import os
import sys
import base64
from typing import List, Dict, Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from common.microservice import Microservice

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "frontend", "static")
TEMPLATES_DIR = os.path.join(APP_DIR, "frontend", "templates")
CAN_LOGS_DIR = os.path.abspath("can_logs")

router = APIRouter()

templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.filters["b64encode"] = lambda s: base64.b64encode(s.encode("utf-8")).decode("utf-8")

class ConnectionManager:
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
        """Broadcasts a message to all clients, specifying the channel."""
        payload = json.dumps({"channel": channel, "data": data})
        await self.broadcast(payload)


manager = ConnectionManager()

def get_service(request: Request) -> Microservice:
    return request.app.state.service

# --- HTML Page Routes ---

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

def render_template(request: Request, template_name: str, context: Dict, content_only: bool = False):
    if content_only:
        context["is_content_only"] = True
    return templates.TemplateResponse(template_name, context)


@router.get("/logger/{path:path}", response_class=HTMLResponse)
async def read_logger_path(request: Request, path: str = "", content_only: bool = Query(False)):
    service = get_service(request)
    files, dirs, extensions = {}, [], []
    try:
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
    try:
        context = {"request": request}
        return render_template(request, f"{page}.html", context, content_only)
    except JinjaExceptions.TemplateNotFound:
        return HTMLResponse("Page not found", status_code=404)


# --- Unified WebSocket Endpoint ---

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    service = get_service(websocket)
    await manager.connect(websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                message = json.loads(raw_data)
                channel = message.get("channel")
                data = message.get("data", {})

                if channel == "can_data":
                    await service.messaging_client.publish("commands.can_bus_service", json.dumps(data).encode())

                elif channel == "gps":
                    await service.messaging_client.publish("commands.gps_service", json.dumps(data).encode())

                elif channel == "settings":
                    if data.get("command") == "get_all_settings":
                        response = await service.messaging_client.request("settings.get.all", b'', timeout=2.0)
                        all_settings = {"settings": json.loads(response.data)}
                        await manager.broadcast_channel('settings', all_settings)
                    else: # Must be a settings update
                        for key, setting_data in data.items():
                            command = {
                                "command": "update_setting",
                                "group": setting_data["group"],
                                "key": key,
                                "value": setting_data["value"]
                            }
                            await service.messaging_client.publish("commands.settings_service", json.dumps(command).encode())

                elif channel == "manager":
                    await service.messaging_client.publish("commands.manager", json.dumps(data).encode())

                elif channel == "heartbeat":
                    # Simple keep-alive
                    pass

            except json.JSONDecodeError:
                service.logger.error(f"Received invalid JSON from websocket: {raw_data}")
            except Exception as e:
                service.logger.error(f"Error processing command from websocket: {e}", exc_info=True)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        service.logger.info("Client disconnected from WebSocket.")


# --- API Endpoints ---

LOGS_DIR = os.path.abspath("logs")

@router.get("/api/logs/{service_name}", response_class=HTMLResponse)
async def get_service_logs(service_name: str, request: Request):
    service = get_service(request)
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_file_path = os.path.normpath(os.path.join(LOGS_DIR, f"{service_name}.log"))
        if not os.path.abspath(log_file_path).startswith(LOGS_DIR):
            return HTMLResponse("Forbidden: Access to this path is not allowed.", status_code=403)
        if not os.path.exists(log_file_path):
            return HTMLResponse(f"Log file for '{service_name}' not found.", status_code=404)

        file_size = os.path.getsize(log_file_path)
        read_size = 16384
        with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
            if file_size > read_size:
                f.seek(file_size - read_size)
                f.readline()
            content = f.read()
            return HTMLResponse(content, media_type="text/plain")
    except Exception as e:
        service.logger.error(f"Error reading log for service '{service_name}': {e}", exc_info=True)
        return HTMLResponse(f"An error occurred while trying to read the log file.", status_code=500)


@router.get("/download/{file_path_b64:path}")
async def download_file(file_path_b64: str):
    try:
        file_path = base64.b64decode(file_path_b64.encode("utf-8")).decode("utf-8")
        full_path = os.path.normpath(os.path.join(CAN_LOGS_DIR, file_path))
        if not full_path.startswith(CAN_LOGS_DIR):
            return HTMLResponse("Forbidden", status_code=403)
        if os.path.exists(full_path):
            return FileResponse(full_path, filename=os.path.basename(full_path))
        return HTMLResponse("File not found", status_code=404)
    except Exception:
        return HTMLResponse("Invalid file path", status_code=400)

class FileToConvert(BaseModel):
    name: str
    folder: str

@router.post("/convert")
async def convert_file(file_to_convert: FileToConvert, request: Request):
    service = get_service(request)
    service.logger.info(f"Queueing conversion for file: {file_to_convert.name} in folder {file_to_convert.folder}")
    try:
        command = {
            "command": "blfToTimeseries",
            "filename": file_to_convert.name,
            "folder": file_to_convert.folder
        }
        await service.messaging_client.publish("commands.convert_service", json.dumps(command).encode())
        return {"status": "queued", "filename": file_to_convert.name}
    except Exception as e:
        service.logger.error(f"Error queueing file conversion: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to queue conversion"}
