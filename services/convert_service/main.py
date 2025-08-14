import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.convert_service.service import ConvertService

if __name__ == "__main__":
    service = ConvertService()
    asyncio.run(service.run())
