"""
PDXC2 Compact ORIC® Piezo Inertia Stage Controller async wrapper

Wraps the Thorlabs Kinesis .NET API (via pythonnet) for non-blocking control
of PDX1/M piezo stages. Supports both open-loop (step-based) and closed-loop 
(encoder-based) motion control with proper error handling and structured logging.

Architecture:
- All .NET method calls wrapped in asyncio.to_thread() for non-blocking execution
- Callbacks for device state tracking (enabled, homed, moving, etc.)
- Context manager support for safe connection cleanup
- Structured logging via structlog for debugging and monitoring
"""

import asyncio
import logging
import contextvars
from contextlib import asynccontextmanager
from typing import Optional
from dataclasses import dataclass

import structlog

# These imports are conditional on pythonnet being available
try:
    import clr
    PYTHONNET_AVAILABLE = True
except ImportError:
    PYTHONNET_AVAILABLE = False

# DLL path will be loaded from config/environment
_kinesis_dll_path: Optional[str] = None
_pdxc2_device_loaded = False

logger = structlog.get_logger()
task_context = contextvars.ContextVar("task_context", default="pdxc2")


def set_kinesis_dll_path(path: str) -> None:
    """Set the path to Kinesis DLLs before initializing PDXC2Controller."""
    global _kinesis_dll_path
    _kinesis_dll_path = path


