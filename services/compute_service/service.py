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

    async def _handle_register_computation(self, source_signal: str, computation_type: str, output_name: str, reply: str = ""):
        """Command handler to dynamically register a new computation."""
        response = {}
        if not all([source_signal, computation_type, output_name]):
            response = {"status": "error", "message": "Missing 'source_signal', 'computation_type', or 'output_name'."}
        elif computation_type not in self.available_computations:
            response = {"status": "error", "message": f"Unknown computation type: {computation_type}"}
        else:
            computation_class = self.available_computations[computation_type]
            computation_instance = computation_class()
            computation_to_store = {"instance": computation_instance, "output_name": output_name}
            self.active_computations[source_signal].append(computation_to_store)
            self.logger.info(f"Registered new computation: '{output_name}' ({computation_type}) on source '{source_signal}'.")
            response = {"status": "ok", "message": "Computation registered successfully."}

        if reply:
            await self.messaging_client.publish(reply, json.dumps(response).encode())

    async def _publish_status(self, status: str | None = None):
        """Publishes the service's current status."""
        if status:
            self.status = status

        status_payload = {"service": self.service_name, "status": self.status, "timestamp": datetime.now().isoformat()}
        await self.messaging_client.publish(f"compute.status", json.dumps(status_payload).encode())
        self.logger.info(f"Published status: {self.status}")

    async def _handle_register_trigger(self, trigger: dict, reply: str = ""):
        """Command handler to dynamically register a new trigger."""
        response = {}
        if not trigger or 'name' not in trigger or 'conditions' not in trigger or 'action' not in trigger:
            response = {"status": "error", "message": "Invalid trigger structure. Required fields: name, conditions, action."}
        else:
            # Initialize the trigger's state
            trigger['is_currently_active'] = False
            trigger['last_event_timestamp'] = None

            # Remove any existing trigger with the same name and add the new one
            self.triggers = [t for t in self.triggers if t.get('name') != trigger.get('name')]
            self.triggers.append(trigger)

            self.logger.info(f"Registered trigger: {trigger.get('name')}")
            response = {"status": "ok", "message": "Trigger registered successfully."}

        if reply:
            await self.messaging_client.publish(reply, json.dumps(response).encode())

    async def _handle_unregister_computation(self, output_name: str, reply: str = ""):
        """Command handler to unregister a computation by its output name."""
        response = {}
        if not output_name:
            response = {"status": "error", "message": "Missing 'output_name'."}
        else:
            found = False
            for source_signal, computations in self.active_computations.items():
                initial_len = len(computations)
                self.active_computations[source_signal] = [
                    comp for comp in computations if comp.get("output_name") != output_name
                ]
                if len(self.active_computations[source_signal]) < initial_len:
                    found = True
                    break

            if found:
                if output_name in self.computation_state:
                    del self.computation_state[output_name]
                self.logger.info(f"Unregistered computation with output: {output_name}")
                response = {"status": "ok", "message": "Computation unregistered."}
            else:
                response = {"status": "error", "message": f"Computation with output '{output_name}' not found."}

        if reply:
            await self.messaging_client.publish(reply, json.dumps(response).encode())

    async def _handle_unregister_trigger(self, name: str, reply: str = ""):
        """Command handler to unregister a trigger by its name."""
        response = {}
        if not name:
            response = {"status": "error", "message": "Missing trigger 'name'."}
        else:
            initial_len = len(self.triggers)
            self.triggers = [t for t in self.triggers if t.get('name') != name]
            if len(self.triggers) < initial_len:
                self.logger.info(f"Unregistered trigger: {name}")
                response = {"status": "ok", "message": "Trigger unregistered."}
            else:
                response = {"status": "error", "message": f"Trigger '{name}' not found."}

        if reply:
            await self.messaging_client.publish(reply, json.dumps(response).encode())

    async def _handle_get_available_signals_request(self, reply: str = "", **kwargs):
        """Returns a list of all available signals for computation."""
        response = {"status": "ok", "signals": list(self.computation_state.keys())}
        if reply:
            await self.messaging_client.publish(reply, json.dumps(response).encode())

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
        self.command_handler.register_command("get_available_signals", self._handle_get_available_signals_request)
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
                # The payload now includes the full trigger objects with their state
                payload = {
                    "computation_state": self.computation_state,
                    "triggers": self.triggers
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


    async def _execute_trigger_action(self, trigger_name: str, action: dict):
        """Executes a single trigger action, e.g., publishing a NATS message."""
        if not action or 'type' not in action:
            return

        action_type = action.get("type")
        if action_type == "publish":
            subject = action.get("subject")
            if not subject:
                self.logger.warning(f"Trigger '{trigger_name}': 'publish' action is missing a 'subject'.")
                return

            payload = action.get("payload", {"trigger_name": trigger_name, "timestamp": datetime.now().isoformat()})
            await self.messaging_client.publish(subject, json.dumps(payload).encode())
            self.logger.info(f"Trigger '{trigger_name}' action: Published to {subject}")
        # Other action types could be implemented here

    async def _evaluate_triggers(self):
        """Evaluate all registered triggers against the current computation state."""
        for trigger in self.triggers:
            try:
                all_conditions_met = True
                for condition in trigger.get("conditions", []):
                    signal_name = condition.get("name")
                    op_func = self.operator_map.get(condition.get("operator"))

                    if signal_name not in self.computation_state or not op_func:
                        all_conditions_met = False
                        break

                    current_value = self.computation_state[signal_name]
                    threshold_value = condition.get("value")
                    if not op_func(current_value, threshold_value):
                        all_conditions_met = False
                        break

                was_active = trigger.get('is_currently_active', False)

                # State change detection
                if all_conditions_met and not was_active:
                    trigger['is_currently_active'] = True
                    trigger['last_event_timestamp'] = datetime.now().isoformat()
                    self.logger.info(f"Trigger '{trigger['name']}' became ACTIVE.")
                    await self._execute_trigger_action(trigger['name'], trigger['action'].get('on_become_active'))

                elif not all_conditions_met and was_active:
                    trigger['is_currently_active'] = False
                    trigger['last_event_timestamp'] = datetime.now().isoformat()
                    self.logger.info(f"Trigger '{trigger['name']}' became INACTIVE.")
                    await self._execute_trigger_action(trigger['name'], trigger['action'].get('on_become_inactive'))

                elif all_conditions_met and was_active:
                    await self._execute_trigger_action(trigger['name'], trigger['action'].get('on_is_active'))

                elif not all_conditions_met and not was_active:
                    await self._execute_trigger_action(trigger['name'], trigger['action'].get('on_is_inactive'))

            except Exception as e:
                self.logger.error(f"Error evaluating trigger '{trigger.get('name', 'Unnamed')}': {e}", exc_info=True)

    async def _stop_logic(self):
        """This is called when the service is shutting down."""
        self.logger.info("Compute service shutting down...")

        if self.state_publisher_task:
            self.state_publisher_task.cancel()

        await self._publish_status("STOPPING")
