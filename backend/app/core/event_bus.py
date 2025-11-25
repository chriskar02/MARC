from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator, Dict


class EventBus:
    """Simple pub/sub bus built on asyncio queues for realtime telemetry."""

    def __init__(self) -> None:
        self._topics: Dict[str, list[asyncio.Queue[Any]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, payload: Any) -> None:
        async with self._lock:
            subscribers = list(self._topics.get(topic, []))
        for queue in subscribers:
            if not queue.full():
                queue.put_nowait(payload)

    async def subscribe(self, topic: str, max_queue: int = 32) -> AsyncIterator[Any]:
        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=max_queue)
        async with self._lock:
            self._topics[topic].append(queue)
        try:
            while True:
                item = await queue.get()
                yield item
        finally:
            async with self._lock:
                self._topics[topic].remove(queue)
