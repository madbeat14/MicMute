import sys
import os
import time
import comtypes.client
import ctypes
from ctypes import POINTER

# Add src directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from MicMute.com_interfaces import (
    CLSID_MMDeviceEnumerator,
    IMMDeviceEnumerator,
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
    comtypes.CoInitialize()
    print("Initializing Audio Meter Debugger...")
    
    try:
        enumerator = comtypes.client.CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
        
        # Get Default Devices
        def_console = enumerator.GetDefaultAudioEndpoint(eCapture, 0).GetId()
        print(f"Default Console: {def_console}")

        # Enumerate all active capture devices
        devices_collection = enumerator.EnumAudioEndpoints(eCapture, 1) # 1 = DEVICE_STATE_ACTIVE
        count = devices_collection.GetCount()
        print(f"Found {count} active capture devices.")
        
        meters = []
        clients = [] # Keep clients alive
        
        for i in range(count):
            device = devices_collection.Item(i)
            dev_id = device.GetId()
            
            # Get Name
            name = "Unknown"
            try:
                props = device.OpenPropertyStore(0)
                val = props.GetValue(PKEY_Device_FriendlyName)
                if val.vt == 31: # VT_LPWSTR
                    ptr = val.data[0]
                    name = ctypes.cast(ptr, ctypes.c_wchar_p).value
            except Exception as e:
                name = f"Error: {e}"

            is_def = ""
            if dev_id == def_console: is_def += " [CONSOLE]"
            
            print(f"Device {i}: {name} ({dev_id}){is_def}")
            
            try:
                # Activate Meter
                meter_unk = device.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
                meter = ctypes.cast(meter_unk, POINTER(IAudioMeterInformation))
                
                # Activate Client to start stream
                client_unk = device.Activate(IAudioClient._iid_, CLSCTX_ALL, None)
                client = ctypes.cast(client_unk, POINTER(IAudioClient))
                
                # Initialize Client
                fmt = client.GetMixFormat()
                # ShareMode=0 (Shared), Flags=0
                client.Initialize(0, 0, 10000000, 0, fmt, None)
                client.Start()
                clients.append(client)
                
                meters.append((i, meter))
                print(f"  Started stream on device {i}")
            except Exception as e:
                print(f"  Failed to setup device {i}: {e}")

        print("\nReading Peak Values (Press Ctrl+C to stop)...")
        for _ in range(10): # Run for about 1 second
            output = []
            for idx, meter in meters:
                try:
                    val = meter.GetPeakValue()
                    output.append(f"Dev {idx}: {val:.4f}")
                except Exception as e:
                    output.append(f"Dev {idx} Err: {e}")
            
            if output:
                print(" | ".join(output))
            
            time.sleep(0.1)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
