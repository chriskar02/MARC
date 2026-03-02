from __future__ import annotations

import time
from typing import Any, Dict

import cv2
import numpy as np
from pypylon import pylon

from app.shared.schemas import WorkerPayload, WorkerPayloadType


def run(control_conn, data_queue, config: Dict[str, Any]) -> None:
    """Camera worker that streams frames from Basler camera using pypylon."""

    name = config.get("name", "basler_camera")
    fps = float(config.get("fps", 30))
    interval = 1.0 / fps
    last_heartbeat = time.time()
    running = True
    frame_count = 0
    
    print(f"[CameraWorker] Starting {name}, FPS={fps:.1f}")
    print(f"[CameraWorker] Data queue: {data_queue}")
    print(f"[CameraWorker] Control connection: {control_conn}")
    
    # Initialize Basler camera with retry logic
    camera = None
    converter = None
    use_fallback = True
    target_serial = config.get("serial", None)  # assigned from main.py config
    MAX_RETRIES = 3

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            tlFactory = pylon.TlFactory.GetInstance()
            print(f"[CameraWorker:{name}] Attempt {attempt}/{MAX_RETRIES} — enumerating...")
            devices = tlFactory.EnumerateDevices()
            print(f"[CameraWorker:{name}] Found {len(devices)} device(s)")

            if len(devices) == 0:
                print(f"[CameraWorker:{name}] No devices found, retrying...")
                import time as _t; _t.sleep(2)
                continue

            device_to_use = None
            for i, dev in enumerate(devices):
                dev_info = pylon.CDeviceInfo(dev)
                serial = dev_info.GetSerialNumber()
                model = dev_info.GetModelName()
                print(f"[CameraWorker:{name}]   [{i}] {model} SN={serial}")
                if serial == target_serial:
                    device_to_use = dev

            if device_to_use is None:
                print(f"[CameraWorker:{name}] Target SN {target_serial} not found")
                import time as _t; _t.sleep(2)
                continue

            camera = pylon.InstantCamera(tlFactory.CreateDevice(device_to_use))
            camera.Open()
            camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            converter = pylon.ImageFormatConverter()
            converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            use_fallback = False
            print(f"[CameraWorker:{name}] Camera SN {target_serial} opened and grabbing")
            break

        except Exception as e:
            print(f"[CameraWorker:{name}] Attempt {attempt} failed: {type(e).__name__}: {e}")
            camera = None
            converter = None
            if attempt < MAX_RETRIES:
                import time as _t; _t.sleep(2)

    if use_fallback:
        print(f"[CameraWorker:{name}] All attempts failed — using test pattern")

    while running:
        if control_conn.poll():
            message = control_conn.recv()
            command = message.get("command")
            if command == "shutdown":
                running = False
            elif command == "set_fps":
                fps = max(float(message.get("value", 30)), 1.0)
                interval = 1.0 / fps

        frame = None
        frame_bytes = None
        
        # Try to grab from camera
        if camera and not use_fallback and camera.IsGrabbing() and converter:
            try:
                # Use longer timeout to wait for frames properly
                grab_result = camera.RetrieveResult(500, pylon.TimeoutHandling_ThrowException)
                
                if grab_result.GrabSucceeded():
                    # Convert to BGR
                    converter.OutputPixelFormat = pylon.PixelType_BGR8packed
                    image = converter.Convert(grab_result)
                    frame = image.GetArray().copy()
                else:
                    error_code = grab_result.GetErrorCode()
                    print(f"[CameraWorker] Grab failed with error code: {error_code}")
                
                grab_result.Release()
                
            except pylon.TimeoutException:
                # Timeout is expected when no frames are available yet
                pass
            except Exception as e:
                print(f"[CameraWorker] Error capturing frame: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                use_fallback = True
                if camera:
                    try:
                        camera.StopGrabbing()
                        camera.Close()
                    except:
                        pass
                    camera = None

        # Fall back to test pattern if no real frame
        if frame is None or use_fallback:
            frame = np.ones((480, 640, 3), dtype=np.uint8) * 50
            
            # Draw checkerboard pattern
            square_size = 40
            for y in range(0, 480, square_size):
                for x in range(0, 640, square_size):
                    if ((x // square_size) + (y // square_size)) % 2 == 0:
                        frame[y : y + square_size, x : x + square_size] = [100, 100, 100]
            
            # Add frame number text
            cv2.putText(
                frame,
                f"Frame {frame_count} (TEST PATTERN)",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (200, 200, 200),
                2,
            )
        
        # Ensure frame is BGR for encoding
        if frame is not None:
            if len(frame.shape) == 2:  # Grayscale
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            
            # Resize large frames to reasonable size for streaming (max 800 width)
            frame_height, frame_width = frame.shape[:2]
            if frame_width > 800:
                scale = 800 / frame_width
                new_width = int(frame_width * scale)
                new_height = int(frame_height * scale)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                frame_width, frame_height = new_width, new_height
            
            # Convert to JPEG bytes (much faster than PNG)
            success, frame_bytes = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            if success:
                payload = WorkerPayload(
                    worker=name,
                    sequence_id=frame_count,
                    monotonic_ts=time.monotonic(),
                    payload_type=WorkerPayloadType.frame,
                    data=frame_bytes.tobytes(),
                    metadata={"format": "jpeg", "width": frame_width, "height": frame_height},
                )
                try:
                    data_queue.put(payload, block=False)
                    frame_count += 1
                except Exception:
                    pass  # queue full, skip frame

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
    
    # Cleanup
    if camera:
        try:
            if camera.IsGrabbing():
                camera.StopGrabbing()
            camera.Close()
            print("[CameraWorker] Camera closed")
        except Exception as e:
            print(f"[CameraWorker] Error closing camera: {e}")
