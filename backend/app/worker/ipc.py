from __future__ import annotations

import asyncio
import multiprocessing as mp
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from ..shared.schemas import ControlMessage, WorkerPayload


@dataclass
class WorkerChannels:
    """Control/data IPC primitives shared between main process and worker."""

    control_parent: mp.connection.Connection
    control_child: mp.connection.Connection
    data_queue: mp.Queue

    @classmethod
    def create(cls, *, queue_size: int = 64) -> "WorkerChannels":
        parent_conn, child_conn = mp.Pipe()
        data_queue: mp.Queue = mp.Queue(maxsize=queue_size)
        return cls(control_parent=parent_conn, control_child=child_conn, data_queue=data_queue)


class ControlChannel:
    def __init__(self, connection: mp.connection.Connection) -> None:
        self._conn = connection

    async def recv(self) -> ControlMessage:
        return await asyncio.to_thread(self._conn.recv)

    async def iter_messages(self) -> AsyncIterator[ControlMessage]:
        while True:
            yield await self.recv()

    async def send(self, message: ControlMessage) -> None:
        await asyncio.to_thread(self._conn.send, message.dict())


class DataChannel:
    def __init__(self, queue: mp.Queue) -> None:
        self._queue = queue

    async def publish(self, payload: WorkerPayload) -> None:
        await asyncio.to_thread(self._queue.put, payload)

    async def get(self) -> WorkerPayload:
        raw: WorkerPayload = await asyncio.to_thread(self._queue.get)
        return raw

    async def iter_payloads(self) -> AsyncIterator[WorkerPayload]:
        while True:
            yield await self.get()


@dataclass
class WorkerContext:
    name: str
    control: ControlChannel
    data: DataChannel
    heartbeat_interval_ms: int = 100
    _sequence_id: int = 0

    async def send_payload(self, payload_type: str, data: bytes, metadata: Optional[dict] = None) -> None:
        self._sequence_id += 1
        payload = WorkerPayload(
            worker=self.name,
            sequence_id=self._sequence_id,
            monotonic_ts=asyncio.get_running_loop().time(),
            payload_type=payload_type,
            data=data,
            metadata=metadata,
        )
        await self.data.publish(payload)
