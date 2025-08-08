import asyncio
from abc import ABC, abstractmethod
from typing import Callable, Awaitable

import nats
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg

class MessagingClient(ABC):
    """
    An abstract base class for a messaging client.
    """
    @abstractmethod
    async def connect(self, servers: list[str] | str):
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    @abstractmethod
    async def publish(self, subject: str, payload: bytes):
        pass

    @abstractmethod
    async def subscribe(self, subject: str, cb: Callable[[Msg], Awaitable[None]], queue: str = ""):
        pass

    @abstractmethod
    async def request(self, subject: str, payload: bytes, timeout: float = 1.0) -> Msg:
        pass

class NatsMessagingClient(MessagingClient):
    """
    A messaging client implementation for NATS.
    """
    def __init__(self):
        self.nc: NATS | None = None

    async def connect(self, servers: list[str] | str):
        if not self.nc or not self.nc.is_connected:
            try:
                self.nc = await nats.connect(servers)
            except Exception as e:
                # This will be caught by the service's logger
                raise

    async def disconnect(self):
        if self.nc and self.nc.is_connected:
            await self.nc.close()

    async def publish(self, subject: str, payload: bytes):
        await self.nc.publish(subject, payload)

    async def subscribe(self, subject: str, cb: Callable[[Msg], Awaitable[None]], queue: str = ""):
        await self.nc.subscribe(subject, cb=cb, queue=queue)

    async def request(self, subject: str, payload: bytes, timeout: float = 1.0) -> Msg:
        return await self.nc.request(subject, payload, timeout=timeout)
