"""Quick Meca500 connection test with safety reset."""
import mecademicpy.robot as mdr
import time

r = mdr.Robot()
print("Connecting to 192.168.0.100...")
try:
    r.Connect(address="192.168.0.100", timeout=5, disconnect_on_exception=False)
    print("Connected!")
    status = r.GetStatusRobot()
    print(f"Status: activated={status.activation_state}, homed={status.homing_state}, error={status.error_status}")
    
    # Check safety status
    safety = r.GetSafetyStatus()
    print(f"Safety status: {safety}")
    for attr in dir(safety):
        if not attr.startswith('_'):
            print(f"  safety.{attr} = {getattr(safety, attr)}")
    
    # Reset any errors
    print("Resetting errors...")
    r.ResetError()
    time.sleep(1)
    
    # Try ResetPStop (general safety stop reset - for reboot condition)
    print("Trying ResetPStop...")
    try:
        r.ResetPStop()
        time.sleep(2)
        print("  ResetPStop OK")
    except Exception as e:
        print(f"  ResetPStop result: {e}")
    
    # Also try ResetPStop2
    print("Trying ResetPStop2...")
    try:
        r.ResetPStop2()
        time.sleep(1)
        print("  ResetPStop2 OK")
    except Exception as e:
        print(f"  ResetPStop2 result: {e}")
    
    # Check safety again
    safety2 = r.GetSafetyStatus()
    print(f"Safety after resets: reset_ready={safety2.reset_ready}, stop_mask={safety2.stop_mask}, reboot={safety2.reboot_stop_state}")
    
    # Try raw commands for safety reset
    for cmd_name in ["ResetSafetyStop", "ResetSafetyStopReboot", "ClearSafetyConditions"]:
        print(f"Trying SendCustomCommand('{cmd_name}')...")
        try:
            r.SendCustomCommand(cmd_name)
            time.sleep(1)
            s = r.GetSafetyStatus()
            print(f"  After: stop_mask={s.stop_mask}, reboot={s.reboot_stop_state}")
            if s.stop_mask == 0:
                print("  SUCCESS - safety cleared!")
                break
        except Exception as e:
            print(f"  Error: {e}")
    
    # Clear motion
    r.ClearMotion()
    time.sleep(0.5)
    
    try:
        r.ResumeMotion()
    except:
        pass
    
    status = r.GetStatusRobot()
    print(f"Status after reset: activated={status.activation_state}, homed={status.homing_state}, error={status.error_status}")
    
    # Try activate
    print("Activating and homing...")
    r.ActivateAndHome()
    r.WaitActivated(timeout=30)
    print("Activated!")
    r.WaitHomed(timeout=30)
    print("Homed!")
    
    pose = r.GetPose()
    print(f"Current pose: {pose}")
    
    r.Disconnect()
    print("Disconnected.")
except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()
    try:
        r.Disconnect()
    except:
        pass
