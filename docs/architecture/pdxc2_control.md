# PDXC2 Compact ORIC® Piezo Inertia Stage Controller Integration

## Overview

The PDXC2 is a benchtop controller for Thorlabs piezo inertia (ORIC) stages like the PDX1/M. This document describes the async wrapper implementation, integration points, and usage patterns.

## Hardware Specifications

### Device
- **Product**: Thorlabs PDXC2 Compact ORIC® Piezo Inertia Stage Controller
- **Controlled Stages**: PDX1/M (1-axis piezo stepper stage)
- **Communication**: USB (Virtual COM port or Kinesis API)
- **Python Support**: Thorlabs Kinesis .NET library via `pythonnet`

### Control Modes

#### Open-Loop Control
- **Use Case**: Fast, uncalibrated moves without feedback
- **Speed**: ~milliseconds per move cycle
- **Accuracy**: ±0.5 µm typical (stepper mode)
- **Range**: ±10,000,000 steps
- **Advantages**: Fast, no calibration required
- **Disadvantages**: No position feedback, accumulates error over time

#### Closed-Loop Control
- **Use Case**: Precise position targeting with encoder feedback
- **Speed**: ~tens of milliseconds per move (slower than open-loop)
- **Accuracy**: ±10 nm (sub-micron with encoder)
- **Range**: ±1,000,000 nm
- **Advantages**: Precise absolute positioning, error correction
- **Disadvantages**: Requires calibration/homing, slower

## Architecture

### PDXC2Controller Class

Located in `backend/app/services/hardware/pdxc2.py`

**Initialization**:
```python
controller = PDXC2Controller(serial_number="112000001")
```

**Lifecycle**:
1. **connect()** – Establish USB/Kinesis connection, start 250ms polling
2. **enable_device()** – Power up and enable motion
3. [Optional] **home() / calibrate()** – Run closed-loop calibration
4. **move_open_loop(step_size)** OR **move_closed_loop(target_nm)**
5. **wait_move_complete()** – Poll until motion stops
6. **disconnect()** – Stop polling and close connection

### Key Methods

#### Connection Management
```python
async def connect() -> bool
    """Connect to PDXC2 device, build device list, start polling (250ms)."""

async def disconnect() -> bool
    """Stop polling and disconnect."""

async def enable_device() -> bool
    """Enable device for operation (power up stage)."""

async def disable_device() -> bool
    """Disable device (power down stage)."""
```

#### Control Mode Selection
```python
async def set_open_loop_mode() -> bool
    """Switch to step-based control (fast, uncalibrated)."""

async def set_closed_loop_mode() -> bool
    """Switch to position feedback control (precise, requires homing)."""
```

#### Motion Control (Open-Loop)
```python
async def move_open_loop(step_size: int) -> bool
    """
    Move stage by step count.
    
    Args:
        step_size: Integer in range [-10000000, +10000000]
                  Positive = extend, Negative = retract
    
    Returns:
        True if move initiated
    """
```

#### Motion Control (Closed-Loop)
```python
async def move_closed_loop(target_nm: int) -> bool
    """
    Move stage to absolute position with encoder feedback.
    
    Args:
        target_nm: Position in nanometers [-1000000, +1000000]
                  Range: ±1 mm with 10 nm minimum step
    
    Returns:
        True if move initiated
        
    Note:
        Requires prior home() call to establish reference position.
    """

async def home(timeout_ms: int = 60000) -> bool
    """
    Home the stage (closed-loop mode only).
    
    Runs pulse parameter optimization and sets encoder reference.
    Must complete before closed-loop moves.
    
    Args:
        timeout_ms: Timeout for calibration process
        
    Returns:
        True if successful
    """
```

#### Motion Monitoring
```python
async def wait_move_complete(timeout_ms: int = 30000) -> bool
    """
    Block until current move completes (position steady-state).
    
    Polls GetCurrentPosition() every 500ms until no change detected.
    """

async def get_current_position() -> int
    """Get current position (steps or nm depending on mode)."""

async def stop_move() -> bool
    """Immediately halt motion."""
```

#### Status & Diagnostics
```python
async def get_status() -> PDXC2Status
    """
    Returns:
        PDXC2Status(
            connected: bool,
            enabled: bool,
            homed: bool,
            current_position: int,
            position_mode: str,  # "open_loop" or "closed_loop"
            is_moving: bool,
            error: Optional[str]
        )
    """
```

## Integration Points

### FastAPI Endpoints

**Device Control Endpoint**: `POST /api/commands/device`

Supported commands:
- `pdxc2_connect` – Establish connection
- `pdxc2_disconnect` – Close connection
- `pdxc2_enable` – Power up stage
- `pdxc2_disable` – Power down stage
- `pdxc2_calibrate` or `pdxc2_home` – Run calibration (closed-loop)
- `pdxc2_set_open_loop` – Switch to open-loop mode
- `pdxc2_set_closed_loop` – Switch to closed-loop mode

**Request**:
```json
{
  "command": "pdxc2_enable"
}
```

**Response**:
```json
{
  "enabled": true,
  "connected": true,
  "homed": false,
  "current_position": 0,
  "position_mode": "open_loop",
  "is_moving": false,
  "error": null
}
```

### Dependency Injection

The PDXC2Controller is registered as a FastAPI dependency:

```python
# In commands.py
async def get_pdxc2(settings: Settings = Depends(get_settings)) -> PDXC2Controller:
    global _pdxc2_controller
    if _pdxc2_controller is None:
        serial = getattr(settings, "pdxc2_serial", "112000001")
        dll_path = getattr(settings, "kinesis_dll_path", None)
        if dll_path:
            set_kinesis_dll_path(dll_path)
        _pdxc2_controller = PDXC2Controller(serial_number=serial)
    return _pdxc2_controller
```

