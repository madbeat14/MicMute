import sys
import os
import time
import comtypes.client
import ctypes

# Add src directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from MicMute.com_interfaces import (
    CLSID_MMDeviceEnumerator,
    IMMDeviceEnumerator,
    IAudioMeterInformation,
    eCapture,
    CLSCTX_ALL,
    IPropertyStore,
    PKEY_Device_FriendlyName
)

def main():
    print("Initializing Audio Meter Debugger...")
    
    try:
        enumerator = comtypes.client.CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
        
        # Get Default Devices
        def_console = enumerator.GetDefaultAudioEndpoint(eCapture, 0).GetId()
        def_media = enumerator.GetDefaultAudioEndpoint(eCapture, 1).GetId()
        def_comm = enumerator.GetDefaultAudioEndpoint(eCapture, 2).GetId()
        
        print(f"Default Console: {def_console}")
        print(f"Default Media:   {def_media}")
        print(f"Default Comm:    {def_comm}")

        # Enumerate all active capture devices
        devices_collection = enumerator.EnumAudioEndpoints(eCapture, 1) # 1 = DEVICE_STATE_ACTIVE
        count = devices_collection.GetCount()
        print(f"Found {count} active capture devices.")
        
        meters = []
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
            if dev_id == def_media: is_def += " [MEDIA]"
            if dev_id == def_comm: is_def += " [COMM]"
            
            print(f"Device {i}: {name} ({dev_id}){is_def}")
            
            try:
                meter_unk = device.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
                meter = meter_unk.QueryInterface(IAudioMeterInformation)
                meters.append((i, meter))
            except Exception as e:
                print(f"  Failed to activate meter for device {i}: {e}")

        print("\nReading Peak Values (Press Ctrl+C to stop)...")
        for _ in range(10): # Run for about 1 second
            output = []
            for idx, meter in meters:
                try:
                    val = meter.GetPeakValue()
                    if val > 0.0001:
                        output.append(f"Dev {idx}: {val:.4f}")
                except:
                    pass
            
            if output:
                print(" | ".join(output))
            else:
                print("Silence...")
            
            time.sleep(0.1)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
