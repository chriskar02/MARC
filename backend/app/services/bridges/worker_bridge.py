from __future__ import annotations

from typing import Any, Dict

import structlog

from ...core.event_bus import EventBus
from ...core.realtime import RealTimeCoordinator, RealtimeTaskConfig
from ...shared.schemas import WorkerPayload
from ...worker.process_manager import WorkerProcessManager, WorkerSpec

logger = structlog.get_logger(__name__)


class WorkerBridge:
    """Coordinates isolated worker processes and republishes their telemetry."""

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._manager = WorkerProcessManager(payload_handler=self._handle_payload)
        self._coordinator: RealTimeCoordinator | None = None

    async def attach_coordinator(self, coordinator: RealTimeCoordinator) -> None:
        self._coordinator = coordinator
        config = RealtimeTaskConfig(
            name="worker_health_check",
            period_ms=200,
            deadline_ms=2,
            priority=5,
        )
        coordinator.register_task(config, self._health_check_task)

    async def start_camera_worker(self, camera_config: Dict[str, Any]) -> None:
        spec = WorkerSpec(
            name="basler_camera",
            target="app.worker.workers.camera_worker:run",
            config=camera_config,
        )
        await self._manager.start_worker(spec)

    async def shutdown(self) -> None:
        await self._manager.shutdown()

    async def _handle_payload(self, payload: WorkerPayload) -> None:
        topic = f"worker/{payload.worker}/{payload.payload_type}"
        if payload.payload_type.value == "frame":
            logger.debug("worker_frame_received", worker=payload.worker, data_len=len(payload.data))
        await self._event_bus.publish(topic, payload)

    async def _health_check_task(self):
        for name, last_heartbeat in self._manager.snapshot().items():
            logger.debug("worker_status", worker=name, last_heartbeat=last_heartbeat)
