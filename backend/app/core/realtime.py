from __future__ import annotations

import asyncio
import heapq
import itertools
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, Optional

import structlog
from pydantic import BaseModel, Field

from . import metrics

logger = structlog.get_logger(__name__)


class RealtimeTaskConfig(BaseModel):
    name: str
    period_ms: float = Field(gt=0)
    deadline_ms: float = Field(gt=0)
    max_jitter_ms: float = Field(default=1.0)
    priority: int = Field(default=0, description="Lower value = higher priority")
    isolated: bool = Field(default=False)

    @property
    def period_seconds(self) -> float:
        return self.period_ms / 1000.0

    @property
    def deadline_seconds(self) -> float:
        return self.deadline_ms / 1000.0

    @property
    def max_jitter_seconds(self) -> float:
        return self.max_jitter_ms / 1000.0


@dataclass
class RealtimeTaskStats:
    jitter_ms: float
    latency_ms: float
    deadline_missed: bool


@dataclass
class RealtimeTaskHandle:
    config: RealtimeTaskConfig
    coroutine_factory: Callable[[], Awaitable[None]]
    next_run: float
    cancelled: bool = False
    last_stats: Optional[RealtimeTaskStats] = None
    _reschedule_at: float = field(default=0.0, init=False)

    def cancel(self) -> None:
        self.cancelled = True


class RealTimeCoordinator:
    """Priority-based scheduler that enforces millisecond budgets for device loops."""

    def __init__(self, *, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._loop = loop or asyncio.get_event_loop()
        self._queue: list[tuple[float, int, int, RealtimeTaskHandle]] = []
        self._seq = itertools.count()
        self._handles: Dict[str, RealtimeTaskHandle] = {}
        self._wakeup = asyncio.Event()
        self._scheduler_task: Optional[asyncio.Task[None]] = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._scheduler_task = self._loop.create_task(self._schedule_loop())
        logger.info("realtime_coordinator_started")

    async def stop(self) -> None:
        self._running = False
        self._wakeup.set()
        for handle in list(self._handles.values()):
            handle.cancel()
        if self._scheduler_task:
            await self._scheduler_task
        logger.info("realtime_coordinator_stopped")

    def register_task(
        self,
        config: RealtimeTaskConfig,
        coroutine_factory: Callable[[], Awaitable[None]],
    ) -> RealtimeTaskHandle:
        if config.name in self._handles:
            raise ValueError(f"Task {config.name} already registered")
        start_time = self._loop.time() + config.period_seconds
        handle = RealtimeTaskHandle(config=config, coroutine_factory=coroutine_factory, next_run=start_time)
        self._handles[config.name] = handle
        self._push(handle)
        self._wakeup.set()
        logger.info("rt_task_registered", task=config.name, period_ms=config.period_ms)
        return handle

    def run_immediately(self, task_name: str) -> None:
        handle = self._handles.get(task_name)
        if not handle:
            raise KeyError(f"Task {task_name} not registered")
        handle.next_run = self._loop.time()
        self._push(handle)
        self._wakeup.set()
        logger.warning("rt_task_immediate_run", task=task_name)

    async def _schedule_loop(self) -> None:
        while self._running:
            if not self._queue:
                self._wakeup.clear()
                await self._wakeup.wait()
                continue

            next_run, _, _, handle = self._queue[0]
            now = self._loop.time()
            delay = max(0.0, next_run - now)
            if delay > 0:
                try:
                    self._wakeup.clear()
                    await asyncio.wait_for(self._wakeup.wait(), timeout=delay)
                    continue
                except asyncio.TimeoutError:
                    pass

            heapq.heappop(self._queue)
            if handle.cancelled:
                continue
            self._loop.create_task(self._execute(handle))

    async def _execute(self, handle: RealtimeTaskHandle) -> None:
        config = handle.config
        scheduled_start = handle.next_run
        jitter = (self._loop.time() - scheduled_start) * 1000.0
        task_latency = 0.0
        deadline_missed = False
        try:
            await handle.coroutine_factory()
        except Exception as exc:  # pragma: no cover - log path
            logger.exception("rt_task_exception", task=config.name, error=str(exc))
        finally:
            finished = self._loop.time()
            task_latency = (finished - scheduled_start) * 1000.0
            if (finished - scheduled_start) > config.deadline_seconds:
                deadline_missed = True
                metrics.task_deadline_counter(config.name).inc()
                logger.warning("rt_task_deadline_miss", task=config.name, latency_ms=task_latency)
            metrics.task_latency_histogram(config.name).observe(task_latency)
            metrics.task_jitter_histogram(config.name).observe(max(jitter, 0.0))
            handle.last_stats = RealtimeTaskStats(jitter_ms=jitter, latency_ms=task_latency, deadline_missed=deadline_missed)
            handle.next_run = scheduled_start + config.period_seconds
            if not handle.cancelled:
                self._push(handle)
                self._wakeup.set()

    def _push(self, handle: RealtimeTaskHandle) -> None:
        heapq.heappush(
            self._queue,
            (handle.next_run, handle.config.priority, next(self._seq), handle),
        )
        metrics.task_backlog_gauge(handle.config.name).set(len(self._queue))

    def get_handle(self, task_name: str) -> Optional[RealtimeTaskHandle]:
        return self._handles.get(task_name)
