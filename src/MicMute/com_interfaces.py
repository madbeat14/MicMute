from comtypes import GUID, IUnknown, COMMETHOD, HRESULT, POINTER, BSTR
from comtypes.client import CreateObject
import ctypes
from ctypes import wintypes, Structure

# --- Constants ---

# CLSID_MMDeviceEnumerator: Standard Windows Class ID for the Multimedia Device Enumerator.
# Source: Defined in mmdeviceapi.h (Windows SDK).
# Reference: https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nn-mmdeviceapi-immdeviceenumerator
CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")

# CLSID_PolicyConfig: Undocumented Class ID for managing default audio devices.
# Source: Reverse engineered from Windows system DLLs (e.g., AudioSes.dll).
# Note: This GUID has remained stable across Windows 7, 8, 10, and 11, but is not officially supported by Microsoft.
# If this changes, search for "IPolicyConfig" or "CPolicyConfigClient" in open-source audio switchers.
CLSID_PolicyConfig = GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}")

eCapture = 1
DEVICE_STATE_ACTIVE = 1
CLSCTX_ALL = 23

# --- Structures ---
class WAVEFORMATEX(Structure):
    _fields_ = [
        ("wFormatTag", wintypes.WORD),
        ("nChannels", wintypes.WORD),
        ("nSamplesPerSec", wintypes.DWORD),
        ("nAvgBytesPerSec", wintypes.DWORD),
        ("nBlockAlign", wintypes.WORD),
        ("wBitsPerSample", wintypes.WORD),
        ("cbSize", wintypes.WORD),
    ]

class PROPERTYKEY(Structure):
    _fields_ = [
        ("fmtid", GUID),
        ("pid", wintypes.DWORD),
    ]

class PROPVARIANT(Structure):
    _fields_ = [
        ("vt", wintypes.WORD),
        ("wReserved1", wintypes.WORD),
        ("wReserved2", wintypes.WORD),
        ("wReserved3", wintypes.WORD),
        ("data", ctypes.c_ulonglong * 2),
    ]

# --- Interfaces ---

# IMMDevice: Represents a generic audio device.
# Source: mmdeviceapi.h (Windows SDK)
# Reference: https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nn-mmdeviceapi-immdevice
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

# IMMDeviceCollection: Represents a collection of audio devices.
# Source: mmdeviceapi.h (Windows SDK)
# Reference: https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nn-mmdeviceapi-immdevicecollection
class IMMDeviceCollection(IUnknown):
    _iid_ = GUID("{0BD7A1BE-7A1A-44DB-8397-CC539238725E}")
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetCount',
                  (['out', 'retval'], POINTER(ctypes.c_uint), 'pcDevices')),
        COMMETHOD([], HRESULT, 'Item',
                  (['in'], ctypes.c_uint, 'nDevice'),
                  (['out', 'retval'], POINTER(POINTER(IMMDevice)), 'ppDevice')),
    ]

# IMMDeviceEnumerator: Provides methods for enumerating audio devices.
# Source: mmdeviceapi.h (Windows SDK)
# Reference: https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nn-mmdeviceapi-immdeviceenumerator
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
                  (['in'], BSTR, 'pwstrId'),
                  (['out', 'retval'], POINTER(POINTER(IMMDevice)), 'ppDevice')),
        COMMETHOD([], HRESULT, 'RegisterEndpointNotificationCallback',
                  (['in'], POINTER(IUnknown), 'pClient')),
        COMMETHOD([], HRESULT, 'UnregisterEndpointNotificationCallback',
                  (['in'], POINTER(IUnknown), 'pClient')),
    ]

# IPolicyConfig: Undocumented interface for setting default audio devices.
# Source: Reverse engineered. Matches CLSID_PolicyConfig.
# Note: Microsoft does not publish this interface. It is widely used in community tools to switch audio devices programmatically.
class IPolicyConfig(IUnknown):
    _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetMixFormat',
                  (['in'], ctypes.c_wchar_p, 'pszDeviceName'),
                  (['out'], ctypes.POINTER(WAVEFORMATEX), 'ppFormat')),
        COMMETHOD([], HRESULT, 'GetDeviceFormat',
                  (['in'], ctypes.c_wchar_p, 'pszDeviceName'),
                  (['in'], ctypes.c_int, 'bDefault'),
                  (['out'], ctypes.POINTER(WAVEFORMATEX), 'ppFormat')),
        COMMETHOD([], HRESULT, 'ResetDeviceFormat',
                  (['in'], ctypes.c_wchar_p, 'pszDeviceName')),
        COMMETHOD([], HRESULT, 'SetDeviceFormat',
                  (['in'], ctypes.c_wchar_p, 'pszDeviceName'),
                  (['in'], ctypes.POINTER(WAVEFORMATEX), 'pEndpointFormat'),
                  (['in'], ctypes.POINTER(WAVEFORMATEX), 'pMixFormat')),
        COMMETHOD([], HRESULT, 'GetProcessingPeriod',
                  (['in'], ctypes.c_wchar_p, 'pszDeviceName'),
                  (['in'], ctypes.c_int, 'bDefault'),
                  (['out'], ctypes.POINTER(ctypes.c_longlong), 'pmftDefaultPeriod'),
                  (['out'], ctypes.POINTER(ctypes.c_longlong), 'pmftMinimumPeriod')),
        COMMETHOD([], HRESULT, 'SetProcessingPeriod',
                  (['in'], ctypes.c_wchar_p, 'pszDeviceName'),
                  (['in'], ctypes.POINTER(ctypes.c_longlong), 'pmftPeriod')),
        COMMETHOD([], HRESULT, 'GetShareMode',
                  (['in'], ctypes.c_wchar_p, 'pszDeviceName'),
                  (['out'], ctypes.POINTER(ctypes.c_int), 'pMode')),
        COMMETHOD([], HRESULT, 'SetShareMode',
                  (['in'], ctypes.c_wchar_p, 'pszDeviceName'),
                  (['in'], ctypes.c_int, 'mode')),
        COMMETHOD([], HRESULT, 'GetPropertyValue',
                  (['in'], ctypes.c_wchar_p, 'pszDeviceName'),
                  (['in'], ctypes.POINTER(PROPERTYKEY), 'pKey'),
                  (['out'], ctypes.POINTER(PROPVARIANT), 'pValue')),
        COMMETHOD([], HRESULT, 'SetPropertyValue',
                  (['in'], ctypes.c_wchar_p, 'pszDeviceName'),
                  (['in'], ctypes.POINTER(PROPERTYKEY), 'pKey'),
                  (['in'], ctypes.POINTER(PROPVARIANT), 'pValue')),
        COMMETHOD([], HRESULT, 'SetDefaultEndpoint',
                  (['in'], ctypes.c_wchar_p, 'wszDeviceId'),
                  (['in'], ctypes.c_int, 'role')),
        COMMETHOD([], HRESULT, 'SetEndpointVisibility',
                  (['in'], ctypes.c_wchar_p, 'wszDeviceId'),
                  (['in'], ctypes.c_int, 'bVisible')),
    ]

# IAudioMeterInformation: Represents a peak meter on an audio device.
# Source: endpointvolume.h (Windows SDK)
# Reference: https://learn.microsoft.com/en-us/windows/win32/api/endpointvolume/nn-endpointvolume-iaudiometerinformation
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
