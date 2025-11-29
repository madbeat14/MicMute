import time
import comtypes
from comtypes import GUID, COMMETHOD, HRESULT, POINTER, IUnknown
from comtypes.client import CreateObject
import ctypes
import sys

# --- COM Interface Definitions ---
# These classes define the structure of the Windows Core Audio APIs (WASAPI) COM interfaces.
# They are necessary to interact with audio devices at a low level.

# CLSID for the MMDeviceEnumerator, the entry point for WASAPI.
CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")

# Structure for audio format information.
class WAVEFORMATEX(ctypes.Structure):
    _fields_ = [
        ('wFormatTag', ctypes.c_ushort),
        ('nChannels', ctypes.c_ushort),
        ('nSamplesPerSec', ctypes.c_uint),
        ('nAvgBytesPerSec', ctypes.c_uint),
        ('nBlockAlign', ctypes.c_ushort),
        ('wBitsPerSample', ctypes.c_ushort),
        ('cbSize', ctypes.c_ushort),
    ]

# Property Key structure for identifying properties.
class PROPERTYKEY(ctypes.Structure):
    _fields_ = [
        ("fmtid", GUID),
        ("pid", ctypes.c_ulong),
    ]

# PropVariant structure (simplified for reading string pointers).
class PROPVARIANT(ctypes.Structure):
    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("wReserved1", ctypes.c_ushort),
        ("wReserved2", ctypes.c_ushort),
        ("wReserved3", ctypes.c_ushort),
        ("data", ctypes.c_ulong * 2), # Placeholder for union
    ]

# Interface for a specific audio device (e.g., a microphone or speaker).
class IMMDevice(IUnknown):
    _iid_ = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
    _methods_ = [
        # Activate: Creates a specific interface (like IAudioMeterInformation) for this device.
        COMMETHOD([], HRESULT, 'Activate',
                  (['in'], POINTER(GUID), 'iid'),
                  (['in'], ctypes.c_uint, 'dwClsCtx'),
                  (['in'], POINTER(IUnknown), 'pActivationParams'),
                  (['out', 'retval'], POINTER(POINTER(IUnknown)), 'ppInterface')),
        # OpenPropertyStore: Access properties like the friendly name of the device.
        COMMETHOD([], HRESULT, 'OpenPropertyStore',
                  (['in'], ctypes.c_uint, 'stgmAccess'),
                  (['out', 'retval'], POINTER(POINTER(IUnknown)), 'ppProperties')),
        # GetId: Retrieves the unique string ID of the device.
        COMMETHOD([], HRESULT, 'GetId',
                  (['out', 'retval'], POINTER(ctypes.c_wchar_p), 'ppstrId')),
        # GetState: Retrieves the current state (active, disabled, etc.) of the device.
        COMMETHOD([], HRESULT, 'GetState',
                  (['out', 'retval'], POINTER(ctypes.c_uint), 'pdwState')),
    ]

# Interface for a collection of audio devices.
class IMMDeviceCollection(IUnknown):
    _iid_ = GUID("{0BD7A1BE-7A1A-44DB-8397-CC539238725E}")
    _methods_ = [
        # GetCount: Returns the number of devices in the collection.
        COMMETHOD([], HRESULT, 'GetCount',
                  (['out', 'retval'], POINTER(ctypes.c_uint), 'pcDevices')),
        # Item: Retrieves a specific device from the collection by index.
        COMMETHOD([], HRESULT, 'Item',
                  (['in'], ctypes.c_uint, 'nDevice'),
                  (['out', 'retval'], POINTER(POINTER(IMMDevice)), 'ppDevice')),
    ]

# Interface for enumerating audio devices.
class IMMDeviceEnumerator(IUnknown):
    _iid_ = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
    _methods_ = [
        # EnumAudioEndpoints: Lists audio devices based on data flow (render/capture) and state.
        COMMETHOD([], HRESULT, 'EnumAudioEndpoints',
                  (['in'], ctypes.c_int, 'dataFlow'),
                  (['in'], ctypes.c_uint, 'dwStateMask'),
                  (['out', 'retval'], POINTER(POINTER(IMMDeviceCollection)), 'ppDevices')),
        # GetDefaultAudioEndpoint: Gets the default device for a specific role (e.g., default communication device).
        COMMETHOD([], HRESULT, 'GetDefaultAudioEndpoint',
                  (['in'], ctypes.c_int, 'dataFlow'),
                  (['in'], ctypes.c_int, 'role'),
                  (['out', 'retval'], POINTER(POINTER(IMMDevice)), 'ppEndpoint')),
        # GetDevice: Gets a device by its ID string.
        COMMETHOD([], HRESULT, 'GetDevice',
                  (['in'], comtypes.BSTR, 'pwstrId'),
                  (['out', 'retval'], POINTER(POINTER(IMMDevice)), 'ppDevice')),
        COMMETHOD([], HRESULT, 'RegisterEndpointNotificationCallback',
                  (['in'], POINTER(IUnknown), 'pClient')),
        COMMETHOD([], HRESULT, 'UnregisterEndpointNotificationCallback',
                  (['in'], POINTER(IUnknown), 'pClient')),
    ]

