from __future__ import annotations

import asyncio
import importlib
import multiprocessing as mp
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Optional

import structlog

from ..core import metrics
from ..shared.schemas import WorkerPayload, WorkerPayloadType
from .ipc import ControlChannel, DataChannel, WorkerChannels

logger = structlog.get_logger(__name__)


@dataclass
class WorkerSpec:
    name: str
    target: str  # dotted path module:function
    config: dict
    queue_size: int = 64


@dataclass
class WorkerProcess:
    spec: WorkerSpec
    process: mp.Process
    channels: WorkerChannels
    monitor_task: asyncio.Task[None]
    last_heartbeat: float = 0.0


class WorkerProcessManager:
    def __init__(
        self,
        payload_handler: Callable[[WorkerPayload], Awaitable[None]],
        *,
        restart_backoff: float = 2.5,
    ) -> None:
        self._payload_handler = payload_handler
        self._restart_backoff = restart_backoff
        self._workers: Dict[str, WorkerProcess] = {}
        self._ctx = mp.get_context("spawn")

    async def start_worker(self, spec: WorkerSpec) -> None:
        if spec.name in self._workers:
            raise ValueError(f"Worker {spec.name} already running")
        channels = WorkerChannels.create(queue_size=spec.queue_size)
        process = self._ctx.Process(
            target=_worker_bootstrap,
            args=(spec.target, channels.control_child, channels.data_queue, spec.config),
            name=f"worker-{spec.name}",
            daemon=True,
        )
        process.start()
        monitor_task = asyncio.create_task(self._monitor_worker(spec.name, channels))
        worker = WorkerProcess(spec=spec, process=process, channels=channels, monitor_task=monitor_task, last_heartbeat=time.time())
        self._workers[spec.name] = worker
        logger.info("worker_started", worker=spec.name, pid=process.pid)

    async def stop_worker(self, name: str) -> None:
        worker = self._workers.get(name)
        if not worker:
            return
        worker.monitor_task.cancel()
        try:
            await worker.monitor_task
        except asyncio.CancelledError:
            pass
        worker.channels.control_parent.send({"command": "shutdown"})
        worker.process.join(timeout=2)
        if worker.process.is_alive():
            worker.process.terminate()
        del self._workers[name]
        logger.info("worker_stopped", worker=name)

    async def shutdown(self) -> None:
        for name in list(self._workers.keys()):
            await self.stop_worker(name)

    async def _monitor_worker(self, name: str, channels: WorkerChannels) -> None:
        data_channel = DataChannel(channels.data_queue)
        while True:
            payload = await data_channel.get()
            if payload.payload_type == WorkerPayloadType.heartbeat:
                ts = time.time()
                metrics.worker_heartbeat_gauge(name).set(ts)
                worker = self._workers.get(name)
                if worker:
                    worker.last_heartbeat = ts
            await self._payload_handler(payload)

    def get_control_channel(self, name: str) -> Optional[ControlChannel]:
        worker = self._workers.get(name)
        if not worker:
            return None
        return ControlChannel(worker.channels.control_parent)

    def snapshot(self) -> Dict[str, float]:
        return {name: worker.last_heartbeat for name, worker in self._workers.items()}


def _worker_bootstrap(target_path: str, control_conn, data_queue, config: dict) -> None:
    import sys
    import os
    
    # Add parent directory to path so subprocess can find 'app' module
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    module_path, func_name = target_path.split(":")
    module = importlib.import_module(module_path)
    target = getattr(module, func_name)
    target(control_conn, data_queue, config)
