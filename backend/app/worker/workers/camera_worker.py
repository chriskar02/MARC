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
    
    # Initialize Basler camera
    camera = None
    tlFactory = pylon.TlFactory.GetInstance()
    target_serial = "25240869"
    
    try:
        # Try to create camera from first available device
        print("[CameraWorker] Attempting to create camera...")
        devices = tlFactory.EnumerateDevices()
        print(f"[CameraWorker] Found {len(devices)} device(s)")
        
        if len(devices) > 0:
            # Try to find camera by serial number
            device_to_use = None
            for i, dev in enumerate(devices):
                dev_info = pylon.CDeviceInfo(dev)
                serial = dev_info.GetSerialNumber()
                model = dev_info.GetModelName()
                print(f"[CameraWorker] Device {i}: {model} (SN: {serial})")
                if serial == target_serial:
                    device_to_use = dev
                    print(f"[CameraWorker] Found target camera with SN {target_serial}")
                    break
            
            # If target not found, use first device
            if device_to_use is None:
                print(f"[CameraWorker] Target camera SN {target_serial} not found, using first device")
                device_to_use = devices[0]
            
            camera = pylon.InstantCamera(tlFactory.CreateDevice(device_to_use))
            print(f"[CameraWorker] Trying to open: {camera.GetDeviceInfo().GetModelName()}")
            camera.Open()
            print(f"[CameraWorker] Camera opened successfully")
            use_fallback = False
        else:
            print("[CameraWorker] No camera device found")
            use_fallback = True
            
    except Exception as e:
        print(f"[CameraWorker] Failed to create/open camera: {e}")
        print(f"[CameraWorker] Exception type: {type(e).__name__}")
        use_fallback = True
        camera = None

    # Start grabbing if camera is available
    converter = None
    if camera and not use_fallback:
        try:
            camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            converter = pylon.ImageFormatConverter()
            converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            print("[CameraWorker] Camera grabbing started successfully")
        except Exception as e:
            print(f"[CameraWorker] Failed to start grabbing: {e}")
            use_fallback = True
            if camera:
                try:
                    camera.Close()
                except:
                    pass
                camera = None

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
                    if frame is not None:
                        print(f"[CameraWorker] Frame {frame_count}: captured {frame.shape}")
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
            
            # Convert to PNG bytes
            success, frame_bytes = cv2.imencode(".png", frame, [cv2.IMWRITE_PNG_COMPRESSION, 6])
            
            if success:
                print(f"[CameraWorker] Frame {frame_count}: PNG {len(frame_bytes)} bytes, {frame_width}x{frame_height}")
                payload = WorkerPayload(
                    worker=name,
                    sequence_id=frame_count,
                    monotonic_ts=time.monotonic(),
                    payload_type=WorkerPayloadType.frame,
                    data=frame_bytes.tobytes(),
                    metadata={"format": "png", "width": frame_width, "height": frame_height},
                )
                try:
                    data_queue.put(payload, block=False)
                    print(f"[CameraWorker] Frame {frame_count} queued successfully")
                    frame_count += 1
                except Exception as e:
                    print(f"[CameraWorker] Failed to queue frame: {e}")
            else:
                print(f"[CameraWorker] Failed to encode frame as PNG")

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
