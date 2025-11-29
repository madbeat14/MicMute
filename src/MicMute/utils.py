import ctypes
import winreg
from ctypes import wintypes, POINTER, c_void_p, c_int, c_long, c_longlong, Structure, sizeof
from PySide6.QtCore import QTimer, QObject, Signal

# --- WIN32 CONSTANTS & TYPES ---
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
VK_LMENU = 0xA4 # Left Alt
VK_RMENU = 0xA5 # Right Alt

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulong)
    ]

class LASTINPUTINFO(Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('dwTime', wintypes.DWORD),
    ]

# C types for hook
LRESULT = c_longlong if ctypes.sizeof(c_void_p) == 8 else c_long
HOOKPROC = ctypes.CFUNCTYPE(LRESULT, c_int, wintypes.WPARAM, POINTER(KBDLLHOOKSTRUCT))
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def is_system_light_theme():
    try:
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "SystemUsesLightTheme")
        key.Close()
        return value == 1
    except Exception:
        return False

def get_idle_duration():
    """Returns the number of seconds the system has been idle."""
    lastInputInfo = LASTINPUTINFO()
    lastInputInfo.cbSize = sizeof(lastInputInfo)
    if user32.GetLastInputInfo(ctypes.byref(lastInputInfo)):
        millis = kernel32.GetTickCount() - lastInputInfo.dwTime
        return millis / 1000.0
    return 0.0

# --- NATIVE KEYBOARD HOOK ---
class NativeKeyboardHook:
    def __init__(self, signals):
        self.signals = signals
        self.hook_id = None
        self.hook_proc = HOOKPROC(self._hook_callback)
        self.l_alt_down = False
        self.r_alt_down = False
        self.config = {
            'mode': 'toggle',
            'toggle': 0xB3,
            'mute': 0,
            'unmute': 0
        }
        self.recording_mode = False
        
    def update_config(self, full_config):
        """Updates the hook with the full hotkey configuration dictionary."""
        self.config['mode'] = full_config.get('mode', 'toggle')
        self.config['toggle'] = full_config.get('toggle', {}).get('vk', 0)
        self.config['mute'] = full_config.get('mute', {}).get('vk', 0)
        self.config['unmute'] = full_config.get('unmute', {}).get('vk', 0)
        
    def set_target_vk(self, vk):
        # Legacy support / Fallback
        self.config['toggle'] = vk

    def start_recording(self):
        self.recording_mode = True

    def stop_recording(self):
        self.recording_mode = False

    def install(self):
        h_mod = 0
        self.hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self.hook_proc,
            h_mod,
            0
        )
        if not self.hook_id:
            error_code = kernel32.GetLastError()
            print(f"Failed to install keyboard hook. Error Code: {error_code}")

    def uninstall(self):
        if self.hook_id:
            user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None

    def _hook_callback(self, nCode, wParam, lParam):
        if nCode >= 0:
            kb_struct = lParam.contents
            vk = kb_struct.vkCode
            event = wParam
            is_down = (event == WM_KEYDOWN or event == WM_SYSKEYDOWN)
            
            # Recording Mode
            if self.recording_mode and is_down:
                self.signals.key_recorded.emit(vk)
                return 1 # Consume event

            # Hotkey Logic
            mode = self.config['mode']
            
            # 1. Toggle Key (Always active if mode is toggle, OR if collision in separate mode)
            # Collision Logic: If separate mode but mute_vk == unmute_vk, treat as toggle
            is_collision = (mode == 'separate' and 
                          self.config['mute'] == self.config['unmute'] and 
                          self.config['mute'] != 0)
            
            if (mode == 'toggle' and vk == self.config['toggle']) or \
               (is_collision and vk == self.config['mute']):
                if is_down:
                    QTimer.singleShot(0, self.signals.toggle_mute.emit)
                    return 1
                return 1

            # 2. Separate Keys (Only if no collision)
            if mode == 'separate' and not is_collision:
                if vk == self.config['mute']:
                    if is_down:
                        QTimer.singleShot(0, lambda: self.signals.set_mute.emit(True))
                        return 1
                    return 1
                elif vk == self.config['unmute']:
                    if is_down:
                        QTimer.singleShot(0, lambda: self.signals.set_mute.emit(False))
                        return 1
                    return 1
                
            # Alt Logic (Hardcoded fallback/secondary)
            if vk == VK_LMENU:
                self.l_alt_down = is_down
                self._check_alts()
            elif vk == VK_RMENU:
                self.r_alt_down = is_down
                self._check_alts()
                
        return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

    def _check_alts(self):
        if self.l_alt_down and self.r_alt_down:
            QTimer.singleShot(0, self.signals.toggle_mute.emit)
            self.l_alt_down = False
            self.r_alt_down = False

# --- WINDOWS AUDIO POLICY CONFIG (Undocumented API) ---
try:
    import comtypes
    from comtypes import client
    from comtypes import GUID, IUnknown, COMMETHOD, HRESULT
    
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

    class IAudioMeterInformation(IUnknown):
        _iid_ = GUID("{C02216F6-8C67-4B5B-9D00-D008E73E0064}")
        _methods_ = [
            COMMETHOD([], HRESULT, 'GetPeakValue',
                      (['out'], POINTER(ctypes.c_float), 'pfPeak')),
            COMMETHOD([], HRESULT, 'GetMeteringChannelCount',
                      (['out'], POINTER(wintypes.DWORD), 'pnChannelCount')),
            COMMETHOD([], HRESULT, 'GetChannelsPeakValues',
                      (['in'], wintypes.DWORD, 'u32ChannelCount'),
                      (['out'], POINTER(ctypes.c_float), 'afPeakValues')),
            COMMETHOD([], HRESULT, 'QueryHardwareSupport',
                      (['out'], POINTER(wintypes.DWORD), 'pdwHardwareSupportMask')),
        ]

    def set_default_device(device_id):
        try:
            policy_config = client.CreateObject(
                GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}"),
                interface=IPolicyConfig
            )
            # Role: 0=eConsole, 1=eMultimedia, 2=eCommunications
            policy_config.SetDefaultEndpoint(device_id, 0) # Console
            policy_config.SetDefaultEndpoint(device_id, 1) # Multimedia
            policy_config.SetDefaultEndpoint(device_id, 2) # Communications
            return True
        except Exception as e:
            print(f"Failed to set default device: {e}")
            return False

except ImportError:
    def set_default_device(device_id):
        print("comtypes not found, cannot set default device.")
        return False
