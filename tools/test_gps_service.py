import asyncio
import nats
import json

async def main():
    """
    A simple NATS client to test the gps_service.
    Subscribes to 'gps' and prints received GeoJSON messages.
    """
    print("Connecting to NATS...")
    try:
        nc = await nats.connect("nats://localhost:4222")
        print("Connected to NATS.")
    except Exception as e:
        print(f"Error connecting to NATS: {e}")
        return

    async def message_handler(msg):
        subject = msg.subject
        data = msg.data.decode()
        print(f"Received a message on '{subject}':")
        try:
            # Pretty print the JSON
            parsed_json = json.loads(data)
            print(json.dumps(parsed_json, indent=2))
        except json.JSONDecodeError:
            print(f"  Could not decode JSON: {data}")

    sub = await nc.subscribe("gps", cb=message_handler)
    print("Subscribed to 'gps'. Waiting for messages... (Press Ctrl+C to stop)")

    # Keep the script running indefinitely
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        await nc.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
