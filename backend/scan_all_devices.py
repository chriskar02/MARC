"""
List all device types and connected devices in Kinesis
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import clr
    dll_path = r"C:\Program Files\Thorlabs\Kinesis"
    
    clr.AddReference(f"{dll_path}\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
    
    from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
    
    print("=" * 60)
    print("Thorlabs Kinesis Device Discovery")
    print("=" * 60)
    
    # Build device list
    print("\n1. Scanning for connected devices...")
    DeviceManagerCLI.BuildDeviceList()
    print("   ✓ Device list built")
    
    # Get device types
    print("\n2. Available device types:")
    device_types = DeviceManagerCLI.GetDeviceTypesList()
    print(f"   Found {device_types.Count} device type(s)")
    
    for i in range(min(10, device_types.Count)):
        type_id = device_types[i]
        print(f"     Type {i}: {type_id}")
    
    # Try different type IDs (common ones for piezo)
    print("\n3. Scanning all device types for connected devices:")
    total_found = 0
    
    for type_id in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]:
        try:
            device_list = DeviceManagerCLI.GetDeviceList(type_id)
            if device_list.Count > 0:
                print(f"\n   Type ID {type_id}: Found {device_list.Count} device(s)")
                total_found += device_list.Count
                
                for i in range(device_list.Count):
                    device_info = device_list[i]
                    print(f"     Device {i+1}:")
                    print(f"       Serial: {device_info.SerialNumber}")
                    print(f"       Model: {device_info.DeviceModel}")
                    print(f"       Description: {device_info.Description}")
        except:
            pass
    
    if total_found == 0:
        print("\n   ❌ No devices found!")
        print("\n   This suggests:")
        print("   - Device is not connected via USB, OR")
        print("   - Device drivers are not installed, OR")
        print("   - Device needs to be powered on")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
