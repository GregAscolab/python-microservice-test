import asyncio
import nats
import json

async def main():
    nc = await nats.connect("nats://localhost:4222")

    # --- Stop All Services ---
    stop_payload = {
        "command": "stop_all"
    }
    await nc.publish("commands.manager", json.dumps(stop_payload).encode())
    print("Sent stop_all command")

    await asyncio.sleep(2) # Wait for services to stop

    await nc.close()

if __name__ == '__main__':
    asyncio.run(main())
