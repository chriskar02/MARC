import asyncio
import websockets
import json

async def test():
    try:
        async with websockets.connect("ws://127.0.0.1:8000/ws") as ws:
            await ws.send(json.dumps({"subscribe": ["camera.split_optics_camera"]}))
            for i in range(3):
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                if isinstance(msg, bytes):
                    # Check for JPEG header (0xFF 0xD8)
                    is_jpeg = msg[:2] == b'\xff\xd8'
                    print(f"Frame {i+1}: {len(msg)} bytes {'JPEG' if is_jpeg else 'unknown'}")
                else:
                    print(f"Frame {i+1}: text: {msg[:200]}")
            print("OK - camera streaming")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
