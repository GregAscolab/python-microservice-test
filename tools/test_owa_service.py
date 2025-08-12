import asyncio
import nats
import json

async def main():
    """
    A simple NATS client to test the owa_service.
    Subscribes to 'owa.status' and prints received messages.
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
        print(f"Received a message on '{subject}': {data}")
        try:
            status = json.loads(data)
            if status.get("status") == "ready":
                print("SUCCESS: owa_service reported ready status.")
                # We can choose to exit after receiving the ready signal
                # or keep listening. For a simple test, we'll exit.
                asyncio.create_task(nc.close())
        except json.JSONDecodeError:
            print("ERROR: Could not decode JSON from message.")


    sub = await nc.subscribe("owa.status", cb=message_handler)
    print("Subscribed to 'owa.status'. Waiting for messages...")

    # Keep the script running until the connection is closed
    await nc.closed_cb

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
