"""
PDXC2 Device Discovery - Find connected devices

This script helps identify what PDXC2 devices are connected to your system.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import clr
    dll_path = r"C:\Program Files\Thorlabs\Kinesis"
    
    clr.AddReference(f"{dll_path}\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
    clr.AddReference(f"{dll_path}\\Thorlabs.MotionControl.Benchtop.PiezoCLI.dll")
    
    from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI, SimulationManager
    
    print("=" * 60)
    print("PDXC2 Device Discovery")
    print("=" * 60)
    
    # Build device list
    print("\nScanning for connected devices...")
    DeviceManagerCLI.BuildDeviceList()
    
    # Get list of PDXC2 devices
    device_list = DeviceManagerCLI.GetDeviceList(4)  # 4 = Benchtop Piezo (PDXC2)
    
    print(f"\nFound {device_list.Count} PDXC2 device(s):\n")
    
    if device_list.Count == 0:
        print("❌ No PDXC2 devices found!")
        print("\nTroubleshooting:")
        print("1. Check USB cable is connected")
        print("2. Power cycle the PDXC2")
        print("3. Check Device Manager for the device")
        print("4. Verify Thorlabs Kinesis is installed")
        print("5. Check Control Panel -> Devices for any unknown devices")
    else:
        for i in range(device_list.Count):
            device_info = device_list[i]
            print(f"Device {i+1}:")
            print(f"  Serial Number: {device_info.SerialNumber}")
            print(f"  Device Model: {device_info.DeviceModel}")
            print(f"  USB Port: {device_info.UsbPort if hasattr(device_info, 'UsbPort') else 'N/A'}")
            print(f"  Description: {device_info.Description}")
            print()

except ImportError as e:
    print("❌ Error: Thorlabs Kinesis not installed or DLLs not found")
    print(f"   {e}")
    print("\nInstall from: https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=Motion_Control")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
