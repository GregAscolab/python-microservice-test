import unittest
import asyncio
from unittest.mock import AsyncMock, patch

import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.compute_service.service import ComputeService
from services.compute_service.computations import RunningAverage, Integrator, Differentiator

class TestGenericComputations(unittest.TestCase):
    def test_running_average(self):
        avg = RunningAverage()
        self.assertEqual(avg.update(10, 0), 10.0)
        self.assertEqual(avg.update(20, 1), 15.0)
        self.assertEqual(avg.update(30, 2), 20.0)

    def test_integrator(self):
        integ = Integrator()
        self.assertEqual(integ.update(10, 0), 0.0) # First point initializes
        self.assertEqual(integ.update(10, 1), 10.0) # Area of rectangle
        self.assertEqual(integ.update(20, 2), 25.0) # 10 + (10+20)/2 * 1

    def test_differentiator(self):
        diff = Differentiator()
        self.assertEqual(diff.update(10, 0), 0.0) # First point initializes
        self.assertEqual(diff.update(20, 1), 10.0) # (20-10)/(1-0)
        self.assertEqual(diff.update(15, 3), -2.5) # (15-20)/(3-1)

class TestComputeServiceIntegration(unittest.TestCase):

    def setUp(self):
        """Set up a new ComputeService instance for each test."""
        self.service = ComputeService()
        self.service.logger.disabled = True
        self.service.messaging_client = AsyncMock()

    def test_register_computation_command(self):
        """Test the command handler for registering computations."""
        args = {
            "source_signal": "can.speed",
            "computation_type": "RunningAverage",
            "output_name": "speed_avg"
        }

        async def run_test():
            await self.service._handle_register_computation(reply="test.reply", **args)

            # Check that the computation was added
            self.assertIn("can.speed", self.service.active_computations)
            comp_info = self.service.active_computations["can.speed"][0]
            self.assertEqual(comp_info['output_name'], 'speed_avg')
            self.assertIsInstance(comp_info['instance'], RunningAverage)

            # Check that a success response was published
            self.service.messaging_client.publish.assert_called_with(
                "test.reply",
                unittest.mock.ANY
            )

        asyncio.run(run_test())

    def test_process_data_and_chaining(self):
        """Test the full data processing pipeline, including chaining."""

        async def run_test():
            # 1. Register an average computation on can.speed
            await self.service._handle_register_computation(
                source_signal="can.speed",
                computation_type="RunningAverage",
                output_name="speed_avg"
            )

            # 2. Register a derivative on the output of the average
            await self.service._handle_register_computation(
                source_signal="speed_avg",
                computation_type="Differentiator",
                output_name="speed_acceleration"
            )

            # 3. Process first data point for can.speed
            await self.service._process_data("can.speed", 10, 0)
            self.assertEqual(self.service.computation_state.get("can.speed"), 10)
            self.assertEqual(self.service.computation_state.get("speed_avg"), 10.0)
            self.assertEqual(self.service.computation_state.get("speed_acceleration"), 0.0)

            # 4. Process second data point for can.speed
            await self.service._process_data("can.speed", 20, 1)
            self.assertEqual(self.service.computation_state.get("can.speed"), 20)
            self.assertEqual(self.service.computation_state.get("speed_avg"), 15.0) # (10+20)/2
            self.assertEqual(self.service.computation_state.get("speed_acceleration"), 5.0) # (15-10)/(1-0)

            # 5. Check if NATS publishes were called for each result
            # Two calls for speed_avg, two for speed_acceleration
            self.assertEqual(self.service.messaging_client.publish.call_count, 4)
            # Check the last call for acceleration
            last_call_args = self.service.messaging_client.publish.call_args
            self.assertEqual(last_call_args.args[0], "compute.result.speed_acceleration")

        asyncio.run(run_test())

    def test_trigger_registration_and_execution(self):
        """Test trigger registration and the execution of its 'publish' action."""
        trigger_def = {
            "name": "test_trigger",
            "conditions": [{"name": "some_signal", "operator": ">", "value": 50}],
            "action": {"type": "publish", "subject": "test.alert"}
        }

        async def run_test():
            # Register the trigger
            await self.service._handle_register_trigger(reply="test.reply", trigger=trigger_def)
            self.assertIn(trigger_def, self.service.triggers)
            self.service.messaging_client.publish.assert_called_with("test.reply", unittest.mock.ANY)
            self.service.messaging_client.publish.reset_mock()

            # Process data that does NOT meet the condition
            await self.service._process_data("some_signal", 40, 0)
            # Publish should not be called for the trigger action
            self.service.messaging_client.publish.assert_not_called()

            # Process data that DOES meet the condition
            await self.service._process_data("some_signal", 60, 1)
            # Publish should be called for the trigger action
            self.service.messaging_client.publish.assert_any_call("test.alert", unittest.mock.ANY)

        asyncio.run(run_test())

    def test_unregister_functionality(self):
        """Test unregistering computations and triggers."""
        async def run_test():
            # Register a computation and a trigger
            await self.service._handle_register_computation(
                reply="r1",
                source_signal="can.temp",
                computation_type="RunningAverage",
                output_name="temp_avg"
            )
            await self.service._handle_register_trigger(reply="r2", trigger={
                "name": "temp_trigger",
                "conditions": [{"name": "temp_avg", "operator": ">", "value": 100}],
                "action": {"type": "publish", "subject": "temp.alert"}
            })

            # Verify they exist
            self.assertTrue(any(c['output_name'] == 'temp_avg' for c in self.service.active_computations['can.temp']))
            self.assertTrue(any(t['name'] == 'temp_trigger' for t in self.service.triggers))

            # Unregister them and check for success replies
            await self.service._handle_unregister_computation(reply="r3", output_name="temp_avg")
            self.service.messaging_client.publish.assert_any_call("r3", unittest.mock.ANY)

            await self.service._handle_unregister_trigger(reply="r4", name="temp_trigger")
            self.service.messaging_client.publish.assert_any_call("r4", unittest.mock.ANY)

            # Verify they are gone
            self.assertFalse(any(c['output_name'] == 'temp_avg' for c in self.service.active_computations.get('can.temp', [])))
            self.assertFalse(any(t['name'] == 'temp_trigger' for t in self.service.triggers))

        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
