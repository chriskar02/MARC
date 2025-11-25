"""
Simple test script for PDXC2 PDX1/M stage controller integration.

Run with: python test_pdxc2.py

Tests:
1. DLL loading and imports
2. Device discovery
3. Connection lifecycle
4. Open-loop moves
5. Closed-loop calibration (if encoder present)
"""

import asyncio
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.hardware.pdxc2 import PDXC2Controller, set_kinesis_dll_path


async def test_basic_connection():
    """Test 1: Basic connection without hardware."""
    logger.info("=" * 60)
    logger.info("TEST 1: Basic Connection (Dry Run)")
    logger.info("=" * 60)
    
    try:
        from app.core.config import get_settings
        settings = get_settings()
        serial = settings.pdxc2_serial
        
        controller = PDXC2Controller(serial_number=serial)
        logger.info(f"✓ Controller instantiated: {controller.serial_number}")
        
        status = await controller.get_status()
        logger.info(f"✓ Initial status: {status}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Connection test failed: {e}")
        return False


async def test_with_device():
    """Test 2: Test with actual hardware (requires device connected)."""
    logger.info("=" * 60)
    logger.info("TEST 2: Connection with Hardware")
    logger.info("=" * 60)
    
    try:
        from app.core.config import get_settings
        settings = get_settings()
        serial = settings.pdxc2_serial
        
        # Optional: Set custom DLL path
        dll_path = settings.kinesis_dll_path
        if dll_path:
            set_kinesis_dll_path(dll_path)
        
        logger.info(f"Connecting to PDXC2 (SN: {serial})...")
        controller = PDXC2Controller(serial_number=serial)
        
        # Try to connect
        logger.info("Connecting to PDXC2...")
        connected = await controller.connect()
        
        if not connected:
            logger.warning("✗ Failed to connect. Ensure:")
            logger.warning("  1. PDXC2 is powered on")
            logger.warning("  2. USB cable is connected")
            logger.warning("  3. Serial number matches device label")
            logger.warning("  4. Kinesis software is installed")
            return False
        
        logger.info("✓ Connected to PDXC2")
        
        # Try to enable device
        logger.info("Enabling device...")
        enabled = await controller.enable_device()
        if not enabled:
            logger.warning("✗ Failed to enable device")
            await controller.disconnect()
            return False
        logger.info("✓ Device enabled")
        
        # Check status
        status = await controller.get_status()
        logger.info(f"✓ Device status: {status}")
        
        # Test open-loop mode
        logger.info("\nTesting open-loop mode...")
        await controller.set_open_loop_mode()
        logger.info("✓ Set to open-loop mode")
        
        # Do a small test move
        logger.info("Initiating small test move (100 steps)...")
        move_ok = await controller.move_open_loop(100)
        if move_ok:
            logger.info("✓ Move initiated")
            
            # Wait for completion
            complete = await controller.wait_move_complete(timeout_ms=5000)
            if complete:
                pos = await controller.get_current_position()
                logger.info(f"✓ Move complete. Position: {pos} steps")
            else:
                logger.warning("✗ Move timeout")
        else:
            logger.warning("✗ Move initiation failed")
        
        # Cleanup
        logger.info("\nDisconnecting...")
        await controller.disconnect()
        logger.info("✓ Disconnected")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Hardware test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_via_fastapi():
    """Test 3: Test through FastAPI endpoint."""
    logger.info("=" * 60)
    logger.info("TEST 3: FastAPI Endpoint Integration")
    logger.info("=" * 60)
    
    try:
        import httpx
        
        # Ensure backend is running on localhost:8000
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            # Test connection
            logger.info("Sending pdxc2_connect command...")
            response = await client.post(
                "/api/commands/device",
                json={"command": "pdxc2_connect"}
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✓ Response: {data}")
                return True
            else:
                logger.error(f"✗ HTTP {response.status_code}: {response.text}")
                return False
                
    except ImportError:
        logger.warning("✗ httpx not installed. Install with: pip install httpx")
        return False
    except Exception as e:
        logger.error(f"✗ FastAPI test failed: {e}")
        logger.info("  Ensure backend is running: python -m uvicorn app.main:app --reload")
        return False


async def interactive_test():
    """Interactive test mode for manual testing."""
    logger.info("=" * 60)
    logger.info("INTERACTIVE TEST MODE")
    logger.info("=" * 60)
    
    controller = PDXC2Controller(serial_number="112000001")
    
    commands = {
        "1": ("connect", controller.connect),
        "2": ("enable", controller.enable_device),
        "3": ("disable", controller.disable_device),
        "4": ("set_open_loop", controller.set_open_loop_mode),
        "5": ("set_closed_loop", controller.set_closed_loop_mode),
        "6": ("home", lambda: controller.home(timeout_ms=60000)),
        "7": ("get_status", controller.get_status),
        "8": ("disconnect", controller.disconnect),
        "q": ("quit", None),
    }
    
    print("\nAvailable commands:")
    for key, (name, _) in commands.items():
        if key != "q":
            print(f"  {key} - {name}")
    print("  q - quit")
    
    while True:
        try:
            cmd = input("\nEnter command: ").strip().lower()
            
            if cmd == "q":
                logger.info("Exiting...")
                break
            
            if cmd == "6":
                # move_open_loop needs input
                try:
                    steps = int(input("Enter step count (-10000000 to +10000000): "))
                    result = await controller.move_open_loop(steps)
                    logger.info(f"Move result: {result}")
                    if result:
                        logger.info("Waiting for move to complete...")
                        complete = await controller.wait_move_complete()
                        logger.info(f"Move complete: {complete}")
                except ValueError:
                    logger.error("Invalid step count")
                continue
            
            if cmd in commands:
                name, func = commands[cmd]
                if func is None:
                    logger.info("Quitting...")
                    break
                
                result = await func()
                logger.info(f"{name}: {result}")
            else:
                logger.error("Unknown command")
                
        except KeyboardInterrupt:
            logger.info("\nInterrupt received, exiting...")
            break
        except Exception as e:
            logger.error(f"Error: {e}")


async def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("PDXC2 PDX1/M Stage Controller Test Suite")
    logger.info("=" * 60 + "\n")
    
    # Check if we should run interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        await interactive_test()
        return
    
    # Run automated tests
    results = []
    
    # Test 1: Basic instantiation (no hardware required)
    results.append(("Basic Instantiation", await test_basic_connection()))
    
    # Test 2: Hardware connection (requires device)
    logger.info("\nAttempting hardware test (may fail if device not connected)...")
    results.append(("Hardware Connection", await test_with_device()))
    
    # Test 3: FastAPI integration (requires backend running)
    logger.info("\nNote: FastAPI test requires backend running on port 8000")
    logger.info("Start with: python -m uvicorn app.main:app --reload")
    
    # Print results
    logger.info("\n" + "=" * 60)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{name}: {status}")
    
    # Overall result
    all_passed = all(result for _, result in results)
    logger.info("=" * 60)
    if all_passed:
        logger.info("✓ All tests passed!")
    else:
        logger.warning("✗ Some tests failed. See details above.")
    
    # Usage instructions
    logger.info("\n" + "=" * 60)
    logger.info("NEXT STEPS")
    logger.info("=" * 60)
    logger.info("1. Backend: python -m uvicorn app.main:app --reload")
    logger.info("2. Frontend: cd frontend && npm run dev")
    logger.info("3. Test Settings Panel: http://localhost:5173")
    logger.info("4. Interactive mode: python test_pdxc2.py --interactive")
    logger.info("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
