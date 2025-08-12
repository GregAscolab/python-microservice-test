import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.owa_service.service import OwaService

async def main():
    """
    Main entry point for the OWA Service.
    """
    service = OwaService()
    await service.run()

if __name__ == "__main__":
    # Set up and run the asyncio event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Service terminated by user.")