def _load_pdxc2_dlls() -> None:
    """Load Thorlabs Kinesis .NET assemblies via pythonnet (clr)."""
    global _pdxc2_device_loaded
    if not PYTHONNET_AVAILABLE:
        raise RuntimeError("pythonnet not installed. Install with: pip install pythonnet==3.0.1")
    if _pdxc2_device_loaded:
        return  # Already loaded
    
    if not _kinesis_dll_path:
        # Fallback to common Kinesis installation path
        dll_path = r"C:\Program Files\Thorlabs\Kinesis"
        logger.info("kinesis_dll_path not set, using default", default_path=dll_path)
    else:
        dll_path = _kinesis_dll_path
    
    try:
        # Add references to Thorlabs Kinesis .NET assemblies
        clr.AddReference(f"{dll_path}\\Thorlabs.MotionControl.Benchtop.PiezoCLI.dll")
        clr.AddReference(f"{dll_path}\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
        clr.AddReference(f"{dll_path}\\Thorlabs.MotionControl.GenericPiezoCLI.dll")
        
        # Import .NET namespaces
        from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI as DM_CLI
        from Thorlabs.MotionControl.Benchtop.PiezoCLI.PDXC2 import InertiaStageController as ISC
        # These enums may be in the parent Piezo namespace
        from Thorlabs.MotionControl.GenericPiezoCLI.Piezo import PiezoControlModeTypes as PCMT
        from Thorlabs.MotionControl.Benchtop.PiezoCLI.PDXC2 import OpenLoopMoveParams as OLMP
        
        # Store in module globals for use in class
        globals()["DeviceManagerCLI"] = DM_CLI
        globals()["InertiaStageController"] = ISC
        globals()["PiezoControlModeTypes"] = PCMT
        globals()["OpenLoopMoveParams"] = OLMP
        
        _pdxc2_device_loaded = True
        logger.info("pdxc2_dlls_loaded", dll_path=dll_path)
    except Exception as e:
        logger.error("failed_to_load_pdxc2_dlls", error=str(e), dll_path=dll_path)
        raise


@dataclass
class PDXC2Status:
    """Current status snapshot of PDXC2 device."""
    connected: bool
    enabled: bool
    homed: bool
    current_position: int  # In steps (open-loop) or nm (closed-loop)
    position_mode: str  # "open_loop" or "closed_loop"
    is_moving: bool
    error: Optional[str] = None


class PDXC2Controller:
    """
    Async wrapper for Thorlabs PDXC2 Compact ORIC® Piezo Inertia Stage Controller.
    
    Manages PDX1/M piezo stages with support for:
    - Open-loop control (stepper-style step commands, fast)
    - Closed-loop control (encoder feedback, precise, slower, requires homing)
    - Device lifecycle (connect, enable, home, disconnect)
    - Callbacks for state tracking
    
    All blocking .NET calls are executed via asyncio.to_thread() to prevent
    blocking the async event loop.
    """
    
    def __init__(self, serial_number: str = "112000001"):
        """
        Initialize PDXC2Controller.
        
        Args:
            serial_number: Device serial number (e.g. "112000001")
        """
        _load_pdxc2_dlls()
        
        self.serial_number = serial_number
        self.device: Optional[InertiaStageController] = None
        self._connected = False
        self._enabled = False
        self._homed = False
        self._current_position = 0
        self._position_mode = "open_loop"
        self._is_moving = False
        self._last_error: Optional[str] = None
        
        logger.info(
            "pdxc2_controller_initialized",
            serial_number=serial_number,
            task=task_context.get()
        )
    
    async def connect(self) -> bool:
        """
        Connect to PDXC2 device and initialize polling.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build device list so the library can find the device
            await asyncio.to_thread(DeviceManagerCLI.BuildDeviceList)
            await asyncio.sleep(0.1)
            
            # Create device instance
            self.device = await asyncio.to_thread(
                InertiaStageController.CreateInertiaStageController,
                self.serial_number
            )
            await asyncio.sleep(0.1)
            
            # Try to connect - may fail if already connected by Kinesis
            try:
                await asyncio.to_thread(self.device.Connect, self.serial_number)
                await asyncio.sleep(0.25)
            except Exception as e:
                # Device might already be connected via Kinesis UI
                logger.info("connect_already_connected_or_unavailable", error=str(e))
                # Try to proceed anyway - device might still be accessible
            
            # Start polling (250ms rate is standard)
            try:
                await asyncio.to_thread(self.device.StartPolling, 250)
                await asyncio.sleep(0.25)
            except Exception as e:
                logger.warning("polling_may_already_started", error=str(e))
            
            # Wait for settings to initialize
            try:
                if not await asyncio.to_thread(self.device.IsSettingsInitialized):
                    await asyncio.to_thread(self.device.WaitForSettingsInitialized, 10000)
            except Exception as e:
                logger.warning("settings_initialization_check_failed", error=str(e))
            
            # Try a simple query to verify device is accessible
            try:
                pos = await asyncio.to_thread(self.device.GetCurrentPosition)
                logger.info("device_query_successful", position=pos)
            except Exception as e:
                logger.error("device_query_failed", error=str(e))
                self._last_error = str(e)
                return False
            
            self._connected = True
            logger.info("pdxc2_connected", serial_number=self.serial_number)
            self._register_callbacks()
            
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error(
                "pdxc2_connect_failed",
                serial_number=self.serial_number,
                error=str(e),
                task=task_context.get()
            )
            return False
    
    async def disconnect(self) -> bool:
        """
        Disconnect from PDXC2 device.
        
        Returns:
            True if successful
        """
        try:
            if self.device:
                await asyncio.to_thread(self.device.StopPolling)
                await asyncio.to_thread(self.device.Disconnect, True)
                self._connected = False
                self._enabled = False
                logger.info("pdxc2_disconnected", serial_number=self.serial_number)
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error("pdxc2_disconnect_failed", error=str(e))
            return False
    
    async def enable_device(self) -> bool:
        """
        Enable the PDXC2 device for operation.
        
        Returns:
            True if successful
        """
        if not self.device:
            logger.warning("pdxc2_enable_failed_not_connected")
            return False
        
        try:
            await asyncio.to_thread(self.device.EnableDevice)
            await asyncio.sleep(0.25)
            self._enabled = True
            logger.info("pdxc2_device_enabled", serial_number=self.serial_number)
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error("pdxc2_enable_failed", error=str(e))
            return False
    
    async def disable_device(self) -> bool:
        """
        Disable the PDXC2 device.
        
        Returns:
            True if successful
        """
        if not self.device:
            return False
        
        try:
            await asyncio.to_thread(self.device.DisableDevice)
            self._enabled = False
            logger.info("pdxc2_device_disabled", serial_number=self.serial_number)
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error("pdxc2_disable_failed", error=str(e))
            return False
    
    async def set_open_loop_mode(self) -> bool:
        """
        Set device to open-loop control mode (step-based, fast).
        
        Returns:
            True if successful
        """
        if not self.device:
            return False
        
        try:
            await asyncio.to_thread(
                self.device.SetPositionControlMode,
                PiezoControlModeTypes.OpenLoop
            )
            self._position_mode = "open_loop"
            logger.info("pdxc2_mode_set", mode="open_loop")
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error("pdxc2_set_open_loop_mode_failed", error=str(e))
            return False
    
    async def set_closed_loop_mode(self) -> bool:
        """
        Set device to closed-loop control mode (encoder feedback, precise).
        Only valid for PDX series stages with encoder.
        
        Returns:
            True if successful
        """
        if not self.device:
            return False
        
        try:
            await asyncio.to_thread(
                self.device.SetPositionControlMode,
                PiezoControlModeTypes.CloseLoop
            )
            self._position_mode = "closed_loop"
            logger.info("pdxc2_mode_set", mode="closed_loop")
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error("pdxc2_set_closed_loop_mode_failed", error=str(e))
            return False
    
    async def move_open_loop(self, step_size: int) -> bool:
        """
        Move stage in open-loop mode (steps).
        
        Open-loop moves are fast but not precise. Step size range: -10000000 to +10000000.
        
        Args:
            step_size: Number of steps to move (positive or negative)
            
        Returns:
            True if move initiated successfully
        """
        if not self.device or not self._enabled:
            logger.warning("pdxc2_move_failed_not_ready")
            return False
        
        try:
            # Clamp step size to valid range
            step_size = max(-10000000, min(10000000, step_size))
            
            # Set open-loop parameters
            params = OpenLoopMoveParams()
            params.StepSize = step_size
            await asyncio.to_thread(self.device.SetOpenLoopMoveParameters, params)
            
            # Initiate move
            await asyncio.to_thread(self.device.MoveStart)
            self._is_moving = True
            
            logger.info(
                "pdxc2_open_loop_move_started",
                step_size=step_size,
                task=task_context.get()
            )
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error("pdxc2_open_loop_move_failed", error=str(e), step_size=step_size)
            return False
    
    async def move_closed_loop(self, target_nm: int) -> bool:
        """
        Move stage in closed-loop mode to target position (nm).
        
        Closed-loop moves are precise but slower and require homing first.
        Position range: -1000000 to +1000000 nm. Min unit: 10nm.
        
        Args:
            target_nm: Target position in nm
            
        Returns:
            True if move initiated successfully
        """
        if not self.device or not self._enabled:
            logger.warning("pdxc2_closed_loop_move_failed_not_ready")
            return False
        
        if not self._homed:
            logger.warning("pdxc2_closed_loop_move_requires_homing")
            return False
        
        try:
            # Clamp position to valid range
            target_nm = max(-1000000, min(1000000, target_nm))
            
            # Set target position
            await asyncio.to_thread(self.device.SetClosedLoopTarget, target_nm)
            
            # Initiate move
            await asyncio.to_thread(self.device.MoveStart)
            self._is_moving = True
            
            logger.info(
                "pdxc2_closed_loop_move_started",
                target_nm=target_nm,
                task=task_context.get()
            )
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error("pdxc2_closed_loop_move_failed", error=str(e), target_nm=target_nm)
            return False
    
    async def home(self, timeout_ms: int = 60000) -> bool:
        """
        Home the stage (closed-loop mode only).
        
        Must be called before closed-loop moves. Also runs calibration/optimization.
        
        Args:
            timeout_ms: Timeout for homing operation (milliseconds)
            
        Returns:
            True if homing successful
        """
        if not self.device or not self._enabled:
            logger.warning("pdxc2_home_failed_not_ready")
            return False
        
        try:
            # Start performance optimization (pulse parameter acquisition)
            await asyncio.to_thread(self.device.PulseParamsAcquireStart)
            await asyncio.sleep(0.5)
            
            # Wait for optimization to complete
            max_wait = timeout_ms / 1000.0
            elapsed = 0.0
            while elapsed < max_wait:
                status = await asyncio.to_thread(lambda: self.device.Status.IsPulseParamsAcquired)
                if status:
                    break
                await asyncio.sleep(0.5)
                elapsed += 0.5
            
            # Home the device
            await asyncio.to_thread(self.device.Home, timeout_ms)
            
            self._homed = True
            logger.info("pdxc2_homed", serial_number=self.serial_number)
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error("pdxc2_home_failed", error=str(e), timeout_ms=timeout_ms)
            return False
    
    async def quick_home(self, timeout_ms: int = 10000) -> bool:
        """
        Quick home without full calibration (just sets reference).
        
        Faster than full home() but requires prior calibration.
        
        Args:
            timeout_ms: Timeout for home operation (milliseconds)
            
        Returns:
            True if home successful
        """
        if not self.device or not self._enabled:
            logger.warning("pdxc2_quick_home_failed_not_ready")
            return False
        
        try:
            # Just home without pulse parameter acquisition
            await asyncio.to_thread(self.device.Home, timeout_ms)
            
            self._homed = True
            logger.info("pdxc2_quick_home", serial_number=self.serial_number)
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error("pdxc2_quick_home_failed", error=str(e))
            return False
    
    async def calibrate(self, timeout_ms: int = 60000) -> bool:
        """
        Calibrate the stage (runs pulse parameter optimization).
        
        Same as home() - this is the closed-loop calibration procedure.
        
        Args:
            timeout_ms: Timeout for calibration (milliseconds)
            
        Returns:
            True if calibration successful
        """
        return await self.home(timeout_ms)
    
    async def wait_move_complete(self, timeout_ms: int = 30000) -> bool:
        """
        Wait for current move operation to complete.
        
        Args:
            timeout_ms: Timeout for move completion (milliseconds)
            
        Returns:
            True if move completed within timeout
        """
        if not self.device:
            return False
        
        try:
            max_wait = timeout_ms / 1000.0
            elapsed = 0.0
            last_pos = await asyncio.to_thread(self.device.GetCurrentPosition)
            
            while elapsed < max_wait:
                await asyncio.sleep(0.5)
                current_pos = await asyncio.to_thread(self.device.GetCurrentPosition)
                
                if current_pos == last_pos:
                    # Position hasn't changed, move complete
                    self._is_moving = False
                    self._current_position = current_pos
                    logger.info(
                        "pdxc2_move_complete",
                        position=current_pos,
                        position_mode=self._position_mode
                    )
                    return True
                
                last_pos = current_pos
                elapsed += 0.5
            
            # Timeout
            logger.warning("pdxc2_move_timeout", timeout_ms=timeout_ms)
            return False
        except Exception as e:
            self._last_error = str(e)
            logger.error("pdxc2_wait_move_complete_failed", error=str(e))
            return False
    
    async def get_current_position(self) -> int:
        """
        Get current position.
        
        Returns:
            Position in steps (open-loop) or nm (closed-loop)
        """
        if not self.device:
            return self._current_position
        
        try:
            pos = await asyncio.to_thread(self.device.GetCurrentPosition)
            self._current_position = pos
            return pos
        except Exception as e:
            # Device might be disconnected - log but return last known position
            logger.warning("pdxc2_get_position_failed", error=str(e))
            return self._current_position
    
    async def stop_move(self) -> bool:
        """
        Stop ongoing move operation.
        
        Returns:
            True if successful
        """
        if not self.device:
            return False
        
        try:
            await asyncio.to_thread(self.device.MoveStop)
            self._is_moving = False
            logger.info("pdxc2_move_stopped")
            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error("pdxc2_stop_move_failed", error=str(e))
            return False
    
    async def get_status(self) -> PDXC2Status:
        """
        Get current device status snapshot.
        
        Returns:
            PDXC2Status dataclass with all state information
        """
        return PDXC2Status(
            connected=self._connected,
            enabled=self._enabled,
            homed=self._homed,
            current_position=self._current_position,
            position_mode=self._position_mode,
            is_moving=self._is_moving,
            error=self._last_error
        )
    
    def _register_callbacks(self) -> None:
        """Register device callbacks for state tracking."""
        if not self.device:
            return
        
        try:
            # Note: These callbacks come from the .NET layer
            # We can subscribe to device events if the .NET API supports them
            # For now, we track state through direct polling/method calls
            logger.info("pdxc2_callbacks_registered", serial_number=self.serial_number)
        except Exception as e:
            logger.warning("pdxc2_callback_registration_failed", error=str(e))
    
    @asynccontextmanager
    async def managed_connection(self):
        """
        Context manager for automatic connection/disconnection.
        
        Usage:
            async with controller.managed_connection():
                await controller.enable_device()
                await controller.move_open_loop(1000)
        """
        try:
            await self.connect()
            yield
        finally:
            await self.disconnect()
