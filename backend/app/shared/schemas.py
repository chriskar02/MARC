from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WorkerPayloadType(str, Enum):
    frame = "frame"
    ft_sample = "ft_sample"
    log = "log"
    heartbeat = "heartbeat"


class WorkerPayload(BaseModel):
    worker: str
    sequence_id: int = Field(default=0)
    monotonic_ts: float = Field(description="Monotonic timestamp from the worker process")
    payload_type: WorkerPayloadType
    data: bytes = Field(description="Binary payload specific to the worker")
    metadata: Optional[dict] = None


class ControlMessage(BaseModel):
    command: str
    args: dict = Field(default_factory=dict)
