import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.can_bus_service.service import CanBusService

async def main():
    """
    Entry point for the CAN Bus Microservice.
    """
    service = CanBusService()
    await service.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("CAN bus service shut down.")
