# Precision Control Desktop Stack

A FastAPI + React + Electron platform for millisecond-level control of precision hardware (Standa motors, Meca500, Bota F/T, Thorlabs PDXC2, Basler cameras, MCWHL5/LH501).

## Repository Layout

```
backend/        FastAPI app, realtime coordinator, worker manager
frontend/       Vite + React dashboard for telemetry/camera feeds
 docs/          Architecture notes (real-time coordinator, worker isolation)
```

## Backend

- `app/core/realtime.py` provides a priority scheduler that enforces jitter/deadline budgets for hardware loops.
- `app/services/bridges/worker_bridge.py` spawns isolated processes (Basler camera, Bota sensor, etc.) and republishes their payloads via the event bus.
- `app/main.py` wires the coordinator, event bus, and worker bridge into FastAPI lifespan and registers telemetry/health endpoints.

### Install & Run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Environment variables (set in `.env`) should include SDK paths like `KINESIS_DLL_PATH` and `LIBXIMC_PATH` so the worker processes can load vendor libraries.

## Frontend

- Located in `frontend/` built with Vite + React + TypeScript.
- `src/providers/WebSocketProvider.tsx` maintains resilient websocket connections and exposes `useChannel` for real-time topics such as `telemetry/realtime` or `worker/{name}/frame`.
- `src/components/camera/CameraStream.tsx` and `src/components/plots/TelemetryPanel.tsx` demonstrate how to render worker data.

### Install & Run

```powershell
cd frontend
npm install
npm run dev
```

Configure `.env` (mirrored to Vite) with:

```
VITE_BACKEND_HTTP=http://127.0.0.1:8000
VITE_BACKEND_WS_URL=ws://127.0.0.1:8000
```

## Electron (future)

The Electron wrapper will launch the FastAPI backend with the correct DLL paths and load the React build. Packaging should include Thorlabs Kinesis, Standa libximc, and Basler runtime DLLs via `electron-builder` `extraResources`.

## Testing & Simulation

- Use the included mock camera worker (`backend/app/worker/workers/camera_worker.py`) to simulate high-rate frame streaming without hardware.
- Add additional dummy workers for motors and sensors to exercise the realtime coordinator and websocket pipeline under load.

## Observability

- Prometheus metrics expose realtime task jitter/latency (`/metrics` once wired via `prometheus_client`).
- Structured logs emitted through `structlog` capture worker lifecycle, deadline misses, and safety overrides.
