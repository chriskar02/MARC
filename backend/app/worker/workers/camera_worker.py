from __future__ import annotations

import os
import time
from typing import Any, Dict

from ...shared.schemas import WorkerPayload, WorkerPayloadType


def run(control_conn, data_queue, config: Dict[str, Any]) -> None:
    """Simulated camera worker that streams mock frames to the main process."""

    name = config.get("name", "basler_camera")
    interval = 1.0 / float(config.get("mock_fps", 30))
    last_heartbeat = time.time()
    running = True

    while running:
        if control_conn.poll():
            message = control_conn.recv()
            command = message.get("command")
            if command == "shutdown":
                running = False
            elif command == "set_fps":
                interval = 1.0 / max(float(message.get("value", 30)), 1.0)

        frame_bytes = os.urandom(512)
        payload = WorkerPayload(
            worker=name,
            sequence_id=int(time.time() * 1000),
            monotonic_ts=time.monotonic(),
            payload_type=WorkerPayloadType.frame,
            data=frame_bytes,
            metadata={"simulated": True},
        )
        data_queue.put(payload)

        now = time.time()
        if (now - last_heartbeat) >= 0.1:
            heartbeat = WorkerPayload(
                worker=name,
                sequence_id=0,
                monotonic_ts=time.monotonic(),
                payload_type=WorkerPayloadType.heartbeat,
                data=b"",
                metadata=None,
            )
            data_queue.put(heartbeat)
            last_heartbeat = now

        time.sleep(interval)
