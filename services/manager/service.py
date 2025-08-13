import asyncio
import os
import subprocess
import sys
import signal
import io
from typing import Dict

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

class ManagerService(Microservice):
    """
    The Microservice Manager.
    Discovers, starts, and monitors other microservices.
    """

    def __init__(self):
        super().__init__("manager_service")
        self.services_dir = "services"
        self.managed_processes: Dict[str, subprocess.Popen] = {}

    def discover_services(self):
        """Discovers available services in the services directory."""
        discovered = []
        for service_name in os.listdir(self.services_dir):
            service_path = os.path.join(self.services_dir, service_name)
            if os.path.isdir(service_path) and "main.py" in os.listdir(service_path):
                if service_name != "manager":
                    discovered.append(service_name)
        self.logger.info(f"Discovered services: {discovered}")
        return discovered

    def start_service(self, service_name: str):
        """Starts a microservice as a new process."""
        if service_name in self.managed_processes and self.managed_processes[service_name].poll() is None:
            self.logger.info(f"Service '{service_name}' is already running.")
            return

        service_main_path = os.path.join(self.services_dir, service_name, "main.py")
        if not os.path.exists(service_main_path):
            self.logger.error(f"Could not find main.py for service '{service_name}'.")
            return

        self.logger.info(f"Starting service '{service_name}'...")
        try:
            # The child process will handle its own logging.
            # We do not redirect stdout/stderr here.
            process = subprocess.Popen([sys.executable, service_main_path])
            self.managed_processes[service_name] = process
            self.logger.info(f"Service '{service_name}' started with PID {process.pid}.")
        except Exception as e:
            self.logger.error(f"Error starting service '{service_name}': {e}", exc_info=True)

    def stop_service(self, service_name: str):
        """Stops a microservice."""
        process = self.managed_processes.get(service_name)
        if process and process.poll() is None:
            self.logger.info(f"Stopping service '{service_name}' (PID {process.pid})...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Service '{service_name}' did not terminate gracefully. Killing.")
                process.kill()
            self.logger.info(f"Service '{service_name}' stopped.")

        if service_name in self.managed_processes:
            del self.managed_processes[service_name]

    async def _start_logic(self):
        """Starts the manager logic: discover and start all services."""
        self.logger.info("Starting service discovery...")
        all_services = self.discover_services()

        if "settings_service" in all_services:
            self.start_service("settings_service")
            await asyncio.sleep(2)
            other_services = [s for s in all_services if s != "settings_service"]
        else:
            other_services = all_services

        for service_name in other_services:
            self.start_service(service_name)

    async def _stop_logic(self):
        """Stops all managed microservices."""
        self.logger.info("Stopping all managed services...")
        for service_name in list(self.managed_processes.keys()):
            self.stop_service(service_name)
        self.logger.info("All managed services have been signaled to stop.")

    async def run(self):
        """The main entry point for the manager service."""
        self.logger.info("Service starting...")
        loop = asyncio.get_running_loop()
        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self._signal_handler)
        except NotImplementedError:
            self.logger.warning("loop.add_signal_handler not implemented. Using signal.signal().")
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            await self._start_logic()
            self.logger.info("Manager is running. Waiting for shutdown signal.")

            while not self._shutdown_event.is_set():
                for name, process in list(self.managed_processes.items()):
                    if process.poll() is not None:
                        exit_code = process.returncode
                        if exit_code < 0:
                            # Terminated by signal
                            signal_num = -exit_code
                            unsigned_code = 128 + signal_num
                            try:
                                signal_name = signal.Signals(signal_num).name
                            except ValueError:
                                signal_name = "UNKNOWN"
                            self.logger.info(
                                f"Service '{name}' (PID {process.pid}) has terminated. "
                                f"Exit Code: {exit_code} (unsigned: {unsigned_code}, signal: {signal_name})"
                            )
                        else:
                            # Normal exit
                            self.logger.info(
                                f"Service '{name}' (PID {process.pid}) has terminated with exit code {exit_code}."
                            )
                        self.stop_service(name)

                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    pass

        except Exception as e:
            self.logger.critical(f"An unhandled error occurred during run: {e}", exc_info=True)
        finally:
            self.logger.info("Shutting down...")
            await self._stop_logic()
            self.logger.info("Manager service has stopped.")
