"""
Debug Audio Script - Pycaw Version (Capture Devices Only)

This script uses pycaw to enumerate and monitor ONLY capture devices (microphones).
It's a high-level version of debug_audio.py.

What this script does:
1. Enumerates all active CAPTURE devices (microphones/line-ins) only
2. Displays their friendly names and IDs
3. Monitors audio input levels in real-time for 10 seconds
4. Shows a visual bar representation of the audio activity
"""

import time
import sys
from pycaw.pycaw import AudioUtilities
from comtypes import CLSCTX_ALL, cast, POINTER
import comtypes

def main():
    print("Enumerating Capture Devices (Pycaw - Recording Devices Only)...")
    sys.stdout.flush()
    
    # Step 1: Initialize COM
    # Required for Windows COM operations
    comtypes.CoInitialize()
    
    try:
        # Step 2: Get the device enumerator from pycaw
        # We use AudioUtilities which provides high-level access to Windows Core Audio
        from pycaw.pycaw import IMMDeviceEnumerator, IAudioMeterInformation, IAudioClient
        
        # Create the device enumerator using pycaw's helper method
        # This is a high-level pycaw wrapper around the Windows MMDeviceEnumerator
        device_enumerator = AudioUtilities.GetDeviceEnumerator()
        
        # Step 3: Enumerate CAPTURE devices only
        # eCapture = 1 (data flow direction: capture/recording)
        # DEVICE_STATE_ACTIVE = 1 (only active devices)
        print("Fetching active capture devices...")
        eCapture = 1  # Audio input direction
        DEVICE_STATE_ACTIVE = 1  # Only active devices
        
        # Get collection of capture devices
        collection = device_enumerator.EnumAudioEndpoints(eCapture, DEVICE_STATE_ACTIVE)
        count = collection.GetCount()
        
        print(f"Found [{count}] active capture devices (microphones/line-ins).")
        sys.stdout.flush()
        
        # Step 4: Process each capture device
        devices = []  # Will store (name, meter, client) tuples
        
        for i in range(count):
            print(f"Processing device {i}...")
            sys.stdout.flush()
            
            try:
                # Get the device from the collection
                device = collection.Item(i)
                
                # Get device ID
                # This is a unique identifier for the device
                dev_id = device.GetId()
                
                # Get friendly name
                # This is the human-readable name shown in Windows Sound settings
                try:
                    # Open the property store to read device properties
                    props = device.OpenPropertyStore(0)  # STGM_READ = 0
                    
                    # PKEY_Device_FriendlyName is the property key for the device name
                    from pycaw.constants import PKEY_Device_FriendlyName
                    name_prop = props.GetValue(PKEY_Device_FriendlyName)
                    
                    # Extract the string value from the property variant
                    name = str(name_prop)
                except Exception as e:
                    # If we can't get the name, use a default
                    name = f"Capture Device {i}"
                    print(f"  Warning: Could not get name, using default. Error: {e}")
                
                print(f"[{i}] {name}")
                print(f"    ID: {dev_id}")
                sys.stdout.flush()
                
                # Step 5: Activate the IAudioMeterInformation interface
                # This interface gives us access to the peak meter for this device
                # CLSCTX_ALL = use any execution context
                meter_interface = device.Activate(
                    IAudioMeterInformation._iid_,
                    CLSCTX_ALL,
                    None
                )
                meter = cast(meter_interface, POINTER(IAudioMeterInformation))
                
                # Step 6: Activate IAudioClient
                # CRITICAL: We must start an audio stream for the meter to work!
                # The meter only reports values when there's an active capture stream
                client_interface = device.Activate(
                    IAudioClient._iid_,
                    CLSCTX_ALL,
                    None
                )
                client = cast(client_interface, POINTER(IAudioClient))
                
                # Step 7: Initialize and start the audio stream
                # Get the device's preferred audio format
                audio_format = client.GetMixFormat()
                
                # Initialize the client:
                # - ShareMode=0: AUDCLNT_SHAREMODE_SHARED (share device with other apps)
                # - StreamFlags=0: No special flags
                # - BufferDuration=10000000: 1 second (in 100-nanosecond units)
                # - Periodicity=0: Let the system decide
                # - pFormat=audio_format: Use the device's optimal format
                # - AudioSessionGuid=None: No specific session
                client.Initialize(0, 0, 10000000, 0, audio_format, None)
                
                # Start the stream - this enables the meter!
                client.Start()
                
                devices.append((name, meter, client))
                print(f"    Successfully initialized meter")
                
            except Exception as e:
                print(f"    Error setting up device {i}: {e}")
                # Skip this device but continue with others
                continue
        
        if not devices:
            print("\nNo capture devices were successfully initialized!")
            return
        
        # Step 8: Monitor audio levels for 10 seconds
        print("\nMonitoring for 10 seconds... Please SPEAK into your microphone.")
        print("(The bar fills up as you speak louder)")
        sys.stdout.flush()
        
        start_time = time.time()
        try:
            while time.time() - start_time < 10:
                output_parts = []
                
                # Read peak value from each device
                for name, meter, client in devices:
                    peak = 0.0
                    try:
                        # GetPeakValue() returns a float from 0.0 (silence) to 1.0 (max volume)
                        # This is the peak amplitude in the most recent audio sample
                        peak = meter.GetPeakValue()
                    except Exception:
                        peak = 0.0
                    
                    # Create visual bar (20 characters wide)
                    bar_len = 20
                    filled = int(peak * bar_len)
                    bar = "#" * filled + " " * (bar_len - filled)
                    
                    # Truncate long names for display
                    disp_name = (name[:20] + '..') if len(name) > 22 else name
                    output_parts.append(f"{disp_name}: {peak:.4f} [{bar}]")
                
                # Print on same line (overwrite with \r)
                line = " | ".join(output_parts)
                print(f"\r{line:<150}", end="")
                sys.stdout.flush()
                
                # Update 10 times per second
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            # Allow user to stop with Ctrl+C
            pass
        
        # Step 9: Clean up
        print("\n\nCleaning up...")
        for name, meter, client in devices:
            try:
                client.Stop()
            except Exception:
                pass
        
        print("Done.")
        
    finally:
        # Step 10: Uninitialize COM
        comtypes.CoUninitialize()

if __name__ == "__main__":
    main()
