import asyncio
import os
import subprocess
import sys
import json
from typing import Dict, TypedDict, Optional
from nats.aio.msg import Msg

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

class ServiceStatus(TypedDict):
    status: str  # e.g., 'stopped', 'running', 'error', 'restarting'
    pid: Optional[int]
    process: Optional[subprocess.Popen]
    last_command: Optional[str] # 'start' or 'stop'
    restart_count: int
    name: str

class ManagerService(Microservice):
    """
    The Microservice Manager.
    Discovers, starts, and monitors other microservices.
    Receives commands via NATS to manage service lifecycles.
    """

    def __init__(self):
        super().__init__("manager")
        self.services_dir = "services"
        self.managed_services: Dict[str, ServiceStatus] = {}
        self.last_published_status = None
        self.max_retries = 3
        self._discover_and_initialize_services()
        self._register_command_handlers()

    def _discover_and_initialize_services(self):
        """Discovers available services and initializes their status."""
        self.logger.info("Discovering services...")
        for service_name in os.listdir(self.services_dir):
            service_path = os.path.join(self.services_dir, service_name)
            # The manager does not manage itself.
            if os.path.isdir(service_path) and "main.py" in os.listdir(service_path) and service_name != "manager":
                self.managed_services[service_name] = {
                    "status": "stopped",
                    "pid": None,
                    "process": None,
                    "last_command": None,
                    "restart_count": 0,
                    "name": service_name,
                }
        self.logger.info(f"Discovered services: {list(self.managed_services.keys())}")

    def _register_command_handlers(self):
        """Registers handlers for manager commands."""
        self.command_handler.register_command("start_service", self.start_service_command)
        self.command_handler.register_command("stop_service", self.stop_service_command)
        self.command_handler.register_command("restart_service", self.restart_service_command)
        self.command_handler.register_command("get_status", self.get_status_command)
        self.command_handler.register_command("start_all", self.start_all_command)
        self.command_handler.register_command("stop_all", self.stop_all_command)
        self.command_handler.register_command("restart_all", self.restart_all_command)

    async def start_service(self, service_name: str) -> bool:
        """Starts a microservice as a new process."""
        if service_name not in self.managed_services:
            self.logger.error(f"Service '{service_name}' not found.")
            return False

        service_info = self.managed_services[service_name]
        if service_info["status"] == 'running' and service_info["process"] and service_info["process"].poll() is None:
            self.logger.info(f"Service '{service_name}' is already running.")
            return True

        service_main_path = os.path.join(self.services_dir, service_name, "main.py")
        if not os.path.exists(service_main_path):
            self.logger.error(f"Could not find main.py for service '{service_name}'.")
            service_info["status"] = "error"
            return False

        self.logger.info(f"Starting service '{service_name}'...")
        try:
            process = subprocess.Popen([sys.executable, service_main_path])
            service_info.update({
                "status": "running",
                "process": process,
                "pid": process.pid,
                "restart_count": 0, # Reset restart count on successful manual start
                "last_command": "start"
            })
            self.logger.info(f"Service '{service_name}' started with PID {process.pid}.")
            await self.publish_status() # Publish status after starting a service
            return True
        except Exception as e:
            self.logger.error(f"Error starting service '{service_name}': {e}", exc_info=True)
            service_info["status"] = "error"
            await self.publish_status() # Publish status after a failed start
            return False

    async def stop_service(self, service_name: str):
        """Stops a microservice."""
        if service_name not in self.managed_services:
            self.logger.error(f"Service '{service_name}' not found.")
            return

        service_info = self.managed_services[service_name]
        process = service_info.get("process")

        if process and process.poll() is None:
            self.logger.info(f"Stopping service '{service_name}' (PID {process.pid})...")
            service_info["status"] = "stopping"
            service_info["last_command"] = "stop"
            process.terminate()
            try:
                await asyncio.to_thread(process.wait, timeout=5)
                self.logger.info(f"Service '{service_name}' terminated gracefully.")
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Service '{service_name}' did not terminate gracefully. Killing.")
                process.kill()
            except Exception as e:
                self.logger.error(f"Error while stopping service {service_name}: {e}")

        service_info.update({"status": "stopped", "pid": None, "process": None})
        await self.publish_status()

    async def restart_service(self, service_name: str):
        self.logger.info(f"Restarting service '{service_name}'...")
        await self.stop_service(service_name)
        await asyncio.sleep(1) # Give it a moment to release resources
        await self.start_service(service_name)

    # --- Command Handler Methods ---

    async def start_service_command(self, service_name: str):
        if service_name:
            await self.start_service(service_name)

    async def stop_service_command(self, service_name: str):
        if service_name:
            await self.stop_service(service_name)

    async def restart_service_command(self, service_name: str):
        if service_name:
            await self.restart_service(service_name)

    async def start_all_command(self):
        """Starts all discovered services, ensuring settings_service starts first."""
        self.logger.info("Executing start_all command...")

        # Define service start order
        service_names = list(self.managed_services.keys())
        # Ensure settings_service is first if it exists
        if "settings_service" in service_names:
            service_names.insert(0, service_names.pop(service_names.index("settings_service")))

        for service_name in service_names:
            await self.start_service(service_name)
            if service_name == "settings_service":
                self.logger.info("Waiting for settings_service to initialize...")
                await asyncio.sleep(2) # Give it time to start and be available
        await self.publish_status()

    async def stop_all_command(self):
        self.logger.info("Executing stop_all command...")
        await self._stop_logic()
        await self.publish_status()

    async def restart_all_command(self):
        self.logger.info("Executing restart_all command...")
        await self.stop_all_command()
        await self.start_all_command()
        self.logger.info("Finished restart_all command.")

    async def get_status_command(self, reply:str=""):
        """Replies with the current status of all services."""
        await self.publish_status(reply=reply, forced=True)

    def get_status_payload(self):
        """Constructs the status payload dictionary."""
        services_status_list = []
        is_all_running = True
        for name, info in self.managed_services.items():
            # Check if the process is still running
            process = info.get("process")
            status = info["status"]
            if status == 'running' and process and process.poll() is not None:
                status = 'crashed' # Or 'stopped', depending on desired behavior
                info['status'] = status
                info['pid'] = None
                info['process'] = None

            if status != 'running':
                is_all_running = False

            status_info = {k: v for k, v in info.items() if k != 'process'}
            services_status_list.append(status_info)

        return {
            "global_status": "all_ok" if is_all_running else "degraded",
            "services": services_status_list
        }

    # --- Core Logic ---

    async def _start_logic(self):
        """Connects to NATS, starts settings_service, subscribes, and monitors."""
        # The manager is a special case. It connects to the default NATS URL
        # without fetching settings first, because it is responsible for
        # starting the settings_service itself.
        self.logger.info("Manager connecting directly to NATS...")
        await self.messaging_client.connect(self.nats_url)
        self.logger.info("Manager connected to NATS.")

        # Now subscribe to commands.
        await self._subscribe_to_commands()

        # Start all services automatically on manager startup.
        self.logger.info("Manager starting... auto-starting all services.")
        await self.start_all_command()

        # Start the monitoring loop as a background task
        asyncio.create_task(self.monitor_services())
        self.logger.info("Service monitoring started.")

    async def _stop_logic(self):
        """Stops all managed microservices."""
        self.logger.info("Stopping all managed services...")
        # Create a list of services to stop to avoid issues with modifying dict during iteration
        service_names = list(self.managed_services.keys())
        for service_name in service_names:
            await self.stop_service(service_name)
        self.logger.info("All managed services have been signaled to stop.")

    async def publish_status(self, reply:str="", forced:bool=False):
        """Publishes the status of all managed services to NATS and stores it."""
        status_payload = self.get_status_payload()
        if forced or (self.last_published_status != status_payload):
            self.logger.info(f"Publishing status update for {len(status_payload['services'])} services.")
            if reply:
                subject = reply
            else:
                subject = "manager.status"
            await self.messaging_client.publish(
                subject,
                json.dumps(status_payload).encode()
            )
            self.last_published_status = status_payload

    async def monitor_services(self):
        """Periodically checks the health of services and handles crashes."""
        while not self._shutdown_event.is_set():
            state_changed = False
            for name, service_info in list(self.managed_services.items()):
                process = service_info.get("process")
                if service_info["status"] == "running" and process and process.poll() is not None:
                    # The process has terminated, but was it intentional?
                    if service_info.get("last_command") != "stop":
                        self.logger.warning(f"Service '{name}' terminated unexpectedly with code {process.returncode}.")
                        service_info["status"] = "crashed"
                        service_info["pid"] = None
                        service_info["process"] = None

                        if service_info["restart_count"] < self.max_retries:
                            service_info["restart_count"] += 1
                            self.logger.info(f"Attempting to restart '{name}' (Attempt {service_info['restart_count']}/{self.max_retries}).")
                            service_info["status"] = "restarting"
                            await self.start_service(name)
                        else:
                            self.logger.error(f"Service '{name}' has crashed too many times. Will not restart again.")
                            service_info["status"] = "error"
                    else:
                        # This was an intentional stop, so we just clean up the state
                        self.logger.info(f"Service '{name}' stopped as commanded.")
                        service_info.update({"status": "stopped", "pid": None, "process": None})
                    state_changed = True

            if state_changed:
                await self.publish_status()

            try:
                # Wait for 2 seconds or until shutdown is triggered
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                pass # This is expected, continue the loop
