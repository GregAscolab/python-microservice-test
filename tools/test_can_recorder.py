import asyncio
import nats
import json
import can
import time

async def send_can_messages(channel: str, num_messages: int):
    """Sends a specified number of CAN messages to the virtual bus."""
    print(f"Starting CAN message sender on bus '{channel}'...")
    try:
        with can.interface.Bus(channel=channel, interface='virtual') as bus:
            for i in range(num_messages):
                # Using arbitration ID 100, which is 'MotorInfo' in sample.dbc
                # Temp: 60C -> (60 - (-40)) / 0.1 = 1000
                # RPM: 3500 -> 3500 / 1 = 3500
                # Data: 0x03E8 for temp, 0x0DAF for RPM
                msg = can.Message(arbitration_id=100, data=[0xE8, 0x03, 0xAF, 0x0D, 0, 0, 0, 0])
                bus.send(msg)
                print(f"Sent CAN message {i+1}/{num_messages}")
                await asyncio.sleep(0.1)
    except Exception as e:
        print(f"Error sending CAN messages: {e}")

async def main():
    """
    Test script for the CAN recorder functionality.
    - Starts a CAN message sender.
    - Sends commands to start and stop recording.
    """
    nats_client = None
    try:
        nats_client = await nats.connect("nats://localhost:8888")
        print("Test script connected to NATS.")
        
        num_messages_to_send = 20
        
        # Start sending CAN messages in the background
        sender_task = asyncio.create_task(send_can_messages('vcan0', num_messages_to_send))
        
        # Give the sender a moment to start
        await asyncio.sleep(1)
        
        # Send start recording command
        print("Sending 'startRecording' command...")
        start_command = {"command": "startRecording"}
        await nats_client.publish("commands.can_bus_service", json.dumps(start_command, indent=None, separators=(',',':')).encode())
        
        # Wait for all messages to be sent
        await sender_task
        print("CAN message sending complete.")
        
        # Give a little extra time for the last message to be logged
        await asyncio.sleep(1)
        
        # Send stop recording command
        print("Sending 'stopRecording' command...")
        stop_command = {"command": "stopRecording"}
        await nats_client.publish("commands.can_bus_service", json.dumps(stop_command, indent=None, separators=(',',':')).encode())
        
        # Wait for upload to complete (in a real scenario, we'd need a confirmation)
        print("Waiting for S3 upload...")
        await asyncio.sleep(5)
        
        print("Test script finished.")
        
    except Exception as e:
        print(f"An error occurred in the test script: {e}")
    finally:
        if nats_client:
            await nats_client.close()
            print("Test script disconnected from NATS.")

if __name__ == "__main__":
    asyncio.run(main())