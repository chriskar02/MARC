# PDXC2 Connection Troubleshooting Guide

## Your Device Info
- **Serial Number**: 112498387
- **USB Port (from Device Manager)**: Port_#0007.Hub_#0001
- **Current Config**: `.env` updated with your SN

## Issue: Device Not Showing in Kinesis

The PDXC2 with SN 112498387 is not appearing in Thorlabs Kinesis device list.

### Checklist:

1. **Power & USB Connection**
   - [ ] PDXC2 is powered ON (check LED indicator)
   - [ ] USB cable is physically connected to PC
   - [ ] Try a different USB port
   - [ ] Try a different USB cable

2. **Driver Installation** (Critical!)
   - [ ] Thorlabs Kinesis software is installed
     - Download from: https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=Motion_Control
   - [ ] The installer should have registered the device drivers
   - [ ] After installing, RESTART your PC

3. **Windows Device Manager Check**
   - [ ] Open Device Manager (Windows Key + X, or devmgmt.msc)
   - [ ] Look for "Universal Serial Bus devices" or "Other devices"
   - [ ] You should see "APT USB Device" or "PDXC2"
   - [ ] If there's a yellow warning triangle, right-click and "Update driver"
   - [ ] Drivers should be auto-found from Thorlabs Kinesis installation

4. **Enable Virtual COM Port (if needed)**
   - [ ] In Device Manager, right-click the APT USB Device
   - [ ] Select "Properties" → "Advanced" tab
   - [ ] Check "Load VCP" box
   - [ ] Click OK and power cycle PDXC2

5. **Kinesis Software Check**
   - [ ] Open Kinesis UI (should be in Start Menu)
   - [ ] It should automatically discover your PDXC2 by serial number
   - [ ] If it doesn't, the drivers aren't installed correctly

## Next Steps

Once you see the PDXC2 in Kinesis UI OR in Device Manager:

1. **Via Kinesis API** (current implementation):
   - Device will auto-connect when serial number is correct
   - No additional config needed beyond what's in `.env`

2. **Via Serial Port** (fallback if Kinesis has issues):
   - Note the COM port from Device Manager (e.g., COM3)
   - Update `.env`: `PDXC2_COM_PORT=COM3`
   - We can add serial-based controller as alternative

## Quick Test

After ensuring driver/connection:

```bash
cd backend
python discover_pdxc2.py      # Should find your device
python test_pdxc2.py          # Should connect successfully
```

## Hardware Check

With PDXC2 powered on and USB connected, you should see:

```
Device Manager:
  Universal Serial Bus devices
    └─ APT USB Device (112498387)  ← Your device
```

OR (after enabling VCP):

```
Ports (COM & LPT):
  └─ APT USB Device Serial Port (COM3)  ← Your COM port
```

## Support Resources

- **Kinesis Software**: https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=Motion_Control
- **PDXC2 User Manual**: Available from Thorlabs downloads
- **APT Serial Commands**: Available with Kinesis software
