import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.manager.service import ManagerService

async def main():
    """
    Entry point for the Microservice Manager.
    """
    service = ManagerService()
    await service.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Manager service shut down.")
