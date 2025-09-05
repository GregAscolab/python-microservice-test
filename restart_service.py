import asyncio
import nats
import json

async def main():
    nc = await nats.connect("nats://localhost:4222")

    # --- Restart app_logger_service ---
    payload = {
        "command": "restart_service",
        "service_name": "app_logger_service"
    }
    await nc.publish("commands.manager", json.dumps(payload).encode())
    print("Sent restart_service command for app_logger_service")

    await nc.close()

if __name__ == '__main__':
    asyncio.run(main())
