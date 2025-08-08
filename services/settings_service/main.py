import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.settings_service.service import SettingsService

async def main():
    """
    Entry point for the Settings Management Microservice.
    """
    service = SettingsService()
    await service.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Settings service shut down.")