# Interface for accessing audio peak meter information.
class IAudioMeterInformation(IUnknown):
    _iid_ = GUID("{C02216F6-8C67-4B5B-9D00-D008E73E0064}")
    _methods_ = [
        # GetPeakValue: Gets the peak sample value for the channels in the audio stream.
        # Returns a float between 0.0 (silence) and 1.0 (full volume).
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

# Interface for creating and managing audio streams.
class IAudioClient(IUnknown):
    _iid_ = GUID("{1CB9AD4C-DBFA-4c32-B178-C2F568A703B2}")
    _methods_ = [
        COMMETHOD([], HRESULT, 'Initialize',
                  (['in'], ctypes.c_int, 'ShareMode'),
                  (['in'], ctypes.c_uint, 'StreamFlags'),
                  (['in'], ctypes.c_longlong, 'hnsBufferDuration'),
                  (['in'], ctypes.c_longlong, 'hnsPeriodicity'),
                  (['in'], POINTER(WAVEFORMATEX), 'pFormat'),
                  (['in'], POINTER(GUID), 'AudioSessionGuid')),
        COMMETHOD([], HRESULT, 'GetBufferSize',
                  (['out', 'retval'], POINTER(ctypes.c_uint), 'pNumBufferFrames')),
        COMMETHOD([], HRESULT, 'GetStreamLatency',
                  (['out', 'retval'], POINTER(ctypes.c_longlong), 'phnsLatency')),
        COMMETHOD([], HRESULT, 'GetCurrentPadding',
                  (['out', 'retval'], POINTER(ctypes.c_uint), 'pNumPaddingFrames')),
        COMMETHOD([], HRESULT, 'IsFormatSupported',
                  (['in'], ctypes.c_int, 'ShareMode'),
                  (['in'], POINTER(WAVEFORMATEX), 'pFormat'),
                  (['out', 'retval'], POINTER(POINTER(WAVEFORMATEX)), 'ppClosestMatch')),
        COMMETHOD([], HRESULT, 'GetMixFormat',
                  (['out', 'retval'], POINTER(POINTER(WAVEFORMATEX)), 'ppDeviceFormat')),
        COMMETHOD([], HRESULT, 'GetDevicePeriod',
                  (['out', 'retval'], POINTER(ctypes.c_longlong), 'phnsDefaultDevicePeriod'),
                  (['out', 'retval'], POINTER(ctypes.c_longlong), 'phnsMinimumDevicePeriod')),
        COMMETHOD([], HRESULT, 'Start'),
        COMMETHOD([], HRESULT, 'Stop'),
        COMMETHOD([], HRESULT, 'Reset'),
        COMMETHOD([], HRESULT, 'SetEventHandle',
                  (['in'], ctypes.c_void_p, 'eventHandle')),
        COMMETHOD([], HRESULT, 'GetService',
                  (['in'], POINTER(GUID), 'riid'),
                  (['out', 'retval'], POINTER(IUnknown), 'ppv')),
    ]

# Interface for reading properties from the property store.
class IPropertyStore(IUnknown):
    _iid_ = GUID("{886d8eeb-8cf2-4446-8d02-cdba1dbdcf99}")
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetCount',
                  (['out', 'retval'], POINTER(ctypes.c_ulong), 'cProps')),
        COMMETHOD([], HRESULT, 'GetAt',
                  (['in'], ctypes.c_ulong, 'iProp'),
                  (['out', 'retval'], POINTER(PROPERTYKEY), 'pkey')),
        COMMETHOD([], HRESULT, 'GetValue',
                  (['in'], POINTER(PROPERTYKEY), 'key'),
                  (['out', 'retval'], POINTER(PROPVARIANT), 'pv')),
        COMMETHOD([], HRESULT, 'SetValue',
                  (['in'], POINTER(PROPERTYKEY), 'key'),
                  (['in'], POINTER(PROPVARIANT), 'propvar')),
        COMMETHOD([], HRESULT, 'Commit'),
    ]

# Constants
eCapture = 1            # Data flow direction: Capture (Microphone)
DEVICE_STATE_ACTIVE = 1 # Device state: Active
CLSCTX_ALL = 23         # Context for CoCreateInstance (In-process, Local server, Remote server)
STGM_READ = 0           # Access mode for Property Store

