"""COM interface definitions for Windows Core Audio APIs.

This module defines the COM interfaces and structures needed for interacting
with Windows Core Audio APIs via comtypes. These are primarily undocumented
or reverse-engineered interfaces required for advanced audio functionality.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes, Structure
from typing import ClassVar

from comtypes import GUID, IUnknown, COMMETHOD, HRESULT, POINTER, BSTR
from comtypes.client import CreateObject

__all__ = [
    # CLSIDs
    "CLSID_MMDeviceEnumerator",
    "CLSID_PolicyConfig",
    # Constants
    "eCapture",
    "eRender",
    "eAll",
    "eConsole",
    "eMultimedia",
    "eCommunications",
    "DEVICE_STATE_ACTIVE",
    "CLSCTX_ALL",
    # Structures
    "WAVEFORMATEX",
    "PROPERTYKEY",
    "PROPVARIANT",
    # Interfaces
    "IMMDevice",
    "IMMDeviceCollection",
    "IMMDeviceEnumerator",
    "IPolicyConfig",
    "IPropertyStore",
    "IAudioMeterInformation",
    "IAudioClient",
    "IMMNotificationClient",
    # Property Keys
    "PKEY_Device_FriendlyName",
]

# --- Constants ---

# CLSID_MMDeviceEnumerator: Standard Windows Class ID for the Multimedia Device Enumerator.
# Source: Defined in mmdeviceapi.h (Windows SDK).
CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")

# CLSID_PolicyConfig: Undocumented Class ID for managing default audio devices.
# Source: Reverse engineered from Windows system DLLs (e.g., AudioSes.dll).
CLSID_PolicyConfig = GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}")

# Data flow direction: Capture (Recording)
eCapture = 1
# Data flow direction: Render (Playback)
eRender = 0
# Data flow direction: All
eAll = 2

# Device state: Active
DEVICE_STATE_ACTIVE = 1

# Context: All (In-process, local server, etc.)
CLSCTX_ALL = 23

# ERole Constants
# Interaction with the computer (System sounds, etc.)
eConsole = 0
# Multimedia playback (Music, Movies)
eMultimedia = 1
# Voice communications (Telephony, Chat)
eCommunications = 2


# --- Structures ---


class WAVEFORMATEX(Structure):
    """Defines the format of waveform-audio data.

    Source: mmreg.h (Windows SDK)
    """

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
    """Specifies the FMTID/PID identifier that programmatically identifies a property.

    Source: wtypes.h (Windows SDK)
    """

    _fields_ = [
        ("fmtid", GUID),
        ("pid", wintypes.DWORD),
    ]


class PROPVARIANT(Structure):
    """Container for a range of property values.

    Source: propidl.h (Windows SDK)
    """

    _fields_ = [
        ("vt", wintypes.WORD),
        ("wReserved1", wintypes.WORD),
        ("wReserved2", wintypes.WORD),
        ("wReserved3", wintypes.WORD),
        ("data", ctypes.c_ulonglong * 2),
    ]


# --- Interfaces ---


class IMMDevice(IUnknown):
    """Represents a generic audio device.

    Source: mmdeviceapi.h (Windows SDK)
    Reference: https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nn-mmdeviceapi-immdevice
    """

    _iid_ = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
    _methods_: ClassVar = [
        COMMETHOD(
            [],
            HRESULT,
            "Activate",
            (["in"], POINTER(GUID), "iid"),
            (["in"], ctypes.c_uint, "dwClsCtx"),
            (["in"], POINTER(IUnknown), "pActivationParams"),
            (["out", "retval"], POINTER(POINTER(IUnknown)), "ppInterface"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "OpenPropertyStore",
            (["in"], ctypes.c_uint, "stgmAccess"),
            (["out", "retval"], POINTER(POINTER(IUnknown)), "ppProperties"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetId",
            (["out", "retval"], POINTER(ctypes.c_wchar_p), "ppstrId"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetState",
            (["out", "retval"], POINTER(ctypes.c_uint), "pdwState"),
        ),
    ]


class IMMDeviceCollection(IUnknown):
    """Represents a collection of audio devices.

    Source: mmdeviceapi.h (Windows SDK)
    Reference: https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nn-mmdeviceapi-immdevicecollection
    """

    _iid_ = GUID("{0BD7A1BE-7A1A-44DB-8397-CC539238725E}")
    _methods_: ClassVar = [
        COMMETHOD(
            [],
            HRESULT,
            "GetCount",
            (["out", "retval"], POINTER(ctypes.c_uint), "pcDevices"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "Item",
            (["in"], ctypes.c_uint, "nDevice"),
            (["out", "retval"], POINTER(POINTER(IMMDevice)), "ppDevice"),
        ),
    ]


class IMMDeviceEnumerator(IUnknown):
    """Provides methods for enumerating audio devices.

    Source: mmdeviceapi.h (Windows SDK)
    Reference: https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nn-mmdeviceapi-immdeviceenumerator
    """

    _iid_ = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
    _methods_: ClassVar = [
        COMMETHOD(
            [],
            HRESULT,
            "EnumAudioEndpoints",
            (["in"], ctypes.c_int, "dataFlow"),
            (["in"], ctypes.c_uint, "dwStateMask"),
            (["out", "retval"], POINTER(POINTER(IMMDeviceCollection)), "ppDevices"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetDefaultAudioEndpoint",
            (["in"], ctypes.c_int, "dataFlow"),
            (["in"], ctypes.c_int, "role"),
            (["out", "retval"], POINTER(POINTER(IMMDevice)), "ppEndpoint"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetDevice",
            (["in"], BSTR, "pwstrId"),
            (["out", "retval"], POINTER(POINTER(IMMDevice)), "ppDevice"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "RegisterEndpointNotificationCallback",
            (["in"], POINTER(IUnknown), "pClient"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "UnregisterEndpointNotificationCallback",
            (["in"], POINTER(IUnknown), "pClient"),
        ),
    ]


class IPolicyConfig(IUnknown):
    """Undocumented interface for managing audio device policies.

    Source: Reverse engineered. Matches CLSID_PolicyConfig.
    Note: Microsoft does not publish this interface. It is widely used in
    community tools to switch audio devices programmatically.
    """

    _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
    _methods_: ClassVar = [
        COMMETHOD(
            [],
            HRESULT,
            "GetMixFormat",
            (["in"], ctypes.c_wchar_p, "pszDeviceName"),
            (["out"], ctypes.POINTER(WAVEFORMATEX), "ppFormat"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetDeviceFormat",
            (["in"], ctypes.c_wchar_p, "pszDeviceName"),
            (["in"], ctypes.c_int, "bDefault"),
            (["out"], ctypes.POINTER(WAVEFORMATEX), "ppFormat"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "ResetDeviceFormat",
            (["in"], ctypes.c_wchar_p, "pszDeviceName"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetDeviceFormat",
            (["in"], ctypes.c_wchar_p, "pszDeviceName"),
            (["in"], ctypes.POINTER(WAVEFORMATEX), "pEndpointFormat"),
            (["in"], ctypes.POINTER(WAVEFORMATEX), "pMixFormat"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetProcessingPeriod",
            (["in"], ctypes.c_wchar_p, "pszDeviceName"),
            (["in"], ctypes.c_int, "bDefault"),
            (["out"], ctypes.POINTER(ctypes.c_longlong), "pmftDefaultPeriod"),
            (["out"], ctypes.POINTER(ctypes.c_longlong), "pmftMinimumPeriod"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetProcessingPeriod",
            (["in"], ctypes.c_wchar_p, "pszDeviceName"),
            (["in"], ctypes.POINTER(ctypes.c_longlong), "pmftPeriod"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetShareMode",
            (["in"], ctypes.c_wchar_p, "pszDeviceName"),
            (["out"], ctypes.POINTER(ctypes.c_int), "pMode"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetShareMode",
            (["in"], ctypes.c_wchar_p, "pszDeviceName"),
            (["in"], ctypes.c_int, "mode"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetPropertyValue",
            (["in"], ctypes.c_wchar_p, "pszDeviceName"),
            (["in"], ctypes.POINTER(PROPERTYKEY), "pKey"),
            (["out"], ctypes.POINTER(PROPVARIANT), "pValue"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetPropertyValue",
            (["in"], ctypes.c_wchar_p, "pszDeviceName"),
            (["in"], ctypes.POINTER(PROPERTYKEY), "pKey"),
            (["in"], ctypes.POINTER(PROPVARIANT), "pValue"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetDefaultEndpoint",
            (["in"], ctypes.c_wchar_p, "wszDeviceId"),
            (["in"], ctypes.c_int, "role"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetEndpointVisibility",
            (["in"], ctypes.c_wchar_p, "wszDeviceId"),
            (["in"], ctypes.c_int, "bVisible"),
        ),
    ]


class IPropertyStore(IUnknown):
    """Interface for reading and writing properties.

    Source: propsys.h (Windows SDK)
    Reference: https://learn.microsoft.com/en-us/windows/win32/api/propsys/nn-propsys-ipropertystore
    """

    _iid_ = GUID("{886d8eeb-8cf2-4446-8d02-cdba1dbdcf99}")
    _methods_: ClassVar = [
        COMMETHOD(
            [],
            HRESULT,
            "GetCount",
            (["out", "retval"], POINTER(ctypes.c_uint), "cProps"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetAt",
            (["in"], ctypes.c_uint, "iProp"),
            (["out", "retval"], POINTER(PROPERTYKEY), "pkey"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetValue",
            (["in"], POINTER(PROPERTYKEY), "key"),
            (["out", "retval"], POINTER(PROPVARIANT), "pv"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "SetValue",
            (["in"], POINTER(PROPERTYKEY), "key"),
            (["in"], POINTER(PROPVARIANT), "propvar"),
        ),
        COMMETHOD([], HRESULT, "Commit"),
    ]


# PKEY_Device_FriendlyName
# Source: functiondiscoverykeys_devpkey.h
PKEY_Device_FriendlyName = PROPERTYKEY(
    GUID("{A45C254E-DF1C-4EFD-8020-67D146A850E0}"), 14
)


class IAudioMeterInformation(IUnknown):
    """Represents a peak meter on an audio device.

    Source: endpointvolume.h (Windows SDK)
    Reference: https://learn.microsoft.com/en-us/windows/win32/api/endpointvolume/nn-endpointvolume-iaudiometerinformation
    """

    _iid_ = GUID("{C02216F6-8C67-4B5B-9D00-D008E73E0064}")
    _methods_: ClassVar = [
        COMMETHOD(
            [],
            HRESULT,
            "GetPeakValue",
            (["out", "retval"], POINTER(ctypes.c_float), "pfPeak"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetMeteringChannelCount",
            (["out", "retval"], POINTER(ctypes.c_uint), "pnChannelCount"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetChannelsPeakValues",
            (["in"], ctypes.c_uint, "u32ChannelCount"),
            (["out"], POINTER(ctypes.c_float), "afPeakValues"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "QueryHardwareSupport",
            (["out", "retval"], POINTER(ctypes.c_uint), "pdwHardwareSupportMask"),
        ),
    ]


class IAudioClient(IUnknown):
    """Enables a client to create and initialize an audio stream.

    Source: audioclient.h (Windows SDK)
    Reference: https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nn-audioclient-iaudioclient
    """

    _iid_ = GUID("{1CB9AD4C-DBFA-4c32-B178-C2F568A703B2}")
    _methods_: ClassVar = [
        COMMETHOD(
            [],
            HRESULT,
            "Initialize",
            (["in"], ctypes.c_int, "ShareMode"),
            (["in"], ctypes.c_uint, "StreamFlags"),
            (["in"], ctypes.c_longlong, "hnsBufferDuration"),
            (["in"], ctypes.c_longlong, "hnsPeriodicity"),
            (["in"], POINTER(WAVEFORMATEX), "pFormat"),
            (["in"], POINTER(GUID), "AudioSessionGuid"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetBufferSize",
            (["out", "retval"], POINTER(ctypes.c_uint), "pNumBufferFrames"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetStreamLatency",
            (["out", "retval"], POINTER(ctypes.c_longlong), "phnsLatency"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetCurrentPadding",
            (["out", "retval"], POINTER(ctypes.c_uint), "pNumPaddingFrames"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "IsFormatSupported",
            (["in"], ctypes.c_int, "ShareMode"),
            (["in"], POINTER(WAVEFORMATEX), "pFormat"),
            (["out", "optional"], POINTER(POINTER(WAVEFORMATEX)), "ppClosestMatch"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetMixFormat",
            (["out", "retval"], POINTER(POINTER(WAVEFORMATEX)), "ppDeviceFormat"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetDevicePeriod",
            (["out", "optional"], POINTER(ctypes.c_longlong), "phnsDefaultPeriod"),
            (["out", "optional"], POINTER(ctypes.c_longlong), "phnsMinimumPeriod"),
        ),
        COMMETHOD([], HRESULT, "Start"),
        COMMETHOD([], HRESULT, "Stop"),
        COMMETHOD([], HRESULT, "Reset"),
        COMMETHOD(
            [],
            HRESULT,
            "SetEventHandle",
            (["in"], ctypes.c_void_p, "eventHandle"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetService",
            (["in"], POINTER(GUID), "riid"),
            (["out", "retval"], POINTER(POINTER(IUnknown)), "ppv"),
        ),
    ]


class IMMNotificationClient(IUnknown):
    """Interface for receiving audio device notifications.

    Source: mmdeviceapi.h (Windows SDK)
    Reference: https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nn-mmdeviceapi-immnotificationclient
    """

    _iid_ = GUID("{7991EEC9-7E89-4D85-8390-6C703CEC60C0}")
    _methods_: ClassVar = [
        COMMETHOD(
            [],
            HRESULT,
            "OnDeviceStateChanged",
            (["in"], ctypes.c_wchar_p, "pwstrDeviceId"),
            (["in"], ctypes.c_uint, "dwNewState"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "OnDeviceAdded",
            (["in"], ctypes.c_wchar_p, "pwstrDeviceId"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "OnDeviceRemoved",
            (["in"], ctypes.c_wchar_p, "pwstrDeviceId"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "OnDefaultDeviceChanged",
            (["in"], ctypes.c_int, "flow"),
            (["in"], ctypes.c_int, "role"),
            (["in"], ctypes.c_wchar_p, "pwstrDefaultDeviceId"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "OnPropertyValueChanged",
            (["in"], ctypes.c_wchar_p, "pwstrDeviceId"),
            (["in"], PROPERTYKEY, "key"),
        ),
    ]
