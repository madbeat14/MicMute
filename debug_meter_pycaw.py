"""
Debug Meter Script - Pycaw Version (Capture Devices Only)

This script uses pycaw to monitor ONLY capture devices (microphones).
It's a high-level version of debug_meter.py.

What this script does:
1. Identifies the default capture device (microphone)
2. Enumerates all active CAPTURE devices (microphones/line-ins) only
3. Shows which device is the default [CONSOLE]
4. Initializes audio streams and meters for all capture devices
5. Monitors audio levels for ~1 second, displaying them by device name
"""

import sys
import time
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation, IAudioClient, IMMDeviceEnumerator
from comtypes import CLSCTX_ALL, cast, POINTER
import comtypes

def main():
    print("Initializing Audio Meter Debugger (Pycaw - Capture Devices Only)...")
    
    # Step 1: Initialize COM
    # COM must be initialized for each thread that uses Windows COM APIs
    comtypes.CoInitialize()
    
    try:
        # Step 2: Get the default capture device using pycaw
        # This is the microphone Windows uses by default for apps
        print("Getting default capture device...")
        default_device = AudioUtilities.GetMicrophone()
        
        default_id = None
        if default_device and hasattr(default_device, '_device'):
            # Get the device ID from the underlying COM device
            try:
                default_id = default_device._device.GetId()
                default_name = default_device.FriendlyName
                print(f"Default Console Device: {default_name}")
                print(f"Default Console ID: {default_id}")
            except Exception as e:
                print(f"Warning: Could not get default device ID: {e}")
        else:
            print("Warning: Could not get default device")
        
        # Step 3: Create the device enumerator
        # Use pycaw's helper method to get the enumerator
        print("\nEnumerating capture devices...")
        device_enumerator = AudioUtilities.GetDeviceEnumerator()
        
        # Step 4: Enumerate CAPTURE devices only
        # eCapture = 1 (recording devices)
        # DEVICE_STATE_ACTIVE = 1 (only active devices)
        eCapture = 1
        DEVICE_STATE_ACTIVE = 1
        
        collection = device_enumerator.EnumAudioEndpoints(eCapture, DEVICE_STATE_ACTIVE)
        count = collection.GetCount()
        print(f"Found {count} active capture devices.")
        
        # Step 5: Set up meters for each capture device
        meters = []  # Will store (device_name, meter) tuples
        clients = []  # Keep clients alive to maintain streams
        
        for i in range(count):
            try:
                # Get the device from the collection
                device = collection.Item(i)
                
                # Get device ID
                dev_id = device.GetId()
                
                # Get friendly name from property store
                try:
                    props = device.OpenPropertyStore(0)  # STGM_READ = 0
                    from pycaw.constants import PKEY_Device_FriendlyName
                    name_prop = props.GetValue(PKEY_Device_FriendlyName)
                    name = str(name_prop)
                except Exception:
                    name = f"Capture Device {i}"
                
                # Check if this is the default device
                is_default = " [CONSOLE]" if dev_id == default_id else ""
                
                print(f"Device {i}: {name} ({dev_id}){is_default}")
                
                # Step 6: Activate IAudioMeterInformation
                # This interface provides the peak meter for reading audio levels
                meter_interface = device.Activate(
                    IAudioMeterInformation._iid_,
                    CLSCTX_ALL,
                    None
                )
                meter = cast(meter_interface, POINTER(IAudioMeterInformation))
                
                # Step 7: Activate IAudioClient
                # CRITICAL: We need an active audio stream for the meter to work!
                # Without starting the client, GetPeakValue() returns 0.0
                client_interface = device.Activate(
                    IAudioClient._iid_,
                    CLSCTX_ALL,
                    None
                )
                client = cast(client_interface, POINTER(IAudioClient))
                
                # Step 8: Initialize and start the audio stream
                # Get the device's preferred audio format
                audio_format = client.GetMixFormat()
                
                # Initialize:
                # - ShareMode=0: AUDCLNT_SHAREMODE_SHARED (share device)
                # - StreamFlags=0: No special flags
                # - BufferDuration=10000000: 1 second (100-nanosecond units)
                # - Periodicity=0: System decides
                # - pFormat=audio_format: Use device's format
                # - AudioSessionGuid=None: No specific session
                client.Initialize(0, 0, 10000000, 0, audio_format, None)
                
                # Start the stream - this enables the meter!
                client.Start()
                
                # Keep references so they don't get garbage collected
                clients.append(client)
                meters.append((name, meter))
                
                print(f"  Started stream on device {i}")
                
            except Exception as e:
                print(f"  Failed to setup device {i}: {e}")
                continue
        
        if not meters:
            print("\nNo capture devices were successfully set up!")
            return
        
        # Step 9: Monitor the meters
        print("\nReading Peak Values (monitoring for ~1 second)...")
        print("Speak into your microphone to see the levels change!")
        
        # Monitor for ~1 second (10 iterations * 100ms)
        for iteration in range(10):
            output = []
            
            for name, meter in meters:
                try:
                    # GetPeakValue() returns 0.0 (silence) to 1.0 (max volume)
                    # This is the peak amplitude in the most recent audio sample
                    peak_value = meter.GetPeakValue()
                    
                    # Truncate long names for display
                    display_name = (name[:15] + '..') if len(name) > 17 else name
                    output.append(f"{display_name}: {peak_value:.4f}")
                    
                except Exception as e:
                    output.append(f"{name} Err: {e}")
            
            # Print all meters on one line
            if output:
                print(" | ".join(output))
            
            # Update 10 times per second
            time.sleep(0.1)
        
        # Step 10: Cleanup
        print("\nStopping audio streams...")
        for client in clients:
            try:
                client.Stop()
            except Exception:
                pass
        
        print("Done.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Step 11: Uninitialize COM
        # Clean up COM resources
        comtypes.CoUninitialize()

if __name__ == "__main__":
    main()
