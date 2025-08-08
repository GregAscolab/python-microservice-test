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
    This service is a special case and does not connect to NATS itself.
    """

    def __init__(self):
        super().__init__("manager_service")
        self.services_dir = "services"
        self.managed_processes: Dict[str, subprocess.Popen] = {}
        self.log_files: Dict[str, io.TextIOWrapper] = {}
        # Create a directory for logs if it doesn't exist
        os.makedirs("logs", exist_ok=True)


    def discover_services(self):
        """
        Discovers available services in the services directory.
        A service is a directory containing a main.py file.
        """
        discovered = []
        for service_name in os.listdir(self.services_dir):
            service_path = os.path.join(self.services_dir, service_name)
            if os.path.isdir(service_path) and "main.py" in os.listdir(service_path):
                if service_name != "manager": # Exclude the manager itself
                    discovered.append(service_name)
        print(f"[{self.service_name}] Discovered services: {discovered}")
        return discovered

    def start_service(self, service_name: str):
        """Starts a microservice as a new process and logs its output."""
        if service_name in self.managed_processes and self.managed_processes[service_name].poll() is None:
            print(f"[{self.service_name}] Service '{service_name}' is already running.")
            return

        service_main_path = os.path.join(self.services_dir, service_name, "main.py")
        if not os.path.exists(service_main_path):
            print(f"[{self.service_name}] Could not find main.py for service '{service_name}'.")
            return

        print(f"[{self.service_name}] Starting service '{service_name}'...")
        try:
            log_path = os.path.join("logs", f"{service_name}.log")
            log_file = open(log_path, "w")
            self.log_files[service_name] = log_file

            process = subprocess.Popen(
                [sys.executable, service_main_path],
                stdout=log_file,
                stderr=log_file
            )
            self.managed_processes[service_name] = process
            print(f"[{self.service_name}] Service '{service_name}' started with PID {process.pid}. Log: {log_path}")
        except Exception as e:
            print(f"[{self.service_name}] Error starting service '{service_name}': {e}")

    def stop_service(self, service_name: str):
        """Stops a microservice and closes its log file."""
        process = self.managed_processes.get(service_name)
        if process and process.poll() is None:
            print(f"[{self.service_name}] Stopping service '{service_name}' (PID {process.pid})...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"[{self.service_name}] Service '{service_name}' did not terminate gracefully. Killing.")
                process.kill()

            print(f"[{self.service_name}] Service '{service_name}' stopped.")

        if service_name in self.managed_processes:
            del self.managed_processes[service_name]

        if service_name in self.log_files:
            self.log_files[service_name].close()
            del self.log_files[service_name]

    async def _start_logic(self):
        """
        Starts the manager logic: discover and start all services.
        """
        print(f"[{self.service_name}] Starting service discovery...")
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
        """
        Stops all managed microservices.
        """
        print(f"[{self.service_name}] Stopping all managed services...")
        for service_name in list(self.managed_processes.keys()):
            self.stop_service(service_name)
        print(f"[{self.service_name}] All managed services have been signaled to stop.")

    async def run(self):
        """
        The main entry point for the manager service.
        """
        self.is_running = True
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        try:
            await self._start_logic()
            print(f"[{self.service_name}] Manager is running. Press Ctrl+C to stop.")

            while self.is_running:
                for name, process in list(self.managed_processes.items()):
                    if process.poll() is not None:
                        print(f"[{self.service_name}] Service '{name}' (PID {process.pid}) has terminated.")
                        self.stop_service(name) # Ensure log file is closed
                await asyncio.sleep(2)

        except asyncio.CancelledError:
            pass
        finally:
            await self._stop_logic()
            print(f"[{self.service_name}] Manager service has stopped.")

    async def stop(self):
        """Stops the manager service."""
        if not self.is_running:
            return
        print(f"[{self.service_name}] Initiating shutdown...")
        self.is_running = False
