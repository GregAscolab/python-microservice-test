import asyncio
import nats
import json
import can
import time
import argparse
import boto3
import os
import glob
import random
from botocore.exceptions import NoCredentialsError
from datetime import datetime

def load_settings(path="config/settings.json") -> dict:
    """Loads settings from a JSON file."""
    print(f"Loading settings from {path}...")
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Settings file not found at {path}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {path}")
        return {}

async def send_can_messages(interface: str, channel: str, num_messages: int) -> list[can.Message]:
    """Sends a specified number of CAN messages and returns them."""
    sent_messages = []
    print(f"Starting CAN message sender on bus '{channel}'...")
    try:
        with can.interface.Bus(channel=channel, interface=interface) as bus:
            for i in range(num_messages):
                msg = can.Message(arbitration_id=random.randint(0,255), data=[random.randint(0,255), random.randint(0,255), random.randint(0,255), random.randint(0,255), random.randint(0,255), random.randint(0,255), random.randint(0,255), random.randint(0,255)], is_extended_id=False)
                bus.send(msg)
                sent_messages.append(msg)
                print(f"Sent CAN message {i+1}/{num_messages}={msg.data}")
                await asyncio.sleep(0.0001)
    except Exception as e:
        print(f"Error sending CAN messages: {e}")
    return sent_messages

async def main(args):
    """
    Test script for the CAN recorder functionality.
    - Starts a CAN message sender.
    - Sends commands to start and stop recording.
    """
    nats_client = None
    try:
        # Load settings first
        all_settings = load_settings()
        can_bus_settings = all_settings.get("can_bus_service", {})
        global_settings = all_settings.get("global", {})
        nats_url = global_settings.get("nats_url", "nats://127.0.0.1:8888") # Default for safety

        # Generate a unique filename for this test run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_filename = f"test_log_{timestamp}.blf"

        if not args.no_nats:
            nats_client = await nats.connect(nats_url)
            print(f"Test script connected to NATS at {nats_url}.")
        
            # Send start recording command with the specific filename
            print(f"Sending 'startRecording' command with filename: {test_filename}")
            start_command = {"command": "startRecording", "filename": test_filename}
            await nats_client.publish("commands.can_bus_service", json.dumps(start_command, indent=None, separators=(',',':')).encode())

            # Give the service a moment to initialize the logger
            await asyncio.sleep(2)
        else:
            input("Press Enter to start sending CAN messages...")

        # Start sending CAN messages and wait for them to complete
        num_messages_to_send = args.msg_nb
        sent_messages = await send_can_messages(args.interface, args.channel, num_messages_to_send)
        print("CAN message sending complete.")
        
        # Give a little extra time for the last message to be logged
        await asyncio.sleep(1)
        
        if not args.no_nats:
            # Send stop recording command
            print("Sending 'stopRecording' command...")
            stop_command = {"command": "stopRecording"}
            await nats_client.publish("commands.can_bus_service", json.dumps(stop_command, indent=None, separators=(',',':')).encode())
        else:
            test_filename = input("Enter test filename to continue with verification:")

        if not args.no_local:
            # Verify local log file
            await asyncio.sleep(1)
            local_log_dir = can_bus_settings.get("log_dir", "can_logs")
            local_log_path = os.path.join(local_log_dir, test_filename)
            if os.path.exists(local_log_path):
                verify_log_file(local_log_path, sent_messages)
            else:
                print(f"  [FAIL] Local log file not found at '{local_log_path}'.")

        # Wait for S3 upload to complete
        print("Waiting for S3 upload...")
        await asyncio.sleep(5) # Give the service time to upload

        # Download and verify S3 log file
        s3_download_dir = "s3_downloads"
        downloaded_log_path = download_log_from_s3(can_bus_settings, test_filename, s3_download_dir)

        if downloaded_log_path:
            verify_log_file(downloaded_log_path, sent_messages)
        else:
            print(f"  [FAIL] Could not download '{test_filename}' from S3.")

        # Clean up local and downloaded files
        if not args.no_local:
            if os.path.exists(local_log_path):
                os.remove(local_log_path)

        if downloaded_log_path and os.path.exists(downloaded_log_path):
            os.remove(downloaded_log_path)
        else:
            print("Failed to download log file from S3.")

        print("Test script finished.")
        
    except Exception as e:
        print(f"An error occurred in the test script: {e}")
    finally:
        if nats_client:
            await nats_client.close()
            print("Test script disconnected from NATS.")

def download_log_from_s3(s3_settings: dict, filename: str, download_dir: str) -> str | None:
    """Downloads the most recent CAN log file from S3."""
    print("Connecting to S3 to download log file...")
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=s3_settings.get("s3_endpoint_url"),
            aws_access_key_id=s3_settings.get("s3_access_key"),
            aws_secret_access_key=s3_settings.get("s3_secret_key")
        )

        bucket_name = s3_settings.get("s3_bucket")
        download_path = os.path.join(download_dir, filename)
        os.makedirs(download_dir, exist_ok=True)

        print(f"Downloading '{filename}' from S3 bucket '{bucket_name}' to '{download_path}'...")
        s3_client.download_file(bucket_name, filename, download_path)
        print("Download complete.")
        return download_path

    except NoCredentialsError:
        print("S3 credentials not found. Please configure them.")
        return None
    except Exception as e:
        print(f"Error downloading from S3: {e}")
        return None

def verify_log_file(log_path: str, sent_messages: list[can.Message]):
    """Verifies the contents of a CAN log file."""
    print(f"Verifying log file: {log_path}")
    try:
        log_reader = can.LogReader(log_path)
        logged_messages = list(log_reader)

        if len(logged_messages) != len(sent_messages):
            print(f"  [FAIL] Message count mismatch: Logged={len(logged_messages)}, Sent={len(sent_messages)}")
            return

        print(f"  [PASS] Message count is correct: {len(logged_messages)}")

        for i, (logged_msg, sent_msg) in enumerate(zip(logged_messages, sent_messages)):
            if logged_msg.arbitration_id != sent_msg.arbitration_id or \
               logged_msg.data != sent_msg.data:
                print(f"  [FAIL] Message content mismatch at index {i}:")
                print(f"    Logged: {logged_msg}")
                print(f"    Sent:   {sent_msg}")
                return

        print("  [PASS] All message contents match.")

    except Exception as e:
        print(f"  [FAIL] Error verifying log file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CAN recorder test script.")
    parser.add_argument("--interface", type=str, default="socketcan", help="CAN interface type (e.g., 'virtual', 'socketcan, 'pcan')")
    parser.add_argument("--channel", type=str, default="vcan0", help="CAN channel name (e.g., 'vcan0', 'PCAN_USBBUS1')")
    parser.add_argument("--msg-nb", type=int, default=20000, help="Number of messages to be sent")
    parser.add_argument("--no-nats", action="store_true", help="Disable NATS connection and wait for user confirmation")
    parser.add_argument("--no-local", action="store_true", help="Disable local log file verification")
    args = parser.parse_args()
    asyncio.run(main(args))