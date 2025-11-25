"""
List available methods on DeviceManagerCLI
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import clr
    dll_path = r"C:\Program Files\Thorlabs\Kinesis"
    
    clr.AddReference(f"{dll_path}\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
    
    from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
    
    print("Available methods on DeviceManagerCLI:")
    print("=" * 60)
    
    methods = [m for m in dir(DeviceManagerCLI) if not m.startswith('_')]
    for method in sorted(methods):
        print(f"  {method}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
