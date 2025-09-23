import asyncio
import nats
import json

async def main():
    nc = await nats.connect("nats://localhost:4222")

    # --- Start Recording ---
    start_payload = {
        "command": "start",
        "hardness": "123",
        "testName": "MyTest",
        "comments": "This is a test."
    }
    await nc.publish("commands.app_logger_service", json.dumps(start_payload).encode())
    print("Sent start command")

    await asyncio.sleep(2)  # Wait for the service to process the start command

    # --- Stop Recording ---
    stop_payload = {
        "command": "stop"
    }
    await nc.publish("commands.app_logger_service", json.dumps(stop_payload).encode())
    print("Sent stop command")

    await asyncio.sleep(2) # Wait for the service to process the stop command and write the file

    await nc.close()

if __name__ == '__main__':
    asyncio.run(main())
