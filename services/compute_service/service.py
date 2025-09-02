import asyncio
import json
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

from collections import defaultdict
import operator
from services.compute_service.computations import RunningAverage, Integrator, Differentiator

class ComputeService(Microservice):
    def __init__(self):
        # Call the parent constructor with the official service name
        super().__init__("compute_service")
        self.computation_state = {}
        self.triggers = []
        self.status = "INITIALIZING"
        # Maps an input signal name (e.g., "can_data.PF_EngineSpeed") to a list of computation instances.
        self.active_computations = defaultdict(list)

        self.available_computations = {
            "RunningAverage": RunningAverage,
            "Integrator": Integrator,
            "Differentiator": Differentiator,
        }
        self.operator_map = {
            '>': operator.gt,
            '<': operator.lt,
            '==': operator.eq,
            '!=': operator.ne,
            '>=': operator.ge,
            '<=': operator.le,
        }

    async def _handle_register_computation(self, args):
        """Command handler to dynamically register a new computation."""
        source_signal = args.get("source_signal")
        computation_type = args.get("computation_type")
        output_name = args.get("output_name")

        if not all([source_signal, computation_type, output_name]):
            return {"status": "error", "message": "Missing 'source_signal', 'computation_type', or 'output_name'."}

        if computation_type not in self.available_computations:
            return {"status": "error", "message": f"Unknown computation type: {computation_type}"}

        # Create a new instance of the requested computation class
        computation_class = self.available_computations[computation_type]
        computation_instance = computation_class()

        # Store it with its output name for later use
        computation_to_store = {
            "instance": computation_instance,
            "output_name": output_name
        }

        self.active_computations[source_signal].append(computation_to_store)
        self.logger.info(f"Registered new computation: '{output_name}' ({computation_type}) on source '{source_signal}'.")
        return {"status": "ok", "message": "Computation registered successfully."}

    async def _publish_status(self, status: str | None = None):
        """Publishes the service's current status."""
        if status:
            self.status = status

        status_payload = {"service": self.service_name, "status": self.status, "timestamp": datetime.now().isoformat()}
        await self.messaging_client.publish(f"compute.status", json.dumps(status_payload).encode())
        self.logger.info(f"Published status: {self.status}")

    async def _handle_register_trigger(self, args):
        """Command handler to dynamically register a new trigger."""
        trigger = args.get("trigger")
        if not trigger or 'name' not in trigger or 'conditions' not in trigger or 'action' not in trigger:
            return {"status": "error", "message": "Invalid trigger structure. Required fields: name, conditions, action."}

        # Simple validation of the action block
        action = trigger['action']
        if 'type' not in action or 'subject' not in action:
            return {"status": "error", "message": "Invalid action structure. Required fields: type, subject."}

        # To prevent duplicate trigger names, we can replace existing ones.
        self.triggers = [t for t in self.triggers if t.get('name') != trigger.get('name')]
        self.triggers.append(trigger)

        self.logger.info(f"Registered trigger: {trigger.get('name')}")
        return {"status": "ok", "message": "Trigger registered successfully."}

    async def _handle_unregister_computation(self, args):
        """Command handler to unregister a computation by its output name."""
        output_name_to_remove = args.get("output_name")
        if not output_name_to_remove:
            return {"status": "error", "message": "Missing 'output_name'."}

        found = False
        for source_signal, computations in self.active_computations.items():
            initial_len = len(computations)
            self.active_computations[source_signal] = [
                comp for comp in computations if comp.get("output_name") != output_name_to_remove
            ]
            if len(self.active_computations[source_signal]) < initial_len:
                found = True
                break # Assuming output names are unique, we can stop

        if found:
            # Also remove the final value from the main state dictionary
            if output_name_to_remove in self.computation_state:
                del self.computation_state[output_name_to_remove]
            self.logger.info(f"Unregistered computation with output: {output_name_to_remove}")
            return {"status": "ok", "message": "Computation unregistered."}
        else:
            return {"status": "error", "message": f"Computation with output '{output_name_to_remove}' not found."}

    async def _handle_unregister_trigger(self, args):
        """Command handler to unregister a trigger by its name."""
        trigger_name_to_remove = args.get("name")
        if not trigger_name_to_remove:
            return {"status": "error", "message": "Missing trigger 'name'."}

        initial_len = len(self.triggers)
        self.triggers = [t for t in self.triggers if t.get('name') != trigger_name_to_remove]

        if len(self.triggers) < initial_len:
            self.logger.info(f"Unregistered trigger: {trigger_name_to_remove}")
            return {"status": "ok", "message": "Trigger unregistered."}
        else:
            return {"status": "error", "message": f"Trigger '{trigger_name_to_remove}' not found."}

    async def _handle_get_available_signals(self, args):
        """Returns a list of all available signals for computation."""
        return {"status": "ok", "signals": list(self.computation_state.keys())}

    async def _start_logic(self):
        """This is called when the service starts."""
        self.logger.info("Compute service starting up...")
        await self.get_settings()
        await self._publish_status("STARTING")

        # Register command handlers
        self.command_handler.register_command("register_computation", self._handle_register_computation)
        self.command_handler.register_command("unregister_computation", self._handle_unregister_computation)
        self.command_handler.register_command("register_trigger", self._handle_register_trigger)
        self.command_handler.register_command("unregister_trigger", self._handle_unregister_trigger)
        self.command_handler.register_command("get_available_signals", self._handle_get_available_signals)
        await self._subscribe_to_commands()

        # Subscribe to data sources
        await self.messaging_client.subscribe("can_data", self._nats_data_handler("can_data"))
        await self.messaging_client.subscribe("digital_twin.data", self._nats_data_handler("digital_twin.data"))
        self.logger.info("Subscribed to data sources.")

        # Start the periodic state publisher
        self.state_publisher_task = asyncio.create_task(self._publish_full_state_loop())

        await self._publish_status("RUNNING")

    async def _publish_full_state_loop(self):
        """Periodically publishes the full state of the service for the UI."""
        publish_interval = self.settings.get("ui_publish_interval", 1.0)
        while True:
            try:
                # In the future, we can add trigger status here as well
                payload = {
                    "computation_state": self.computation_state,
                    "triggers": [t.get("name", "Unnamed") for t in self.triggers] # Just names for now
                }
                await self.messaging_client.publish(f"compute.state.full", json.dumps(payload).encode())
                await asyncio.sleep(publish_interval)
            except asyncio.CancelledError:
                self.logger.info("State publisher task cancelled.")
                break
            except Exception as e:
                self.logger.error(f"Error in state publisher loop: {e}", exc_info=True)
                await asyncio.sleep(publish_interval) # Wait before retrying

    def _nats_data_handler(self, nats_source: str):
        """Returns an async function to handle incoming NATS messages."""
        async def handler(msg):
            try:
                data = json.loads(msg.data.decode())

                # For CAN-like data with a 'name' field
                if 'name' in data and 'value' in data:
                    signal_name = f"{nats_source}.{data['name']}"
                    value = data['value']
                    timestamp = data.get('ts', datetime.now().timestamp() * 1000) / 1000.0
                    await self._process_data(signal_name, value, timestamp)
                # For other data (like digital twin)
                else:
                    # This will process the entire JSON object as a single "value"
                    # which might be useful for some computations (e.g., a trigger on a complex object)
                    await self._process_data(nats_source, data, datetime.now().timestamp())

            except json.JSONDecodeError:
                self.logger.error(f"Failed to decode JSON from source '{nats_source}'")
            except Exception as e:
                self.logger.error(f"Error in NATS data handler for '{nats_source}': {e}", exc_info=True)
        return handler

    async def _process_data(self, signal_name: str, value: any, timestamp: float):
        """
        Processes a single piece of data, updates state, and triggers further computations.
        This is the core of the chaining mechanism.
        """
        self.logger.debug(f"Processing: {signal_name} = {value}")

        # 1. Update the global computation state
        self.computation_state[signal_name] = value

        # 2. Find and execute all computations that use this signal as an input
        if signal_name in self.active_computations:
            for comp_info in self.active_computations[signal_name]:
                instance = comp_info["instance"]
                output_name = comp_info["output_name"]

                try:
                    # The computation's update method performs the calculation
                    new_value = instance.update(value, timestamp)

                    # Publish the individual result
                    result_payload = {"value": new_value, "timestamp": datetime.now().isoformat()}
                    await self.messaging_client.publish(f"compute.result.{output_name}", json.dumps(result_payload).encode())

                    # 3. Recursively call _process_data with the new result
                    # This is what enables chaining computations.
                    await self._process_data(output_name, new_value, timestamp)

                except Exception as e:
                    self.logger.error(f"Error running computation '{output_name}': {e}", exc_info=True)

        # 4. After all processing for this data point is done, evaluate triggers
        await self._evaluate_triggers()


    async def _evaluate_triggers(self):
        """Evaluate all registered triggers against the current computation state."""
        # This method remains largely the same, but we might want to enhance it later
        # to handle stateful triggers (e.g., only fire once).
        for trigger in self.triggers:
            try:
                conditions_met = []
                for condition in trigger.get("conditions", []):
                    signal_name = condition.get("name")
                    operator_str = condition.get("operator")
                    threshold_value = condition.get("value")

                    if signal_name not in self.computation_state:
                        conditions_met.append(False)
                        continue # A condition can't be met if the signal doesn't exist yet

                    current_value = self.computation_state[signal_name]
                    op_func = self.operator_map.get(operator_str)

                    if op_func is None:
                        self.logger.warning(f"Trigger '{trigger.get('name')}': Invalid operator '{operator_str}'")
                        conditions_met.append(False)
                        continue

                    conditions_met.append(op_func(current_value, threshold_value))

                if all(conditions_met):
                    self.logger.info(f"Trigger '{trigger.get('name')}' conditions met. Executing action.")
                    action = trigger.get("action")

                    if action.get("type") == "publish":
                        subject = action.get("subject")
                        # Use a provided payload or create a default one
                        payload = action.get("payload", {
                            "trigger_name": trigger.get('name'),
                            "timestamp": datetime.now().isoformat()
                        })

                        if subject:
                            await self.messaging_client.publish(subject, json.dumps(payload).encode())
                            self.logger.info(f"Trigger action: Published to {subject}")
                        else:
                            self.logger.warning(f"Trigger '{trigger.get('name')}': 'publish' action is missing a 'subject'.")

                    # Here we could add other action types like "run_command", etc.

            except Exception as e:
                self.logger.error(f"Error evaluating trigger '{trigger.get('name', 'Unnamed')}': {e}", exc_info=True)

    async def _stop_logic(self):
        """This is called when the service is shutting down."""
        self.logger.info("Compute service shutting down...")

        if self.state_publisher_task:
            self.state_publisher_task.cancel()

        await self._publish_status("STOPPING")
