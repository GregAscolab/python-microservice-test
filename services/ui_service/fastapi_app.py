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
import base64

# Add the project root to the Python path to allow for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from common.microservice import Microservice

# --- Absolute Path Setup ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(APP_DIR, "frontend", "templates")
CAN_LOGS_DIR = os.path.abspath("can_logs")

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def b64encode(input:str):
    return base64.b64encode(input.encode("utf-8")).decode("utf-8")
templates.env.filters["b64encode"] = b64encode


def get_service(request: Request) -> Microservice:
    return request.app.state.service

# --- HTML Page Routes ---
@router.get("/{page}", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- API Endpoints ---

@router.get("/api/logger/files/{path:path}", response_class=HTMLResponse)
async def list_files(request: Request, path: str = ""):
    service = get_service(request)
    try:
        # Security check to prevent path traversal
        safe_path = os.path.normpath(os.path.join(CAN_LOGS_DIR, path))
        if not safe_path.startswith(CAN_LOGS_DIR):
            return HTMLResponse("Forbidden", status_code=403)

        os.makedirs(safe_path, exist_ok=True)
        items = sorted(os.listdir(safe_path))  # Sort items alphabetically

        files = [{"name": item, "size": os.path.getsize(os.path.join(safe_path, item)), "type": "file"} for item in items if os.path.isfile(os.path.join(safe_path, item))]
        dirs = [{"name": item, "type": "dir"} for item in items if os.path.isdir(os.path.join(safe_path, item))]

        response_data = {"path": path, "contents": dirs + files}
        return HTMLResponse(content=json.dumps(response_data), media_type="application/json")

    except Exception as e:
        service.logger.error(f"Error listing files for logger path '{path}': {e}")
        return HTMLResponse(content=json.dumps({"error": str(e)}), status_code=500, media_type="application/json")


@router.get("/api/logs/{service_name}", response_class=HTMLResponse)
async def get_service_logs(service_name: str, request: Request):
    log_file_path = os.path.normpath(os.path.join(os.path.abspath("logs"), f"{service_name}.log"))
    if not os.path.abspath(log_file_path).startswith(os.path.abspath("logs")):
        return HTMLResponse("Forbidden", status_code=403)
    if not os.path.exists(log_file_path):
        return HTMLResponse(f"Log file for '{service_name}' not found.", status_code=404)
    with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
        file_size = os.path.getsize(log_file_path)
        read_size = 16384
        if file_size > read_size:
            f.seek(file_size - read_size)
            f.readline()
        content = f.read()
        return HTMLResponse(content, media_type="text/plain")

@router.get("/download/{file_path_b64:path}")
async def download_file(file_path_b64: str):
    file_path = base64.b64decode(file_path_b64.encode("utf-8")).decode("utf-8")
    full_path = os.path.normpath(os.path.join(CAN_LOGS_DIR, file_path))
    if not full_path.startswith(CAN_LOGS_DIR):
        return HTMLResponse("Forbidden", status_code=403)
    if os.path.exists(full_path):
        return FileResponse(full_path, filename=os.path.basename(full_path))
    return HTMLResponse("File not found", status_code=404)

class FileToConvert(BaseModel):
    name: str
    folder: str

@router.post("/convert")
async def convert_file(file_content: FileToConvert, request: Request):
    command = {"command": "blfToTimeseries", "filename": file_content.name, "folder": file_content.folder}
    await get_service(request).messaging_client.publish("commands.convert_service", json.dumps(command).encode())
    return {"status": "queued", "filename": file_content.name}
