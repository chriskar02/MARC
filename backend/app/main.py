from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Dict

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .api import commands
from .core.config import Settings, get_settings
from .core.event_bus import EventBus
from .core.realtime import RealTimeCoordinator, RealtimeTaskConfig
from .deps import get_event_bus, get_realtime_coordinator

logger = logging.getLogger(__name__)


def _telemetry_task_factory(event_bus: EventBus) -> Callable[[], Awaitable[None]]:
    async def _task() -> None:
        payload: Dict[str, Any] = {
            "type": "coordinator",
            "timestamp": asyncio.get_running_loop().time(),
        }
        await event_bus.publish("telemetry/realtime", payload)

    return _task


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = get_settings()
    event_bus = EventBus()
    coordinator = RealTimeCoordinator()
    await coordinator.start()
    coordinator.register_task(
        RealtimeTaskConfig(
            name="telemetry_heartbeat",
            period_ms=1000,
            deadline_ms=5,
            max_jitter_ms=1,
            priority=10,
        ),
        coroutine_factory=_telemetry_task_factory(event_bus),
    )
    app.state.settings = settings
    app.state.event_bus = event_bus
    app.state.coordinator = coordinator
    try:
        yield
    finally:
        await coordinator.stop()


def create_app() -> FastAPI:
    application = FastAPI(title="Precision Control Backend", lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _provide_event_bus() -> EventBus:
        return application.state.event_bus

    def _provide_coordinator() -> RealTimeCoordinator:
        return application.state.coordinator

    application.dependency_overrides[get_event_bus] = _provide_event_bus
    application.dependency_overrides[get_realtime_coordinator] = _provide_coordinator

    application.include_router(commands.router)

    @application.get("/health")
    async def health() -> Dict[str, Any]:
        coordinator: RealTimeCoordinator = application.state.coordinator
        handle = coordinator.get_handle("telemetry_heartbeat")
        return {
            "status": "ok",
            "coordinator": {
                "last_latency_ms": handle.last_stats.latency_ms if handle and handle.last_stats else None,
                "deadline_missed": handle.last_stats.deadline_missed if handle and handle.last_stats else None,
            },
        }

    @application.websocket("/ws/telemetry")
    async def websocket_telemetry(websocket: WebSocket) -> None:
        await websocket.accept()
        event_bus: EventBus = application.state.event_bus
        try:
            async for payload in event_bus.subscribe("telemetry/realtime"):
                message = {"topic": "telemetry/realtime", "payload": payload}
                try:
                    await websocket.send_json(message)
                except Exception:
                    break  # Client disconnected, exit gracefully
        except Exception as exc:
            logger.error("ws_telemetry_error", error_msg=str(exc))
        finally:
            try:
                await websocket.close()
            except Exception:
                pass  # Already closed

    @application.websocket("/ws/camera/{worker_name}")
    async def websocket_camera(websocket: WebSocket, worker_name: str) -> None:
        # TODO: Implement camera worker integration
        await websocket.close(code=1000, reason="Camera worker not yet implemented")

    return application


app = create_app()
