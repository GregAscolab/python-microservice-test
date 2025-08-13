import asyncio
import nats
import json
import can
import time
import argparse
import boto3
import os
import glob
from botocore.exceptions import NoCredentialsError

def load_settings(path="config/settings-linux.json") -> dict:
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
                msg = can.Message(arbitration_id=100, data=[0xE8, 0x03, 0xAF, 0x0D, 0, 0, 0, 0], is_extended_id=False)
                bus.send(msg)
                sent_messages.append(msg)
                print(f"Sent CAN message {i+1}/{num_messages}")
                await asyncio.sleep(0.1)
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
        nats_url = global_settings.get("nats_url", "nats://localhost:8888") # Default for safety

        nats_client = await nats.connect(nats_url)
        print(f"Test script connected to NATS at {nats_url}.")
        
        num_messages_to_send = 20
        
        # Start sending CAN messages in the background
        sender_task = asyncio.create_task(send_can_messages(args.interface, args.channel, num_messages_to_send))
        
        # Give the sender a moment to start
        await asyncio.sleep(1)
        
        # Send start recording command
        print("Sending 'startRecording' command...")
        start_command = {"command": "startRecording"}
        await nats_client.publish("commands.can_bus_service", json.dumps(start_command, indent=None, separators=(',',':')).encode())
        
        # Wait for all messages to be sent
        sent_messages = await sender_task
        print("CAN message sending complete.")
        
        # Give a little extra time for the last message to be logged
        await asyncio.sleep(1)
        
        # Send stop recording command
        print("Sending 'stopRecording' command...")
        stop_command = {"command": "stopRecording"}
        await nats_client.publish("commands.can_bus_service", json.dumps(stop_command, indent=None, separators=(',',':')).encode())
        
        # Verify local log file
        local_log_dir = "can_logs"
        latest_local_log = get_latest_log_file(local_log_dir)
        if latest_local_log:
            verify_log_file(latest_local_log, sent_messages)
        else:
            print(f"No local log file found in '{local_log_dir}'.")

        # Wait for S3 upload and verify
        s3_download_dir = "s3_downloads"
        downloaded_log_path = None

        for i in range(10): # Try for 10 seconds
            downloaded_log_path = download_latest_log_from_s3(can_bus_settings, s3_download_dir)
            if downloaded_log_path:
                break
            await asyncio.sleep(1)
        
        if downloaded_log_path:
            verify_log_file(downloaded_log_path, sent_messages)
            # Clean up
            if latest_local_log and os.path.exists(latest_local_log):
                os.remove(latest_local_log)
            if os.path.exists(downloaded_log_path):
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

def get_latest_log_file(log_dir: str, prefix="can_log_") -> str | None:
    """Gets the path of the most recent log file in a directory."""
    try:
        list_of_files = glob.glob(os.path.join(log_dir, f"{prefix}*"))
        if not list_of_files:
            return None
        return max(list_of_files, key=os.path.getctime)
    except Exception as e:
        print(f"Error getting latest log file: {e}")
        return None

def download_latest_log_from_s3(s3_settings: dict, download_dir: str) -> str | None:
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
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix="can_log_")
        if 'Contents' not in response:
            print(f"No log files found in S3 bucket '{bucket_name}'.")
            return None

        all_logs = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
        latest_log = all_logs[0]
        latest_log_name = latest_log['Key']

        download_path = os.path.join(download_dir, latest_log_name)
        os.makedirs(download_dir, exist_ok=True)

        print(f"Downloading '{latest_log_name}' from S3 to '{download_path}'...")
        s3_client.download_file(bucket_name, latest_log_name, download_path)
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
    parser.add_argument("--interface", type=str, default="virtual", help="CAN interface type (e.g., 'virtual', 'pcan')")
    parser.add_argument("--channel", type=str, default="vcan0", help="CAN channel name (e.g., 'vcan0', 'PCAN_USBBUS1')")
    args = parser.parse_args()
    asyncio.run(main(args))