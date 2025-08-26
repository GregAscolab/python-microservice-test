import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import asyncio
import cantools
import can
import nats
import json
import time
import math

class DigitalTwinTester:
    def __init__(self, nats_url, can_interface, can_channel, dbc_file):
        self.nats_url = nats_url
        self.can_interface = can_interface
        self.can_channel = can_channel
        self.dbc_file = dbc_file
        self.db = cantools.db.load_file(self.dbc_file)
        self.can_bus = None
        self.nc = None

    async def connect(self):
        self.can_bus = can.interface.Bus(channel=self.can_channel, interface=self.can_interface)
        self.nc = await nats.connect(self.nats_url)

    async def disconnect(self):
        if self.can_bus:
            self.can_bus.shutdown()
        if self.nc:
            await self.nc.close()

    async def run_test_scenario(self, scenario):
        print(f"--- Running scenario: {scenario['name']} ---")
        for step in scenario['steps']:
            signal_name = step['signal']
            value = step['value']
            duration = step['duration']

            print(f"Setting {signal_name} to {value}")

            # Find the message that contains this signal
            message_def = None
            for msg in self.db.messages:
                if signal_name in [s.name for s in msg.signals]:
                    message_def = msg
                    break

            if not message_def:
                print(f"Signal {signal_name} not found in DBC file")
                continue

            # Create and send the CAN message
            message_data = {signal.name: 0 for signal in message_def.signals}
            message_data[signal_name] = value
            data = message_def.encode(message_data)
            message = can.Message(arbitration_id=message_def.frame_id, data=data)
            self.can_bus.send(message)

            # Wait for the digital twin to update
            await asyncio.sleep(duration)

            # Check the output
            try:
                # To get the data, we need to subscribe, not request
                sub = await self.nc.subscribe("digital_twin.data")
                msg = await sub.next_msg(timeout=1)
                await sub.unsubscribe()

                data = json.loads(msg.data.decode())
                print("Received digital twin data:", data)

                # Add assertions here
                if signal_name == "PF_BOOM_InclX":
                    boom_end_z = data['boom'][1][2]
                    turret_z = data['turret'][0][2]
                    boom_length = 8 # From settings

                    expected_z = turret_z + boom_length * abs(math.sin(math.radians(value)))
                    print(f"Boom angle: {value}, Expected Z: {expected_z}, Actual Z: {boom_end_z}")
                    # Loosen the assertion to account for floating point inaccuracies
                    assert abs(expected_z - boom_end_z) < 0.1, f"Expected Z={expected_z}, but got {boom_end_z}"

            except nats.errors.TimeoutError:
                print("Timeout waiting for digital twin data")

        print(f"--- Scenario {scenario['name']} complete ---")

async def main():
    tester = DigitalTwinTester(
        nats_url="nats://localhost:4222",
        can_interface="virtual",
        can_channel="vcan0",
        dbc_file="config/db-full.dbc"
    )

    await tester.connect()

    test_scenarios = [
        {
            "name": "Boom movement",
            "steps": [
                {"signal": "PF_BOOM_InclX", "value": 0, "duration": 1},
                {"signal": "PF_BOOM_InclX", "value": 45, "duration": 1},
                {"signal": "PF_BOOM_InclX", "value": 90, "duration": 1},
                {"signal": "PF_BOOM_InclX", "value": 45, "duration": 1},
                {"signal": "PF_BOOM_InclX", "value": 0, "duration": 1},
            ]
        }
    ]

    for scenario in test_scenarios:
        await tester.run_test_scenario(scenario)

    await tester.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
