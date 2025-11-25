# Real-Time Coordinator Overview

The real-time coordinator is a lightweight scheduling layer that sits between FastAPI endpoints/websocket broadcasters and the hardware services. Its goals are:

- guarantee predictable execution windows for device service loops
- detect and report jitter/drift relative to each service's desired period
- provide centralized observability (Prometheus + structlog) for timing and backlog metrics

## Responsibilities

1. **Task registration** – hardware services register async callables along with metadata (period, deadline, jitter budget, priority, human-readable label).
2. **Scheduling** – the coordinator maintains a min-heap/priority queue keyed by next scheduled run time. It uses `asyncio.Condition` to wake precisely when the earliest task is due and dispatches it on a shared high-priority loop executor.
3. **Isolation hooks** – scheduling records which tasks originate from isolated worker processes (camera, high-rate F/T sensor). If a worker falls behind, the coordinator raises alerts but does not block local tasks.
4. **Metrics** – every run emits timing metrics: period, exec duration, deadline miss count, jitter histogram buckets, task backlog depth.
5. **Backpressure signaling** – when a device overruns repeatedly, the coordinator can notify the owning service (e.g., request downsampling) via callbacks.

## Integration Points

- `app/core/realtime.py` implements `RealTimeCoordinator` and `RealtimeTaskHandle`.
- `app/main.py` creates a singleton coordinator during FastAPI lifespan and exposes it through dependency injection.
- Hardware modules (e.g., Standa, PDXC2, Bota sensor) submit their loops during startup and store handles for later cancellation.
- Metrics exported through `prometheus_client` and optionally OpenTelemetry.

## Data Model

```
class RealtimeTaskConfig(BaseModel):
    name: str
    period_ms: int
    deadline_ms: int
    max_jitter_ms: int
    priority: int = 0  # lower is higher priority
    isolated: bool = False
```

Each scheduled loop returns a `RealtimeTaskHandle` with `.cancel()`, `.next_deadline`, `.stats`.

## Deadline/Jitter Monitoring

- `scheduled_start` = last planned start time.
- `actual_start` = `asyncio.get_running_loop().time()` when execution begins.
- `jitter` = `actual_start - scheduled_start` (ms). Count as warning if > `max_jitter`.
- `deadline_miss` when `actual_finish > scheduled_start + deadline`.

These metrics feed:

- Prometheus Gauges/Histograms per task
- Structured log events for anomalies
- Optional websocket topic `/ws/telemetry` for UI display

## Safety Hooks

Emergency-stop sequences can request immediate execution priority by invoking `coordinator.run_immediately(task_name)` which bumps the task and logs a safety override.
