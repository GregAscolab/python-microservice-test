import asyncio
from services.manager import main as manager_main

if __name__ == "__main__":
    print("Starting the microservice application...")
    try:
        asyncio.run(manager_main.main())
    except KeyboardInterrupt:
        print("Application shut down by user.")
    print("Application has been shut down.")