### Event Bus Integration (Future)

Once fully integrated, telemetry will be published to the event bus for WebSocket broadcasting:

```
Topic: "pdxc2/state"
Payload: {
    "connected": bool,
    "enabled": bool,
    "position": int,
    "mode": "open_loop" | "closed_loop",
    "timestamp": float
}
```

## Configuration

### Environment Variables

```dotenv
# .env
KINESIS_DLL_PATH=C:\Program Files\Thorlabs\Kinesis
PDXC2_SERIAL=112000001
PDXC2_DEFAULT_MODE=open_loop
```

### Pydantic Settings

In `backend/app/core/config.py`:

```python
class Settings(BaseSettings):
    kinesis_dll_path: str = Field(default="", description="Path to Thorlabs Kinesis DLLs")
    pdxc2_serial: str = Field(default="112000001", description="Serial number of PDXC2 device")
    pdxc2_default_mode: str = Field(default="open_loop", description="Default control mode")
```

## Usage Examples

### Basic Open-Loop Move

```python
controller = PDXC2Controller(serial_number="112000001")

async with controller.managed_connection():
    # Connect and enable
    await controller.enable_device()
    
    # Move 5000 steps forward
    await controller.set_open_loop_mode()
    await controller.move_open_loop(5000)
    
    # Wait for move to complete
    await controller.wait_move_complete(timeout_ms=10000)
    
    # Get final position
    pos = await controller.get_current_position()
    print(f"Final position: {pos} steps")
```

### Closed-Loop Calibration & Move

```python
controller = PDXC2Controller(serial_number="112000001")

async with controller.managed_connection():
    await controller.enable_device()
    
    # Calibrate stage (requires encoder on PDX1/M)
    success = await controller.home(timeout_ms=60000)
    if not success:
        print("Calibration failed!")
        return
    
    # Switch to closed-loop and move to 500µm (500000nm)
    await controller.set_closed_loop_mode()
    await controller.move_closed_loop(500000)
    
    # Wait and verify
    await controller.wait_move_complete()
    pos = await controller.get_current_position()
    print(f"Final position: {pos} nm = {pos / 1000} µm")
```

### Integration with FastAPI

```python
# In your FastAPI endpoint:
@router.post("/api/commands/device")
async def device_control(
    cmd: DeviceCommand,
    pdxc2: PDXC2Controller = Depends(get_pdxc2)
):
    if cmd.command == "pdxc2_calibrate":
        success = await pdxc2.connect()
        if success:
            await pdxc2.enable_device()
            success = await pdxc2.home()
        status = await pdxc2.get_status()
        return {**status.__dict__, "calibrated": success}
```

## Error Handling & Recovery

### Common Issues

1. **DLL not found**: Ensure `KINESIS_DLL_PATH` environment variable is set to Thorlabs Kinesis installation directory.

2. **Device not found**: Verify:
   - USB cable is connected
   - Device is powered on
   - Serial number matches device label
   - No other application is controlling the device

3. **Closed-loop move fails**: Must call `home()` first to calibrate encoder reference.

4. **Move timeout**: Increase `timeout_ms` or check if device is jammed.

### Structured Logging

All operations are logged via `structlog` with task context:

```python
logger.info("pdxc2_move_started", step_size=5000, task="move_x_stage")
logger.error("pdxc2_home_failed", error="Timeout", timeout_ms=60000)
```

## Performance Characteristics

### Latency Budget

- **Connect**: ~500ms (first time, DLL load)
- **Enable**: ~250ms (device power-up + polling start)
- **Open-loop move**: ~5-50ms (initiates stepper, polling frequency 250ms)
- **Get position**: ~2-5ms (cached polling)
- **Closed-loop move**: ~10-100ms (depends on distance)
- **Home/calibrate**: ~10-60 seconds (device-specific optimization)

### Threading Model

All blocking Kinesis .NET calls use `asyncio.to_thread()`:

```python
# Non-blocking wrapper
pos = await asyncio.to_thread(self.device.GetCurrentPosition)

# Equivalent to:
loop = asyncio.get_running_loop()
pos = await loop.run_in_executor(None, self.device.GetCurrentPosition)
```

This prevents GIL blocking and allows concurrent operations.

## Testing

### Simulator Mode

Thorlabs Kinesis supports simulation mode (no hardware required):

```python
# Enable before initialization:
SimulationManager.Instance.InitializeSimulations()

# Run tests against virtual device
```

### Unit Test Example

```python
@pytest.mark.asyncio
async def test_pdxc2_open_loop_move():
    controller = PDXC2Controller(serial_number="112000001")
    
    async with controller.managed_connection():
        await controller.enable_device()
        await controller.set_open_loop_mode()
        
        success = await controller.move_open_loop(1000)
        assert success
        
        complete = await controller.wait_move_complete(timeout_ms=5000)
        assert complete
        
        pos = await controller.get_current_position()
        assert pos == 1000
```

## References

- **Thorlabs Examples**: https://github.com/Thorlabs/Motion_Control_Examples/tree/main/Python/Kinesis/Benchtop/PDXC2
- **Kinesis Software**: https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=Motion_Control
- **APT Serial Commands**: Available from Thorlabs Software download page
- **pythonnet Documentation**: https://pythonnet.github.io/

## Future Enhancements

1. **Event Bus Integration**: Publish position updates to WebSocket clients
2. **Multi-axis Support**: Handle multiple PDX stages (if PDXC2 supports it)
3. **Callbacks**: Register .NET event handlers for move completion
4. **Caching**: Cache position/status for polling clients
5. **Error Recovery**: Automatic reconnect with exponential backoff
6. **Performance Optimization**: Use hardware triggers instead of polling where possible
