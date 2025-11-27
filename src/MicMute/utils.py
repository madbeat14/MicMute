import ctypes
import winreg
from ctypes import wintypes, POINTER, c_void_p, c_int, c_long, c_longlong
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

# --- NATIVE KEYBOARD HOOK ---
class NativeKeyboardHook:
    def __init__(self, signals):
        self.signals = signals
        self.hook_id = None
        self.hook_proc = HOOKPROC(self._hook_callback)
        self.l_alt_down = False
        self.r_alt_down = False
        self.target_vk = 0xB3 # Default Media Play/Pause
        self.recording_mode = False
        
    def set_target_vk(self, vk):
        self.target_vk = vk

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
                # Ignore modifier keys alone if desired, but for now capture everything
                # except mouse clicks (which aren't keyboard events anyway)
                self.signals.key_recorded.emit(vk)
                return 1 # Consume event

            # Hotkey Logic
            if vk == self.target_vk:
                if is_down:
                    QTimer.singleShot(0, self.signals.toggle_mute.emit)
                    return 1 # Suppress
                return 1 # Suppress up event too
                
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
