from __future__ import annotations

import asyncio
import logging
from typing import Optional, Tuple

import mecademicpy.robot as mdr

logger = logging.getLogger(__name__)


class Meca500Controller:
    """
    High-level async wrapper around mecademicpy Robot class for Meca500.
    
    Follows best practices from mecademicpy README:
    - Uses asynchronous mode by default (non-blocking)
    - Provides callbacks for state changes
    - Implements proper error handling and recovery
    - Manages connection lifecycle
    """

    def __init__(self, address: str = "192.168.0.100", enable_callbacks: bool = True):
        self.address = address
        self.robot = mdr.Robot()
        self.enable_callbacks = enable_callbacks
        self._connected = False
        self._activated = False
        self._homed = False
        self._error_state = False

    async def connect(self) -> bool:
        """Connect to the Meca500 robot."""
        try:
            # Connect is synchronous even in async mode
            await asyncio.to_thread(self.robot.Connect, address=self.address)
            self._connected = True
            logger.info("meca500_connected", address=self.address)

            if self.enable_callbacks:
                await self._register_callbacks()

            return True
        except Exception as e:
            logger.error("meca500_connect_failed", error=str(e), address=self.address)
            return False

    async def disconnect(self) -> None:
        """Disconnect from the Meca500 robot."""
        try:
            await asyncio.to_thread(self.robot.Disconnect)
            self._connected = False
            self._activated = False
            self._homed = False
            logger.info("meca500_disconnected")
        except Exception as e:
            logger.error("meca500_disconnect_failed", error=str(e))

    async def activate_and_home(self) -> bool:
        """
        Activate the robot and perform homing if necessary.
        
        This follows the mecademicpy recommendation to use ActivateAndHome()
        which is more efficient than separate calls.
        """
        try:
            await asyncio.to_thread(self.robot.ActivateAndHome)
            # Wait for activation to complete
            await asyncio.to_thread(self.robot.WaitActivated, timeout=10)
            self._activated = True
            # Wait for homing to complete
            await asyncio.to_thread(self.robot.WaitHomed, timeout=10)
            self._homed = True
            logger.info("meca500_activated_and_homed")
            return True
        except Exception as e:
            logger.error("meca500_activate_home_failed", error=str(e))
            return False

    async def deactivate(self) -> bool:
        """Deactivate the robot."""
        try:
            await asyncio.to_thread(self.robot.DeactivateRobot)
            await asyncio.to_thread(self.robot.WaitDeactivated, timeout=5)
            self._activated = False
            self._homed = False
            logger.info("meca500_deactivated")
            return True
        except Exception as e:
            logger.error("meca500_deactivate_failed", error=str(e))
            return False

    async def home(self) -> bool:
        """Perform homing sequence."""
        try:
            await asyncio.to_thread(self.robot.Home)
            await asyncio.to_thread(self.robot.WaitHomed, timeout=10)
            self._homed = True
            logger.info("meca500_homed")
            return True
        except Exception as e:
            logger.error("meca500_home_failed", error=str(e))
            return False

    async def move_joints(self, j1: float, j2: float, j3: float, j4: float, j5: float, j6: float) -> bool:
        """Move to specified joint angles (degrees)."""
        try:
            await asyncio.to_thread(self.robot.MoveJoints, j1, j2, j3, j4, j5, j6)
            logger.debug("meca500_move_joints_sent", joints=[j1, j2, j3, j4, j5, j6])
            return True
        except Exception as e:
            logger.error("meca500_move_joints_failed", error=str(e), joints=[j1, j2, j3, j4, j5, j6])
            return False

    async def zero_all_joints(self) -> bool:
        """Move all joints to zero position (home configuration)."""
        return await self.move_joints(0, 0, 0, 0, 0, 0)

    async def get_joints(self) -> Optional[Tuple[float, float, float, float, float, float]]:
        """Get current joint positions."""
        try:
            joints = await asyncio.to_thread(self.robot.GetJoints)
            logger.debug("meca500_joints_read", joints=joints)
            return tuple(joints) if joints else None
        except Exception as e:
            logger.error("meca500_get_joints_failed", error=str(e))
            return None

    async def get_pose(self) -> Optional[dict]:
        """Get current Cartesian pose (position + orientation)."""
        try:
            pose = await asyncio.to_thread(self.robot.GetPose)
            if pose:
                return {
                    "x": pose[0],
                    "y": pose[1],
                    "z": pose[2],
                    "alpha": pose[3],
                    "beta": pose[4],
                    "gamma": pose[5],
                }
            return None
        except Exception as e:
            logger.error("meca500_get_pose_failed", error=str(e))
            return None

    async def get_status(self) -> Optional[dict]:
        """Get robot status (connection, activation, error state, etc.)."""
        try:
            status = await asyncio.to_thread(self.robot.GetStatusRobot)
            return {
                "connected": self._connected,
                "activated": self._activated,
                "homed": self._homed,
                "is_moving": status.motion_status if status else False,
                "error": status.error_status if status else False,
                "paused": status.pause_motion_status if status else False,
            }
        except Exception as e:
            logger.error("meca500_get_status_failed", error=str(e))
            return None

    async def reset_error(self) -> bool:
        """Reset robot error state."""
        try:
            await asyncio.to_thread(self.robot.ResetError)
            self._error_state = False
            logger.info("meca500_error_reset")
            return True
        except Exception as e:
            logger.error("meca500_reset_error_failed", error=str(e))
            return False

    async def wait_idle(self, timeout: float = 30.0) -> bool:
        """Wait for robot to complete all motions."""
        try:
            await asyncio.to_thread(self.robot.WaitIdle, timeout=timeout)
            logger.debug("meca500_wait_idle_complete")
            return True
        except asyncio.TimeoutError:
            logger.warning("meca500_wait_idle_timeout", timeout=timeout)
            return False
        except Exception as e:
            logger.error("meca500_wait_idle_failed", error=str(e))
            return False

    async def clear_motion(self) -> bool:
        """Clear the motion queue immediately."""
        try:
            await asyncio.to_thread(self.robot.ClearMotion)
            logger.warning("meca500_motion_cleared")
            return True
        except Exception as e:
            logger.error("meca500_clear_motion_failed", error=str(e))
            return False

    async def pause_motion(self) -> bool:
        """Pause ongoing motion."""
        try:
            await asyncio.to_thread(self.robot.PauseMotion)
            logger.info("meca500_motion_paused")
            return True
        except Exception as e:
            logger.error("meca500_pause_motion_failed", error=str(e))
            return False

    async def resume_motion(self) -> bool:
        """Resume paused motion."""
        try:
            await asyncio.to_thread(self.robot.ResumeMotion)
            logger.info("meca500_motion_resumed")
            return True
        except Exception as e:
            logger.error("meca500_resume_motion_failed", error=str(e))
            return False

    async def send_command(self, command: str) -> Optional[str]:
        """
        Send a raw command string to the robot.
        
        This is for advanced usage or testing; prefer specific methods when available.
        """
        try:
            response = await asyncio.to_thread(self.robot.SendCustomCommand, command)
            logger.debug("meca500_custom_command", command=command, response=str(response))
            return str(response) if response else "OK"
        except Exception as e:
            logger.error("meca500_custom_command_failed", command=command, error=str(e))
            return None

    async def set_valve(self, bank: int, pin: int, state: bool) -> bool:
        """
        Control pneumatic valve (GPIO output).
        
        Args:
            bank: GPIO bank number (1-3)
            pin: GPIO pin number (1-16)
            state: True for open/on, False for close/off
        
        Returns:
            True if command successful
        """
        try:
            # SetIO(bank, pin, state)
            await asyncio.to_thread(self.robot.SetIO, bank, pin, state)
            logger.info("meca500_valve_set", bank=bank, pin=pin, state=state)
            return True
        except Exception as e:
            logger.error("meca500_valve_set_failed", bank=bank, pin=pin, state=state, error=str(e))
            return False

    async def get_valve_state(self, bank: int, pin: int) -> Optional[bool]:
        """
        Read pneumatic valve state (GPIO input/output).
        
        Args:
            bank: GPIO bank number (1-3)
            pin: GPIO pin number (1-16)
        
        Returns:
            True if open/on, False if closed/off, None on error
        """
        try:
            # GetIO(bank, pin) returns the state
            state = await asyncio.to_thread(self.robot.GetIO, bank, pin)
            logger.debug("meca500_valve_state_read", bank=bank, pin=pin, state=state)
            return bool(state)
        except Exception as e:
            logger.error("meca500_valve_state_failed", bank=bank, pin=pin, error=str(e))
            return None

    async def _register_callbacks(self) -> None:
        """Register callback handlers for robot state changes."""
        callbacks = mdr.RobotCallbacks()

        def on_connected():
            logger.info("meca500_callback_connected")
            self._connected = True

        def on_disconnected():
            logger.info("meca500_callback_disconnected")
            self._connected = False
            self._activated = False
            self._homed = False

        def on_activated():
            logger.info("meca500_callback_activated")
            self._activated = True

        def on_deactivated():
            logger.info("meca500_callback_deactivated")
            self._activated = False
            self._homed = False

        def on_homed():
            logger.info("meca500_callback_homed")
            self._homed = True

        def on_error():
            logger.error("meca500_callback_error")
            self._error_state = True

        callbacks.on_connected = on_connected
        callbacks.on_disconnected = on_disconnected
        callbacks.on_activated = on_activated
        callbacks.on_deactivated = on_deactivated
        callbacks.on_homed = on_homed
        callbacks.on_error = on_error

        await asyncio.to_thread(
            self.robot.RegisterCallbacks,
            callbacks=callbacks,
            run_callbacks_in_separate_thread=True,
        )

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup."""
        if self._activated:
            await self.deactivate()
        await self.disconnect()
