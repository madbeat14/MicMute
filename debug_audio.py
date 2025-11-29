import time
import comtypes
from comtypes import GUID, COMMETHOD, HRESULT, POINTER, IUnknown
from comtypes.client import CreateObject
import ctypes
import sys

# --- COM Interface Definitions ---

CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")

class IMMDevice(IUnknown):
    _iid_ = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
    _methods_ = [
        COMMETHOD([], HRESULT, 'Activate',
                  (['in'], POINTER(GUID), 'iid'),
                  (['in'], ctypes.c_uint, 'dwClsCtx'),
                  (['in'], POINTER(IUnknown), 'pActivationParams'),
                  (['out', 'retval'], POINTER(POINTER(IUnknown)), 'ppInterface')),
        COMMETHOD([], HRESULT, 'OpenPropertyStore',
                  (['in'], ctypes.c_uint, 'stgmAccess'),
                  (['out', 'retval'], POINTER(POINTER(IUnknown)), 'ppProperties')),
        COMMETHOD([], HRESULT, 'GetId',
                  (['out', 'retval'], POINTER(ctypes.c_wchar_p), 'ppstrId')),
        COMMETHOD([], HRESULT, 'GetState',
                  (['out', 'retval'], POINTER(ctypes.c_uint), 'pdwState')),
    ]

class IMMDeviceCollection(IUnknown):
    _iid_ = GUID("{0BD7A1BE-7A1A-44DB-8397-CC539238725E}")
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetCount',
                  (['out', 'retval'], POINTER(ctypes.c_uint), 'pcDevices')),
        COMMETHOD([], HRESULT, 'Item',
                  (['in'], ctypes.c_uint, 'nDevice'),
                  (['out', 'retval'], POINTER(POINTER(IMMDevice)), 'ppDevice')),
    ]

class IMMDeviceEnumerator(IUnknown):
    _iid_ = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
    _methods_ = [
        COMMETHOD([], HRESULT, 'EnumAudioEndpoints',
                  (['in'], ctypes.c_int, 'dataFlow'),
                  (['in'], ctypes.c_uint, 'dwStateMask'),
                  (['out', 'retval'], POINTER(POINTER(IMMDeviceCollection)), 'ppDevices')),
        COMMETHOD([], HRESULT, 'GetDefaultAudioEndpoint',
                  (['in'], ctypes.c_int, 'dataFlow'),
                  (['in'], ctypes.c_int, 'role'),
                  (['out', 'retval'], POINTER(POINTER(IMMDevice)), 'ppEndpoint')),
        COMMETHOD([], HRESULT, 'GetDevice',
                  (['in'], comtypes.BSTR, 'pwstrId'),
                  (['out', 'retval'], POINTER(POINTER(IMMDevice)), 'ppDevice')),
        COMMETHOD([], HRESULT, 'RegisterEndpointNotificationCallback',
                  (['in'], POINTER(IUnknown), 'pClient')),
        COMMETHOD([], HRESULT, 'UnregisterEndpointNotificationCallback',
                  (['in'], POINTER(IUnknown), 'pClient')),
    ]

class IAudioMeterInformation(IUnknown):
    _iid_ = GUID("{C02216F6-8C67-4B5B-9D00-D008E73E0064}")
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetPeakValue',
                  (['out', 'retval'], POINTER(ctypes.c_float), 'pfPeak')),
        COMMETHOD([], HRESULT, 'GetMeteringChannelCount',
                  (['out', 'retval'], POINTER(ctypes.c_uint), 'pnChannelCount')),
        COMMETHOD([], HRESULT, 'GetChannelsPeakValues',
                  (['in'], ctypes.c_uint, 'u32ChannelCount'),
                  (['out'], POINTER(ctypes.c_float), 'afPeakValues')),
        COMMETHOD([], HRESULT, 'QueryHardwareSupport',
                  (['out', 'retval'], POINTER(ctypes.c_uint), 'pdwHardwareSupportMask')),
    ]

# Constants
eCapture = 1
DEVICE_STATE_ACTIVE = 1
CLSCTX_ALL = 23

def main():
    print("Enumerating Capture Devices (Manual COM Definitions)...")
    sys.stdout.flush()
    
    comtypes.CoInitialize()
    try:
        enumerator = CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
        collection = enumerator.EnumAudioEndpoints(eCapture, DEVICE_STATE_ACTIVE)
        count = collection.GetCount()
        print(f"Found [{count}] active capture devices.")
        sys.stdout.flush()
        
        devices = []
        for i in range(count):
            print(f"Processing device {i}...")
            sys.stdout.flush()
            try:
                device = collection.Item(i)
            except Exception as e:
                print(f"  Error getting device item: {e}")
                continue
            
            try:
                dev_id = device.GetId()
            except Exception as e:
                print(f"  Error getting ID: {e}")
                dev_id = "Unknown ID"
            
            name = f"Device_{i}"
            # Use ID as name to avoid complex PropertyStore logic
            if dev_id != "Unknown ID":
                 name = f"Device {i} ({str(dev_id)[:10]}...)"

            print(f"[{i}] {name}")
            print(f"    ID: {dev_id}")
            sys.stdout.flush()
            
            try:
                meter_unk = device.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
                meter = meter_unk.QueryInterface(IAudioMeterInformation)
                devices.append((name, meter))
            except Exception as e:
                print(f"    Error getting meter: {e}")
                devices.append((name, None))

        print("\nMonitoring for 10 seconds... Please SPEAK into your microphone.")
        sys.stdout.flush()
        
        start_time = time.time()
        try:
            while time.time() - start_time < 10:
                output_parts = []
                
                for name, meter in devices:
                    peak = 0.0
                    if meter:
                        try:
                            peak = meter.GetPeakValue()
                        except Exception:
                            peak = 0.0
                    
                    bar_len = 20
                    filled = int(peak * bar_len)
                    bar = "#" * filled + " " * (bar_len - filled)
                    
                    disp_name = (name[:13] + '..') if len(name) > 15 else name
                    output_parts.append(f"{disp_name}: {peak:.4f} [{bar}]")
                
                line = " | ".join(output_parts)
                print(f"\r{line:<150}", end="")
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            pass
        
        print("\nDone.")

    except Exception as e:
        print(f"Fatal Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        comtypes.CoUninitialize()

if __name__ == "__main__":
    main()
