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
# This ensures that file paths are correct regardless of the working directory
APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "frontend", "static")
TEMPLATES_DIR = os.path.join(APP_DIR, "frontend", "templates")
# Use an absolute path for the main log directory as well
LOGS_DIR = os.path.abspath("logs")
CAN_LOGS_DIR = os.path.abspath("can_logs")
APP_LOGS_DIR = os.path.abspath("app_logs")
FAVICON_PATH = os.path.join(APP_DIR, "frontend", "static", "images", "favicon.ico")

# We use an APIRouter now, which will be included by the main app in service.py
router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def b64encode(input:str):
    return base64.b64encode(input.encode("utf-8")).decode("utf-8")
templates.env.filters["b64encode"] = b64encode

# --- Helper function to get the parent service ---
def get_service(request: Request) -> Microservice:
    return request.app.state.service

@router.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(FAVICON_PATH)

# --- HTML Page Routes ---
@router.get("/{page}", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- API Endpoints ---
def getServiceNameFolder(service_name:str) -> str|None:
    folder_path = None
    if service_name == "logger":
        folder_path = CAN_LOGS_DIR
    elif service_name == "app_logger":
        folder_path = APP_LOGS_DIR
    else:
        pass
        # folder_path = None

    return folder_path

@router.get("/api/files/{service_name}/{path:path}", response_class=HTMLResponse)
async def list_files(request: Request, service_name:str, path: str = ""):
    folder_path = getServiceNameFolder(service_name)
    if not folder_path:
        return HTMLResponse(f"Unknowed service name: {service_name}", status_code=404)
    
    service = get_service(request)
    try:
        # Security check to prevent path traversal
        safe_path = os.path.normpath(os.path.join(folder_path, path))
        if not safe_path.startswith(folder_path):
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

@router.get("/api/file/{service_name}/{filename}")
async def get_app_log_content(service_name:str, filename: str, request: Request):
    folder_path = getServiceNameFolder(service_name)
    if not folder_path:
        return HTMLResponse(f"Unknowed service name: {service_name}", status_code=404)
    
    service = get_service(request)
    try:
        log_file_path = os.path.normpath(os.path.join(folder_path, filename))
        if not os.path.abspath(log_file_path).startswith(folder_path):
            return HTMLResponse("Forbidden", status_code=403)

        if not os.path.exists(log_file_path):
            return HTMLResponse("File not found", status_code=404)

        with open(log_file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            return content
    except Exception as e:
        service.logger.error(f"Error reading app log file '{filename}': {e}", exc_info=True)
        return HTMLResponse("Error reading file", status_code=500)

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

@router.get("/api/download/{service_name}/{file_path_b64:path}")
async def download_file(service_name:str, file_path_b64: str):
    folder_path = getServiceNameFolder(service_name)
    if not folder_path:
        return HTMLResponse(f"Unknowed service name: {service_name}", status_code=404)
    
    file_path = base64.b64decode(file_path_b64.encode("utf-8")).decode("utf-8")
    full_path = os.path.normpath(os.path.join(folder_path, file_path))
    if not full_path.startswith(folder_path):
        return HTMLResponse("Forbidden", status_code=403)

    if os.path.exists(full_path):
        return FileResponse(full_path, filename=os.path.basename(full_path))
    return HTMLResponse(f"File not found: {full_path}", status_code=404)

class FileToConvert(BaseModel):
    name: str
    folder: str

@router.post("/api/convert")
async def convert_file(file_content: FileToConvert, request: Request):
    service = get_service(request)
    service.logger.info(f"Queueing conversion for file: {file_content.name} in folder {file_content.folder}")

    try:
        command = {
            "command": "blfToTimeseries",
            "filename": file_content.name,
            "folder": file_content.folder
        }
        await service.messaging_client.publish(
            "commands.convert_service",
            json.dumps(command).encode()
        )
        return {"status": "queued", "filename": file_content.name}
    except Exception as e:
        service.logger.error(f"Error queueing file conversion: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to queue conversion"}
