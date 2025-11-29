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
    from comtypes import client, GUID, IUnknown, COMMETHOD, HRESULT, POINTER
    import ctypes
    
    from .com_interfaces import (
        CLSID_MMDeviceEnumerator, CLSID_PolicyConfig, eCapture, DEVICE_STATE_ACTIVE, CLSCTX_ALL,
        WAVEFORMATEX, PROPERTYKEY, PROPVARIANT,
        IMMDevice, IMMDeviceCollection, IMMDeviceEnumerator, IPolicyConfig, IAudioMeterInformation,
        IPropertyStore, PKEY_Device_FriendlyName
    )
    from comtypes import client, GUID


    def set_default_device(device_id):
        try:
            policy_config = client.CreateObject(
                CLSID_PolicyConfig,
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

    def get_audio_devices():
        devices = []
        try:
            enumerator = client.CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
            collection = enumerator.EnumAudioEndpoints(eCapture, DEVICE_STATE_ACTIVE)
            count = collection.GetCount()
            for i in range(count):
                device = collection.Item(i)
                dev_id = device.GetId()
                name = "Unknown Device"
                try:
                    props = device.OpenPropertyStore(0) # STGM_READ
                    val = props.GetValue(PKEY_Device_FriendlyName)
                    # PROPVARIANT handling
                    if val.vt == 31: # VT_LPWSTR
                        # val.data is c_ulonglong * 2
                        ptr = val.data[0]
                        name = ctypes.cast(ptr, ctypes.c_wchar_p).value
                except Exception:
                    pass
                devices.append({'id': dev_id, 'name': name})
        except Exception as e:
            print(f"Error enumerating devices: {e}")
        return devices

except ImportError:
    def set_default_device(device_id):
        print("comtypes not found, cannot set default device.")
        return False
