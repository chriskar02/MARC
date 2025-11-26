from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..core.config import Settings, get_settings
from ..core.network import get_ipv4_adapters
from ..services.hardware.meca500 import Meca500Controller
from ..services.hardware.pdxc2 import PDXC2Controller

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/commands", tags=["commands"])

# Singleton instances; in production, use dependency injection or app state
_meca500_controller: Optional[Meca500Controller] = None
_pdxc2_controller: Optional[PDXC2Controller] = None


async def get_meca500(settings: Settings = Depends(get_settings)) -> Meca500Controller:
    """Dependency to get or create the Meca500 controller."""
    global _meca500_controller
    if _meca500_controller is None:
        # Default IP; override via settings if needed
        meca_ip = getattr(settings, "meca500_address", "192.168.0.100")
        _meca500_controller = Meca500Controller(address=meca_ip)
    return _meca500_controller


async def get_pdxc2(settings: Settings = Depends(get_settings)) -> PDXC2Controller:
    """Dependency to get or create the PDXC2 controller."""
    global _pdxc2_controller
    if _pdxc2_controller is None:
        # Default serial number; override via settings if needed
        serial = getattr(settings, "pdxc2_serial", "112000001")
        # Set DLL path if configured
        dll_path = getattr(settings, "kinesis_dll_path", None)
        if dll_path:
            from ..services.hardware.pdxc2 import set_kinesis_dll_path
            set_kinesis_dll_path(dll_path)
        _pdxc2_controller = PDXC2Controller(serial_number=serial)
    return _pdxc2_controller


class MotorCommand(BaseModel):
    command: str
    axis: str = ""
    value: float = 0.0


class RobotCommand(BaseModel):
    command: str


class DeviceCommand(BaseModel):
    command: str
    port: str = ""
    
    model_config = {"extra": "allow"}  # Allow additional fields


@router.post("/motors/xy")
async def xy_motor_command(cmd: MotorCommand):
    """Handle XY stage motor commands."""
    # TODO: Integrate with actual motor controller
    if cmd.command == "move":
        return {"x_position": cmd.value if cmd.axis == "x" else 0, "y_position": cmd.value if cmd.axis == "y" else 0}
    elif cmd.command == "home":
        return {"x_position": 0.0, "y_position": 0.0}
    elif cmd.command == "stop":
        return {"status": "stopped"}
    raise HTTPException(status_code=400, detail=f"Unknown motor command: {cmd.command}")


@router.post("/robot")
async def robot_command(cmd: RobotCommand):
    """Handle Meca500 robot commands."""
    # TODO: Integrate with mecademicpy
    return {"robot": f"Executed: {cmd.command}"}


@router.get("/network/adapters")
async def get_network_adapters():
    """List all available network adapters with calculated Meca500 addresses."""
    adapters = get_ipv4_adapters()
    return {
        "adapters": [adapter.to_dict() for adapter in adapters],
        "count": len(adapters),
    }


@router.post("/network/meca-address")
async def get_meca_address(adapter_name: str, ip: str, netmask: str = "255.255.255.0"):
    """Get the recommended Meca500 address for a specific adapter."""
    from ..core.network import _calculate_meca_address, validate_meca_address
    
    meca_addr = _calculate_meca_address(ip, netmask)
    is_valid = validate_meca_address(meca_addr, ip, netmask)
    
    return {
        "adapter": adapter_name,
        "local_ip": ip,
        "netmask": netmask,
        "meca_address": meca_addr,
        "is_valid": is_valid,
    }


@router.post("/pdxc2")
async def pdxc2_command(cmd: RobotCommand):
    """Handle PDXC2 piezo controller commands."""
    # TODO: Integrate with PDXC2_Control module
    return {"pdxc2": f"Executed: {cmd.command}"}


