from __future__ import annotations

import structlog
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..core.config import Settings, get_settings
from ..core.network import get_ipv4_adapters
from ..services.hardware.meca500 import Meca500Controller

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/commands", tags=["commands"])

# Singleton instances; in production, use dependency injection or app state
_meca500_controller: Optional[Meca500Controller] = None


async def get_meca500(settings: Settings = Depends(get_settings)) -> Meca500Controller:
    """Dependency to get or create the Meca500 controller."""
    global _meca500_controller
    if _meca500_controller is None:
        meca_ip = getattr(settings, "meca500_address", "192.168.0.100")
        try:
            _meca500_controller = Meca500Controller(address=meca_ip)
        except Exception as e:
            logger.error("meca500_init_failed", error=str(e))
            raise HTTPException(status_code=503, detail=f"Meca500 init failed: {e}")
    return _meca500_controller




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
    """Handle Standa XY/XYZ stage motor commands (via libximc)."""
    # TODO: Integrate with Standa ximc library
    if cmd.command == "move":
        return {"axis": cmd.axis, "position": cmd.value, "status": "moved"}
    elif cmd.command == "home":
        return {"x_position": 0.0, "y_position": 0.0, "z_position": 0.0, "status": "homed"}
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


@router.post("/device")
async def device_control(
    cmd: DeviceCommand,
    meca500: Meca500Controller = Depends(get_meca500),
):
    """Handle device-level control commands (activate, calibrate, etc.)."""
    try:
        return await _device_control_inner(cmd, meca500)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("device_control_unhandled", error=str(e), command=cmd.command)
        return {"error": str(e), "command": cmd.command}


async def _device_control_inner(cmd: DeviceCommand, meca500: Meca500Controller):
    """Inner device control logic."""
    # === Meca500 Commands ===
    if "meca500_activate" in cmd.command:
        # Allow overriding address from command payload
        if hasattr(cmd, "address"):
            meca500.address = cmd.address
        result = await meca500.activate_and_home()
        if result.get("success"):
            status = await meca500.get_status()
            return {"connected": meca500._connected, "enabled": meca500._activated, **(status or {})}
        else:
            return {"error": result.get("error", "Activation failed"), **{k: v for k, v in result.items() if k != "success"}}
    
    elif "meca500_deactivate" in cmd.command:
        success = await meca500.deactivate()
        return {"connected": meca500._connected, "enabled": False} if success else {"error": "Deactivation failed"}
    
    elif "meca500_zero_joints" in cmd.command:
        success = await meca500.zero_all_joints()
        joints = await meca500.get_joints()
        return {"status": "joints_zeroed", "joints": joints} if success else {"error": "Zero joints failed"}
    elif "meca500_move_joints" in cmd.command:
        # Expecting `angles` list in payload
        angles = getattr(cmd, "angles", None)
        if not angles or len(angles) != 6:
            return {"error": "Invalid angles payload"}
        success = await meca500.move_joints(*angles)
        joints = await meca500.get_joints()
        return {"moved": success, "joints": joints} if success else {"error": "Move joints failed"}

    elif "meca500_move_shipping" in cmd.command:
        success = await meca500.move_to_shipping()
        status = await meca500.get_status()
        return {"moved": success, **status} if success else {"error": "Move to shipping failed"}

    elif "meca500_move_tool_delta" in cmd.command:
        # Expecting dx, dy, dz and optional targetOrientation
        dx = getattr(cmd, "dx", 0)
        dy = getattr(cmd, "dy", 0)
        dz = getattr(cmd, "dz", 0)
        target_orientation = getattr(cmd, "targetOrientation", None)
        success = await meca500.move_tool_delta(float(dx), float(dy), float(dz), target_orientation)
        status = await meca500.get_status()
        return {"moved": success, **status} if success else {"error": "Tool delta move failed"}

    elif "meca500_move_pose" in cmd.command:
        # Move to absolute Cartesian XYZ position (keeps orientation from optional params or current)
        x = float(getattr(cmd, "x", 0))
        y = float(getattr(cmd, "y", 0))
        z = float(getattr(cmd, "z", 0))
        alpha = getattr(cmd, "alpha", None)
        beta = getattr(cmd, "beta", None)
        gamma = getattr(cmd, "gamma", None)
        # Fill orientation from current pose if not provided
        if alpha is None or beta is None or gamma is None:
            current = await meca500.get_pose()
            if current:
                alpha = float(alpha) if alpha is not None else current.get("alpha", 0)
                beta = float(beta) if beta is not None else current.get("beta", 0)
                gamma = float(gamma) if gamma is not None else current.get("gamma", 0)
            else:
                alpha = float(alpha or 0)
                beta = float(beta or 0)
                gamma = float(gamma or 0)
        success = await meca500.move_to_pose(x, y, z, float(alpha), float(beta), float(gamma))
        pose = await meca500.get_pose()
        return {"moved": success, "pose": pose} if success else {"error": "Move pose failed"}

    elif "meca500_get_pose" in cmd.command:
        try:
            if not meca500._connected:
                return {"pose": None, "joints": None, "connected": False}
            pose = await meca500.get_pose()
            joints = await meca500.get_joints()
            status = await meca500.get_status()
            return {"pose": pose, "joints": list(joints) if joints else None, "connected": True, **(status or {})}
        except Exception as e:
            logger.error("meca500_get_pose_endpoint_failed", error=str(e))
            return {"pose": None, "joints": None, "connected": meca500._connected, "error": str(e)}

    elif "meca500_move_xyz_delta" in cmd.command:
        # Relative XYZ delta move in Cartesian space, preserving orientation
        dx = float(getattr(cmd, "dx", 0))
        dy = float(getattr(cmd, "dy", 0))
        dz = float(getattr(cmd, "dz", 0))
        success = await meca500.move_tool_delta(dx, dy, dz)
        pose = await meca500.get_pose()
        return {"moved": success, "pose": pose} if success else {"error": "XYZ delta move failed"}
    
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
    
    # === Bota Commands ===
    elif "bota_tare" in cmd.command:
        # TODO: Implement Bota tare
        return {"connected": True, "tared": True}
    
    # === Standa Stage Motor Commands ===
    elif "standa_connect" in cmd.command:
        # TODO: Implement Standa ximc connection
        port = getattr(cmd, "port", "")
        return {"connected": True, "port": port}
    
    elif "standa_disconnect" in cmd.command:
        # TODO: Implement Standa ximc disconnection
        return {"connected": False}
    
    elif "standa_home" in cmd.command:
        # TODO: Implement Standa homing
        return {"status": "homed", "x": 0, "y": 0, "z": 0}

    elif "standa_move" in cmd.command:
        axis = getattr(cmd, "axis", "x")
        value = float(getattr(cmd, "value", 0))
        return {"axis": axis, "position": value, "status": "moved"}

    elif "standa_stop" in cmd.command:
        return {"status": "stopped"}
    
    raise HTTPException(status_code=400, detail=f"Unknown device command: {cmd.command}")


@router.post("/safety/emergency-stop")
async def emergency_stop():
    """Immediately halt all motors and disable robot."""
    # TODO: Call safety service to fan out to all devices
    return {"status": "emergency_stop_activated", "timestamp": 0}
