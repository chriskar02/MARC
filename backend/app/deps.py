from __future__ import annotations

from fastapi import Depends

from .core.config import Settings, get_settings
from .core.event_bus import EventBus
from .core.realtime import RealTimeCoordinator


def get_event_bus() -> EventBus:
    # FastAPI injects this via app.state; placeholder for wiring inside routers
    raise NotImplementedError("Dependency override must supply EventBus instance")


def get_realtime_coordinator() -> RealTimeCoordinator:
    raise NotImplementedError("Dependency override must supply RealTimeCoordinator instance")


def get_app_settings(settings: Settings = Depends(get_settings)) -> Settings:
    return settings