@router.post("/device")
async def device_control(
    cmd: DeviceCommand,
    meca500: Meca500Controller = Depends(get_meca500),
    pdxc2: PDXC2Controller = Depends(get_pdxc2),
):
    """Handle device-level control commands (activate, calibrate, etc.)."""
    # === Meca500 Commands ===
    if "meca500_activate" in cmd.command:
        # Allow overriding address from command payload
        if hasattr(cmd, "address"):
            meca500.address = cmd.address
        success = await meca500.activate_and_home()
        status = await meca500.get_status()
        return {"connected": meca500._connected, "enabled": meca500._activated, **status} if success else {"error": "Activation failed"}
    
    elif "meca500_deactivate" in cmd.command:
        success = await meca500.deactivate()
        return {"connected": meca500._connected, "enabled": False} if success else {"error": "Deactivation failed"}
    
    elif "meca500_zero_joints" in cmd.command:
        success = await meca500.zero_all_joints()
        joints = await meca500.get_joints()
        return {"status": "joints_zeroed", "joints": joints} if success else {"error": "Zero joints failed"}
    
    elif "meca500_valve_open" in cmd.command:
        bank = getattr(cmd, "bank", 1)
        pin = getattr(cmd, "pin", 1)
        success = await meca500.set_valve(bank, pin, True)
        return {"valve_state": True, "bank": bank, "pin": pin} if success else {"error": "Valve open failed"}
    
    elif "meca500_valve_close" in cmd.command:
        bank = getattr(cmd, "bank", 1)
        pin = getattr(cmd, "pin", 1)
        success = await meca500.set_valve(bank, pin, False)
        return {"valve_state": False, "bank": bank, "pin": pin} if success else {"error": "Valve close failed"}
    
    elif "meca500_connect" in cmd.command:
        # Allow overriding address from command payload
        if hasattr(cmd, "address"):
            meca500.address = cmd.address
        success = await meca500.connect()
        return {"connected": True} if success else {"error": "Connection failed"}
    
    elif "meca500_disconnect" in cmd.command:
        await meca500.disconnect()
        return {"connected": False}
    
    # === PDXC2 Commands ===
    elif "pdxc2_connect" in cmd.command:
        success = await pdxc2.connect()
        status = await pdxc2.get_status()
        return {"connected": success, **status.__dict__} if success else {"error": "Connection failed"}
    
    elif "pdxc2_disconnect" in cmd.command:
        success = await pdxc2.disconnect()
        return {"connected": False} if success else {"error": "Disconnection failed"}
    
    elif "pdxc2_enable" in cmd.command:
        success = await pdxc2.enable_device()
        status = await pdxc2.get_status()
        return {"enabled": success, **status.__dict__} if success else {"error": "Enable failed"}
    
    elif "pdxc2_disable" in cmd.command:
        success = await pdxc2.disable_device()
        status = await pdxc2.get_status()
        return {"enabled": False, **status.__dict__} if success else {"error": "Disable failed"}
    
    elif "pdxc2_calibrate" in cmd.command:
        # Connect if not already connected
        if not pdxc2._connected:
            await pdxc2.connect()
        # Enable if not already enabled
        if not pdxc2._enabled:
            await pdxc2.enable_device()
        # Run full calibration with pulse parameter acquisition
        success = await pdxc2.calibrate(timeout_ms=60000)
        status = await pdxc2.get_status()
        return {"calibrated": success, **status.__dict__} if success else {"error": "Calibration failed"}
    
    elif "pdxc2_home" in cmd.command:
        # Connect if not already connected
        if not pdxc2._connected:
            await pdxc2.connect()
        # Enable if not already enabled
        if not pdxc2._enabled:
            await pdxc2.enable_device()
        # Run quick home (without full calibration)
        success = await pdxc2.quick_home(timeout_ms=10000)
        status = await pdxc2.get_status()
        return {"homed": success, **status.__dict__} if success else {"error": "Home failed"}
    
    elif "pdxc2_set_open_loop" in cmd.command:
        success = await pdxc2.set_open_loop_mode()
        status = await pdxc2.get_status()
        return {"mode": "open_loop", **status.__dict__} if success else {"error": "Mode change failed"}
    
    elif "pdxc2_set_closed_loop" in cmd.command:
        success = await pdxc2.set_closed_loop_mode()
        status = await pdxc2.get_status()
        return {"mode": "closed_loop", **status.__dict__} if success else {"error": "Mode change failed"}
    
    elif "pdxc2_move_open_loop" in cmd.command:
        step_size = getattr(cmd, "step_size", 1)
        success = await pdxc2.move_open_loop(step_size)
        status = await pdxc2.get_status()
        return {"moved": success, **status.__dict__} if success else {"error": "Move failed"}
    
    elif "pdxc2_move_closed_loop" in cmd.command:
        position = getattr(cmd, "position", 0)
        success = await pdxc2.move_closed_loop(position)
        status = await pdxc2.get_status()
        return {"moved": success, **status.__dict__} if success else {"error": "Move failed"}
    
    # === Bota Commands ===
    elif "bota_tare" in cmd.command:
        # TODO: Implement Bota tare
        return {"connected": True, "tared": True}
    
    # === XY Motor Commands ===
    elif "xy_motors_connect" in cmd.command:
        # TODO: Implement XY motor connection
        return {"connected": True}
    
    elif "xy_motors_disconnect" in cmd.command:
        # TODO: Implement XY motor disconnection
        return {"connected": False}
    
    raise HTTPException(status_code=400, detail=f"Unknown device command: {cmd.command}")


@router.post("/safety/emergency-stop")
async def emergency_stop():
    """Immediately halt all motors and disable robot."""
    # TODO: Call safety service to fan out to all devices
    return {"status": "emergency_stop_activated", "timestamp": 0}
