import sys
import os
import ctypes
import winreg
from ctypes import wintypes, POINTER, c_void_p, c_int, c_long, c_longlong, Structure, sizeof
from PySide6.QtCore import QTimer, QObject, Signal

# --- PATH HELPERS ---
def get_internal_asset(filename):
    """
    Resolves the path to an internal bundled asset.
    Handles both frozen (PyInstaller) and source modes.
    
    Args:
        filename (str): Name of the asset file (e.g., 'mute.wav').
        
    Returns:
        str: Absolute path to the asset.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        base_dir = sys._MEIPASS
        assets_dir = os.path.join(base_dir, "MicMute", "assets")
    else:
        # Running from source
        base_dir = os.path.dirname(__file__)
        assets_dir = os.path.join(base_dir, "assets")
    
    return os.path.join(assets_dir, filename)

def get_external_sound_dir():
    """
    Returns the path to the external user sounds directory.
    Creates the directory if it does not exist.
    
    Returns:
        str: Absolute path to 'micmute_sounds' directory.
    """
    # Next to the executable or script
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        # Go up two levels from src/MicMute/utils.py to root
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        
    sound_dir = os.path.join(base_dir, "micmute_sounds")
    os.makedirs(sound_dir, exist_ok=True)
    return sound_dir

# --- WIN32 CONSTANTS & TYPES ---
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
# Left Alt
VK_LMENU = 0xA4
# Right Alt
VK_RMENU = 0xA5

class KBDLLHOOKSTRUCT(ctypes.Structure):
    """
    Structure for low-level keyboard hook events.
    """
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulong)
    ]

class LASTINPUTINFO(Structure):
    """
    Structure for tracking system idle time.
    """
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
    """
    Checks if the Windows system theme is set to Light mode.
    
    Returns:
        bool: True if Light theme is active, False otherwise.
    """
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
import queue

def set_high_priority():
    """Sets the process priority to High to prevent hook timeouts during high load."""
    try:
        import psutil
        p = psutil.Process()
        p.nice(psutil.HIGH_PRIORITY_CLASS)
        print("Process priority set to HIGH.")
    except ImportError:
        # Fallback to ctypes
        try:
            kernel32 = ctypes.windll.kernel32
            # HIGH_PRIORITY_CLASS = 0x00000080
            # GetCurrentProcess = -1
            kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), 0x00000080)
            print("Process priority set to HIGH (via ctypes).")
        except Exception as e:
            print(f"Failed to set process priority: {e}")
    except Exception as e:
        print(f"Failed to set process priority: {e}")

# --- NATIVE KEYBOARD HOOK ---
class NativeKeyboardHook:
    """
    Manages a low-level keyboard hook to intercept global hotkeys.
    """
    def __init__(self, signals):
        """
        Initializes the keyboard hook.
        
        Args:
            signals (MuteSignals): The signals object to emit events to.
        """
        self.signals = signals
        self.hook_id = None
        self.hook_proc = HOOKPROC(self._hook_callback)
        self.l_alt_down = False
        self.r_alt_down = False
        self.recording_mode = False
        
        # Optimized config attributes
        self.mode = 'toggle'
        self.toggle_vk = 0xB3
        self.mute_vk = 0
        self.unmute_vk = 0
        self.is_collision = False
        
        # Event Queue for thread-safe, fast communication
        self.event_queue = queue.SimpleQueue()
        
    def update_config(self, full_config):
        """Updates the hook with the full hotkey configuration dictionary."""
        self.mode = full_config.get('mode', 'toggle')
        self.toggle_vk = full_config.get('toggle', {}).get('vk', 0)
        self.mute_vk = full_config.get('mute', {}).get('vk', 0)
        self.unmute_vk = full_config.get('unmute', {}).get('vk', 0)
        
        # Pre-calculate collision logic
        self.is_collision = (self.mode == 'separate' and 
                           self.mute_vk == self.unmute_vk and 
                           self.mute_vk != 0)
        
    def set_target_vk(self, vk):
        """
        Sets the target virtual key code for the toggle action.
        
        Args:
            vk (int): The virtual key code.
        """
        # Legacy support / Fallback
        self.toggle_vk = vk

    def start_recording(self):
        """
        Enables key recording mode to capture the next key press.
        """
        self.recording_mode = True

    def stop_recording(self):
        """
        Disables key recording mode.
        """
        self.recording_mode = False

    def install(self):
        """
        Installs the low-level keyboard hook.
        """
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
        """
        Removes the low-level keyboard hook.
        """
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
                # Consume event
                return 1

            # Hotkey Logic
            # 1. Toggle Key (Always active if mode is toggle, OR if collision in separate mode)
            if (self.mode == 'toggle' and vk == self.toggle_vk) or \
               (self.is_collision and vk == self.mute_vk):
                if is_down:
                    self.event_queue.put('toggle')
                    return 1
                return 1

            # 2. Separate Keys (Only if no collision)
            if self.mode == 'separate' and not self.is_collision:
                if vk == self.mute_vk:
                    if is_down:
                        self.event_queue.put('mute')
                        return 1
                    return 1
                elif vk == self.unmute_vk:
                    if is_down:
                        self.event_queue.put('unmute')
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
            self.event_queue.put('toggle')
            self.l_alt_down = False
            self.r_alt_down = False

# --- MESSAGE LOOP & THREADING ---
import threading

class HookThread(threading.Thread):
    """
    Dedicated thread for running the keyboard hook message loop.
    """
    def __init__(self, signals, config):
        """
        Initializes the hook thread.
        
        Args:
            signals (MuteSignals): Signals object.
            config (dict): Initial hotkey configuration.
        """
        super().__init__(daemon=True)
        self.signals = signals
        self.config = config
        self.hook = None
        self.thread_id = None
        self.ready_event = threading.Event()

    def run(self):
        """
        Runs the thread, installing the hook and starting the message pump.
        """
        self.thread_id = kernel32.GetCurrentThreadId()
        self.hook = NativeKeyboardHook(self.signals)
        self.hook.update_config(self.config)
        self.hook.install()
        self.ready_event.set()

        # Message Pump
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        self.hook.uninstall()

    def stop(self):
        """
        Stops the thread and uninstalls the hook.
        """
        if self.thread_id:
            # WM_QUIT
            user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
            self.join(1.0)

    def update_config(self, config):
        """
        Updates the hook configuration safely.
        
        Args:
            config (dict): New configuration.
        """
        if self.hook:
            self.hook.update_config(config)

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
        IPropertyStore, PKEY_Device_FriendlyName, IAudioClient, IMMNotificationClient,
        eRender, eConsole, eMultimedia, eCommunications
    )
    from comtypes import client, GUID, COMObject

    class DeviceChangeListener(COMObject):
        """
        COM Object for receiving audio device notifications.
        """
        _com_interfaces_ = [IMMNotificationClient]

        def __init__(self, callback):
            """
            Initializes the listener.
            
            Args:
                callback (callable): Function to call on default device change.
            """
            super().__init__()
            self.callback = callback

        def OnDeviceStateChanged(self, pwstrDeviceId, dwNewState):
            pass

        def OnDeviceAdded(self, pwstrDeviceId):
            pass

        def OnDeviceRemoved(self, pwstrDeviceId):
            pass

        def OnDefaultDeviceChanged(self, flow, role, pwstrDefaultDeviceId):
            """
            Callback when the default audio device changes.
            """
            # eConsole is usually the system default
            if flow == eCapture and role == eConsole:
                if self.callback:
                    self.callback(pwstrDefaultDeviceId)

        def OnPropertyValueChanged(self, pwstrDeviceId, key):
            pass

    def set_default_device(device_id):
        """
        Sets the system default audio device using undocumented PolicyConfig.
        
        Args:
            device_id (str): The ID of the device to set as default.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            policy_config = client.CreateObject(
                CLSID_PolicyConfig,
                interface=IPolicyConfig
            )
            # Role: 0=eConsole, 1=eMultimedia, 2=eCommunications
            # Console
            policy_config.SetDefaultEndpoint(device_id, 0)
            # Multimedia
            policy_config.SetDefaultEndpoint(device_id, 1)
            # Communications
            policy_config.SetDefaultEndpoint(device_id, 2)
            return True
        except Exception as e:
            print(f"Failed to set default device: {e}")
            return False

    def get_audio_devices():
        """
        Enumerates all active audio capture devices.
        
        Returns:
            list: List of dicts {'id': str, 'name': str}.
        """
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
                    # STGM_READ
                    props = device.OpenPropertyStore(0)
                    val = props.GetValue(PKEY_Device_FriendlyName)
                    # PROPVARIANT handling
                    # VT_LPWSTR
                    if val.vt == 31:
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
    
    def get_audio_devices():
        return []
    
    class DeviceChangeListener:
        def __init__(self, callback): pass
