import asyncio
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.app_logger_service.service import AppLoggerService

if __name__ == "__main__":
    service = AppLoggerService()
    asyncio.run(service.run())
