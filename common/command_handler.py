import json
import logging
from typing import Callable, Awaitable, Dict, Any

class CommandHandler:
    """
    A factory for registering and handling RPC-like commands.
    """

    def __init__(self, service_name: str, logger: logging.Logger):
        self.service_name = service_name
        self.logger = logger
        self._handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}

    def register_command(self, command_name: str, handler: Callable[..., Awaitable[Any]]):
        """
        Registers a callback function to handle a specific command.
        """
        self.logger.info(f"Registering command: {command_name}")
        self._handlers[command_name] = handler

    async def handle_message(self, msg_payload: bytes, reply:str=""):
        """
        Parses a raw message payload, identifies the command, and executes the
        corresponding handler.
        """
        try:
            data = json.loads(msg_payload)
            command = data.get("command")

            if not command:
                self.logger.warning("Received message without a 'command' field.")
                return

            handler = self._handlers.get(command)
            if not handler:
                self.logger.warning(f"No handler registered for command: {command}")
                return

            args = {k: v for k, v in data.items() if k != 'command'}
            if reply:
                args["reply"] = reply

            self.logger.info(f"Executing command '{command}' with args: {args}")
            await handler(**args)

        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON from message: {msg_payload}")
        except Exception as e:
            self.logger.error(f"Error handling command: {e}", exc_info=True)
