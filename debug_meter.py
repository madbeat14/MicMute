import sys
import os
import time
import comtypes.client
import ctypes
from ctypes import POINTER

# Add src directory to sys.path to allow importing modules from the MicMute package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import COM interface definitions and constants from the project's utility module.
from MicMute.com_interfaces import (
    CLSID_MMDeviceEnumerator,
    IMMDeviceEnumerator,
    IMMDevice,
    IAudioMeterInformation,
    IAudioClient,
    WAVEFORMATEX,
    eCapture,
    CLSCTX_ALL,
    IPropertyStore,
    PKEY_Device_FriendlyName
)

def main():
    import comtypes
    # Initialize the COM library.
    comtypes.CoInitialize()
    print("Initializing Audio Meter Debugger...")
    
    try:
        # Create the Device Enumerator object.
        enumerator = comtypes.client.CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
        
        # Get the Default Capture Device (Microphone) for Console role.
        def_console = enumerator.GetDefaultAudioEndpoint(eCapture, 0).GetId()
        print(f"Default Console: {def_console}")

        # Enumerate all active capture devices.
        # eCapture = 1 (Microphone), 1 = DEVICE_STATE_ACTIVE
        devices_collection = enumerator.EnumAudioEndpoints(eCapture, 1) 
        count = devices_collection.GetCount()
        print(f"Found {count} active capture devices.")
        
        meters = []
        clients = [] # Keep clients alive to prevent garbage collection and stream stopping.
        
        for i in range(count):
            # Get the device at index i.
            device_unk = devices_collection.Item(i)
            device = device_unk.QueryInterface(IMMDevice)
            dev_id = device.GetId()
            
            # Get the friendly name of the device using the Property Store.
            name = "Unknown"
            try:
                # Open the property store for reading.
                props_unk = device.OpenPropertyStore(0)
                props = props_unk.QueryInterface(IPropertyStore)
                # Get the value of the FriendlyName property.
                val = props.GetValue(PKEY_Device_FriendlyName)
                if val.vt == 31: # VT_LPWSTR (Pointer to wide string)
                    ptr = val.data[0]
                    name = ctypes.cast(ptr, ctypes.c_wchar_p).value
            except Exception as e:
                name = f"Error: {e}"

            # Check if this is the default device.
            is_def = ""
            if dev_id == def_console: is_def += " [CONSOLE]"
            
            print(f"Device {i}: {name} ({dev_id}){is_def}")
            
            try:
                # Activate the IAudioMeterInformation interface.
                # This is used to read the peak audio levels.
                meter_unk = device.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
                meter = ctypes.cast(meter_unk, POINTER(IAudioMeterInformation))
                
                # Activate the IAudioClient interface.
                # This is CRITICAL: We need to initialize and start an audio stream
                # because some devices won't report meter values unless a stream is active.
                client_unk = device.Activate(IAudioClient._iid_, CLSCTX_ALL, None)
                client = ctypes.cast(client_unk, POINTER(IAudioClient))
                
                # Initialize the Audio Client.
                fmt = client.GetMixFormat()
                # Initialize(ShareMode=0 (Shared), Flags=0, BufferDuration=10000000 (1 sec), Periodicity=0, Format=fmt, AudioSessionGuid=None)
                client.Initialize(0, 0, 10000000, 0, fmt, None)
                
                # Start the audio stream.
                client.Start()
                
                # Store the client to keep it alive.
                clients.append(client)
                
                meters.append((name, meter))
                print(f"  Started stream on device {i}")
            except Exception as e:
                print(f"  Failed to setup device {i}: {e}")

        print("\nReading Peak Values (Press Ctrl+C to stop)...")
        # Monitor for a short period (approx 1 second).
        for _ in range(10): 
            output = []
            for name, meter in meters:
                try:
                    # Get the peak value from the meter.
                    val = meter.GetPeakValue()
                    # Truncate name for display
                    disp_name = (name[:15] + '..') if len(name) > 17 else name
                    output.append(f"{disp_name}: {val:.4f}")
                except Exception as e:
                    output.append(f"{name} Err: {e}")
            
            if output:
                print(" | ".join(output))
            
            time.sleep(0.1)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    # Note: We are not explicitly uninitializing COM here as the script ends,
    # but in a long-running app, you should call comtypes.CoUninitialize().

if __name__ == "__main__":
    main()
