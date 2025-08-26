import asyncio
import os
import sys

# Add the project root to the Python path so this script can find other modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import our yet-to-be-created service class
from services.digital_twin_service.service import DigitalTwinService

if __name__ == "__main__":
    # Instantiate the service
    service = DigitalTwinService()
    # Start the service's lifecycle
    asyncio.run(service.run())
