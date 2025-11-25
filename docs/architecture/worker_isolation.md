# Latency-Sensitive Worker Isolation

High-rate hardware loops (Basler cameras, Bota F/T sensor) are placed inside dedicated worker processes to eliminate interference from the ASGI loop or other drivers.

## Goals

- shield critical loops from Python GIL contention and GC pauses
- allow per-device process restarts without taking down FastAPI
- provide streaming IPC optimized for small binary payloads
- expose health/latency metrics to the main app

## Components

1. **Worker Manager (`app/worker/process_manager.py`)**
   - starts/stops child processes using `multiprocessing` (spawn start method)
   - injects environment variables (DLL paths) and configuration payloads via command args or pipes
   - monitors heartbeat intervals using an async task; restarts workers after configurable backoff

2. **IPC Layer (`app/worker/ipc.py`)**
   - structured messages defined with `pydantic` models (JSON) for control plane
   - shared-memory ring buffer or `multiprocessing.Queue` for data plane
   - asynchronous adapters wrapping `asyncio.Protocol` for clean integration with FastAPI event loop

3. **Device Workers (`app/worker/workers/*.py`)**
   - e.g., `camera_worker.py`, `ft_sensor_worker.py`
   - run synchronous vendor SDK loops (pypylon, Bota driver)
   - push telemetry frames onto IPC queue; respond to control commands (change frame rate, start recording)

4. **Bridge Service (`app/services/bridges/worker_bridge.py`)**
   - subscribes to worker data queues
   - republishes payloads via event bus/websockets
   - exposes metrics (latency, dropped frames, queue depth)

## Message Flow

```
FastAPI (main loop)
  └─ WorkerManager spawns CameraWorker
       ├─ Control channel: bidirectional JSON over multiprocessing Pipe
       └─ Data channel: shared-memory queue of `WorkerPayload` records
```

`WorkerPayload` contains monotonic timestamp, payload type (`frame`, `ft_sample`, `log`), and binary blob. The bridge converts into domain-specific schemas before emitting to clients.

## Failure Handling

- worker sends heartbeat every 100 ms
- manager detects missed heartbeats and triggers escalation: log warning, notify safety service, attempt restart
- on repeated failures, mark device degraded and expose through status endpoint

## Testing

- provide dummy worker implementations (simulated camera) used in CI
- integration tests spin manager + dummy worker and assert metrics + websocket output
