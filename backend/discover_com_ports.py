"""
Discover PDXC2 via COM ports (serial protocol)

The PDXC2 can also be accessed via serial port (APT USB Device COM port)
"""

import serial.tools.list_ports
import sys

print("=" * 60)
print("Available COM Ports (Serial Devices)")
print("=" * 60)

ports = serial.tools.list_ports.comports()

if not ports:
    print("\n❌ No COM ports found!")
    sys.exit(1)

print(f"\nFound {len(ports)} port(s):\n")

pdxc2_candidates = []

for i, port in enumerate(ports, 1):
    print(f"{i}. Port: {port.name}")
    print(f"   Description: {port.description}")
    print(f"   Device: {port.device}")
    print(f"   Manufacturer: {port.manufacturer}")
    print(f"   Serial Number: {port.serial_number}")
    print(f"   Product: {port.product}")
    print()
    
    # PDXC2 devices typically show as "APT USB Device"
    if "APT" in str(port.description).upper() or "THORLABS" in str(port.description).upper():
        pdxc2_candidates.append(port.name)

if pdxc2_candidates:
    print(f"✓ Found {len(pdxc2_candidates)} potential PDXC2 port(s):")
    for port_name in pdxc2_candidates:
        print(f"  - {port_name}")
    print(f"\nUpdate your .env with: PDXC2_COM_PORT={pdxc2_candidates[0]}")
else:
    print("ℹ️  No obvious PDXC2 port found.")
    print("   If you see a COM port labeled 'APT USB Device', that's likely your PDXC2")
    print("   You may need to enable 'Load VCP' in Device Manager for your PDXC2")
