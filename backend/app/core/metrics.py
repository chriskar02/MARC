from __future__ import annotations

from typing import Dict

from prometheus_client import Counter, Gauge, Histogram, REGISTRY


_TASK_LATENCY: Dict[str, Histogram] = {}
_TASK_JITTER: Dict[str, Histogram] = {}
_TASK_DEADLINES: Dict[str, Counter] = {}
_TASK_BACKLOG: Dict[str, Gauge] = {}
_WORKER_HEARTBEAT: Dict[str, Gauge] = {}


def task_latency_histogram(task_name: str) -> Histogram:
    if task_name not in _TASK_LATENCY:
        try:
            _TASK_LATENCY[task_name] = Histogram(
                f"rt_task_latency_ms_{task_name}",
                "Execution latency (ms) per realtime task",
                buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 50),
            )
        except ValueError:
            _TASK_LATENCY[task_name] = REGISTRY._names_to_collectors.get(f"rt_task_latency_ms_{task_name}")
    return _TASK_LATENCY[task_name]


def task_jitter_histogram(task_name: str) -> Histogram:
    if task_name not in _TASK_JITTER:
        try:
            _TASK_JITTER[task_name] = Histogram(
                f"rt_task_jitter_ms_{task_name}",
                "Start-time jitter (ms) per realtime task",
                buckets=(0.05, 0.1, 0.2, 0.5, 1, 2, 5),
            )
        except ValueError:
            _TASK_JITTER[task_name] = REGISTRY._names_to_collectors.get(f"rt_task_jitter_ms_{task_name}")
    return _TASK_JITTER[task_name]


def task_deadline_counter(task_name: str) -> Counter:
    if task_name not in _TASK_DEADLINES:
        try:
            _TASK_DEADLINES[task_name] = Counter(
                f"rt_task_deadline_miss_total_{task_name}",
                "Deadline misses per realtime task",
            )
        except ValueError:
            _TASK_DEADLINES[task_name] = REGISTRY._names_to_collectors.get(f"rt_task_deadline_miss_total_{task_name}")
    return _TASK_DEADLINES[task_name]


def task_backlog_gauge(task_name: str) -> Gauge:
    if task_name not in _TASK_BACKLOG:
        try:
            _TASK_BACKLOG[task_name] = Gauge(
                f"rt_task_backlog_{task_name}",
                "Number of pending tasks waiting for scheduling",
            )
        except ValueError:
            _TASK_BACKLOG[task_name] = REGISTRY._names_to_collectors.get(f"rt_task_backlog_{task_name}")
    return _TASK_BACKLOG[task_name]


def worker_heartbeat_gauge(worker_name: str) -> Gauge:
    if worker_name not in _WORKER_HEARTBEAT:
        try:
            _WORKER_HEARTBEAT[worker_name] = Gauge(
                f"worker_heartbeat_timestamp_{worker_name}",
                "Unix timestamp of the last heartbeat received from worker",
            )
        except ValueError:
            _WORKER_HEARTBEAT[worker_name] = REGISTRY._names_to_collectors.get(f"worker_heartbeat_timestamp_{worker_name}")
    return _WORKER_HEARTBEAT[worker_name]