# Property Key for Device Friendly Name: {a45c254e-df1c-4efd-8020-67d146a850e0}, 14
PKEY_Device_FriendlyName = PROPERTYKEY(GUID("{a45c254e-df1c-4efd-8020-67d146a850e0}"), 14)

def main():
    print("Enumerating Capture Devices (Manual COM Definitions)...")
    sys.stdout.flush()
    
    # Initialize the COM library.
    comtypes.CoInitialize()
    try:
        # Create the Device Enumerator object.
        enumerator = CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
        
        # Enumerate active capture devices (microphones).
        collection = enumerator.EnumAudioEndpoints(eCapture, DEVICE_STATE_ACTIVE)
        count = collection.GetCount()
        print(f"Found [{count}] active capture devices.")
        sys.stdout.flush()
        
        devices = []
        clients = [] # Keep clients alive to prevent garbage collection and stream stopping.
        
        # Loop through each found device.
        for i in range(count):
            print(f"Processing device {i}...")
            sys.stdout.flush()
            try:
                # Get the device object at index i.
                device_unk = collection.Item(i)
                device = device_unk.QueryInterface(IMMDevice)
            except Exception as e:
                print(f"  Error getting device item: {e}")
                continue
            
            try:
                # Get the unique ID of the device.
                dev_id = device.GetId()
            except Exception as e:
                print(f"  Error getting ID: {e}")
                dev_id = "Unknown ID"
            
            # Get the Friendly Name
            friendly_name = "Unknown Name"
            try:
                props_unk = device.OpenPropertyStore(STGM_READ)
                props = props_unk.QueryInterface(IPropertyStore)
                val = props.GetValue(ctypes.byref(PKEY_Device_FriendlyName))
                # VT_LPWSTR = 31. The data is a pointer to a wide string.
                if val.vt == 31: 
                    # Access the data field.
                    # The 'data' field in our struct is c_ulong * 2 (8 bytes).
                    # We cast the address of 'data' to a POINTER(c_void_p) to read the pointer value.
                    ptr_val = ctypes.cast(ctypes.byref(val.data), POINTER(ctypes.c_void_p))[0]
                    if ptr_val:
                        friendly_name = ctypes.cast(ptr_val, ctypes.c_wchar_p).value
            except Exception as e:
                print(f"  Error getting friendly name: {e}")
                friendly_name = f"Error ({e})"

            name = f"{friendly_name}"

            print(f"[{i}] {name}")
            print(f"    ID: {dev_id}")
            sys.stdout.flush()
            
            try:
                # Activate the IAudioMeterInformation interface for this device.
                # This allows us to read the audio levels.
                meter_unk = device.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
                meter = meter_unk.QueryInterface(IAudioMeterInformation)
                
                # Activate the IAudioClient interface.
                # This is CRITICAL: We need to initialize and start an audio stream
                # because some devices won't report meter values unless a stream is active.
                client_unk = device.Activate(IAudioClient._iid_, CLSCTX_ALL, None)
                client = client_unk.QueryInterface(IAudioClient)
                
                # Initialize the Audio Client.
                fmt = client.GetMixFormat()
                # Initialize(ShareMode=0 (Shared), Flags=0, BufferDuration=10000000 (1 sec), Periodicity=0, Format=fmt, AudioSessionGuid=None)
                client.Initialize(0, 0, 10000000, 0, fmt, None)
                
                # Start the audio stream.
                client.Start()
                
                # Store the client to keep it alive.
                clients.append(client)
                
                devices.append((name, meter))
            except Exception as e:
                print(f"    Error getting meter/client: {e}")
                devices.append((name, None))

        print("\nMonitoring for 10 seconds... Please SPEAK into your microphone.")
        sys.stdout.flush()
        
        # Monitor audio levels for 10 seconds.
        start_time = time.time()
        try:
            while time.time() - start_time < 10:
                output_parts = []
                
                # Check peak value for each device.
                for name, meter in devices:
                    peak = 0.0
                    if meter:
                        try:
                            # Read the current peak value (0.0 to 1.0).
                            peak = meter.GetPeakValue()
                        except Exception:
                            peak = 0.0
                    
                    # Create a visual bar for the volume level.
                    bar_len = 20
                    filled = int(peak * bar_len)
                    bar = "#" * filled + " " * (bar_len - filled)
                    
                    # Truncate name for display
                    disp_name = (name[:20] + '..') if len(name) > 22 else name
                    output_parts.append(f"{disp_name}: {peak:.4f} [{bar}]")
                
                # Print the levels on the same line (using \r to overwrite).
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
        # Uninitialize the COM library.
        comtypes.CoUninitialize()

if __name__ == "__main__":
    main()
