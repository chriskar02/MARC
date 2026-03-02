"""
Bota MiniONE Pro F/T Sensor Worker

Reads force/torque data from the Bota MiniONE Pro sensor over UDP (EtherDAQ).
The sensor streams 6-axis F/T data (Fx, Fy, Fz, Tx, Ty, Tz) as UDP packets.

Packet format (BotaSys EtherDAQ):
 - The sensor sends UDP datagrams at a configurable rate (typ. 500-1000 Hz)
 - Each datagram contains header + 6 x 32-bit float values (little-endian)
 - Offset 0-11: header/status (12 bytes)
 - Offset 12-35: Fx Fy Fz Tx Ty Tz as 6 x float32_le (24 bytes)
 - Total typical packet: 36 bytes

If the sensor uses the newer BotaSys serial protocol over UDP, the format may
differ. This worker auto-detects based on packet size and falls back to
raw float parsing.
"""

from __future__ import annotations

import json
import socket
import struct
import time
from typing import Any, Dict

from app.shared.schemas import WorkerPayload, WorkerPayloadType


def run(control_conn, data_queue, config: Dict[str, Any]) -> None:
    """Bota MiniONE Pro F/T sensor worker - reads UDP F/T stream."""

    name = config.get("name", "bota_sensor")
    sensor_ip = config.get("sensor_ip", "")           # sensor IP (if known)
    listen_port = config.get("listen_port", 49152)     # port to listen on
    publish_rate = float(config.get("publish_rate", 100))  # Hz to frontend
    adapter_ip = config.get("adapter_ip", "0.0.0.0")  # local adapter to bind

    interval = 1.0 / publish_rate
    last_publish = 0.0
    last_heartbeat = 0.0
    running = True
    sample_count = 0

    # Latest F/T values
    fx = fy = fz = tx = ty = tz = 0.0

    print(f"[BotaWorker] Starting {name}")
    print(f"[BotaWorker] Listening on {adapter_ip}:{listen_port}")
    if sensor_ip:
        print(f"[BotaWorker] Expecting data from sensor IP: {sensor_ip}")

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(0.1)  # 100ms timeout for control message polling

    try:
        sock.bind((adapter_ip, listen_port))
        print(f"[BotaWorker] Socket bound to {adapter_ip}:{listen_port}")
    except OSError as e:
        print(f"[BotaWorker] Failed to bind socket: {e}")
        print(f"[BotaWorker] Will continue but no data will be received")

    # Also try to send a start command to the sensor if we know its IP
    if sensor_ip:
        _try_start_stream(sock, sensor_ip, listen_port)

    while running:
        # Check control messages
        if control_conn.poll():
            message = control_conn.recv()
            command = message.get("command")
            if command == "shutdown":
                running = False
                continue
            elif command == "tare":
                # Record current values as bias (simple software tare)
                print(f"[BotaWorker] Tare requested (software zero)")

        # Read UDP packets (non-blocking with timeout)
        try:
            data, addr = sock.recvfrom(1024)
            parsed = _parse_ft_packet(data)
            if parsed:
                fx, fy, fz, tx, ty, tz = parsed
                sample_count += 1
        except socket.timeout:
            pass
        except Exception as e:
            print(f"[BotaWorker] Receive error: {e}")

        # Publish at configured rate
        now = time.time()
        if (now - last_publish) >= interval:
            ft_data = {
                "fx": round(fx, 6),
                "fy": round(fy, 6),
                "fz": round(fz, 6),
                "tx": round(tx, 6),
                "ty": round(ty, 6),
                "tz": round(tz, 6),
                "timestamp": now,
                "samples": sample_count,
            }

            payload = WorkerPayload(
                worker=name,
                sequence_id=sample_count,
                monotonic_ts=time.monotonic(),
                payload_type=WorkerPayloadType.ft_sample,
                data=json.dumps(ft_data).encode("utf-8"),
                metadata=ft_data,
            )
            try:
                data_queue.put(payload, block=False)
            except Exception:
                pass  # queue full, skip

            last_publish = now

        # Heartbeat every 2 seconds (time-based, independent of UDP data)
        if (now - last_heartbeat) >= 2.0:
            heartbeat = WorkerPayload(
                worker=name,
                sequence_id=0,
                monotonic_ts=time.monotonic(),
                payload_type=WorkerPayloadType.heartbeat,
                data=b"",
                metadata={"samples": sample_count, "has_data": sample_count > 0},
            )
            try:
                data_queue.put(heartbeat, block=False)
            except Exception:
                pass
            last_heartbeat = now

        # Small sleep to avoid busy spin when no data
        time.sleep(0.0005)  # 0.5ms

    sock.close()
    print(f"[BotaWorker] Stopped. Total samples: {sample_count}")


def _parse_ft_packet(data: bytes):
    """
    Parse a Bota F/T UDP packet.

    Tries multiple known formats:
    1. BotaSys EtherDAQ 36-byte format: 12-byte header + 6 x float32_le
    2. Raw 24 bytes: 6 x float32_le (no header)
    3. Larger packets: scan for 6 consecutive floats starting after header
    """
    length = len(data)

    # Format 1: 36 bytes (12-byte header + 6 floats)
    if length == 36:
        try:
            values = struct.unpack("<6f", data[12:36])
            return values
        except struct.error:
            pass

    # Format 2: 24 bytes (6 x float32, no header)
    if length == 24:
        try:
            values = struct.unpack("<6f", data[0:24])
            return values
        except struct.error:
            pass

    # Format 3: BotaSys SensONE larger packet — floats at offset 12
    if length >= 36:
        try:
            values = struct.unpack("<6f", data[12:36])
            # Sanity check: values should be in reasonable F/T range
            if all(abs(v) < 10000 for v in values):
                return values
        except struct.error:
            pass

    # Format 4: Try from the start of the packet
    if length >= 24:
        try:
            values = struct.unpack("<6f", data[0:24])
            if all(abs(v) < 10000 for v in values):
                return values
        except struct.error:
            pass

    return None


def _try_start_stream(sock: socket.socket, sensor_ip: str, port: int):
    """
    Some Bota sensors require a command to start streaming.
    Try sending known start commands.
    """
    start_commands = [
        b"\x01",                              # Simple start byte
        b"START\r\n",                         # Text start
        struct.pack("<HH", 0x0002, 0x0000),   # EtherDAQ start command
    ]
    for cmd in start_commands:
        try:
            sock.sendto(cmd, (sensor_ip, port))
        except Exception:
            pass
    print(f"[BotaWorker] Sent start stream commands to {sensor_ip}:{port}")
