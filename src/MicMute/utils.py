"""Utility functions and classes for MicMute.

This module provides helper functions for path resolution, Windows registry access,
keyboard hooks, COM interface management, and audio device operations.
"""

from __future__ import annotations

import ctypes
import gc
import os
import subprocess
import sys
import tempfile
import threading
import winreg
from collections.abc import Callable
from ctypes import wintypes, POINTER, c_void_p, c_int, c_long, c_longlong, Structure, sizeof
from pathlib import Path
from queue import SimpleQueue
from typing import Any, ClassVar, Protocol, TypeVar, runtime_checkable

from PySide6.QtCore import QObject, Signal

__all__ = [
    "get_internal_asset",
    "get_external_sound_dir",
    "get_run_on_startup",
    "set_run_on_startup",
    "is_system_light_theme",
    "get_idle_duration",
    "set_high_priority",
    "NativeKeyboardHook",
    "HookThread",
    "set_default_device",
    "get_audio_devices",
    "DeviceChangeListener",
    "WH_KEYBOARD_LL",
    "WM_KEYDOWN",
    "WM_KEYUP",
    "VK_LMENU",
    "VK_RMENU",
    "KBDLLHOOKSTRUCT",
    # COM Interface exports
    "CLSID_MMDeviceEnumerator",
    "CLSID_PolicyConfig",
    "IMMDeviceEnumerator",
    "IMMDevice",
    "IPolicyConfig",
    "IAudioMeterInformation",
    "IAudioClient",
    "IMMNotificationClient",
    "eCapture",
    "eConsole",
    "eMultimedia",
    "eCommunications",
    "eRender",
    "DEVICE_STATE_ACTIVE",
    "CLSCTX_ALL",
    "PKEY_Device_FriendlyName",
    "WAVEFORMATEX",
    "PROPERTYKEY",
    "PROPVARIANT",
]


# --- PATH HELPERS ---

def get_internal_asset(filename: str) -> Path:
    """Resolve the path to an internal bundled asset.

    Handles both frozen (PyInstaller) and source modes.

    Args:
        filename: Name of the asset file (e.g., 'mute.wav').

    Returns:
        Absolute path to the asset.
    """
    if getattr(sys, "frozen", False):
        # Running as compiled EXE
        base_dir = Path(sys._MEIPASS)
        assets_dir = base_dir / "MicMute" / "assets"
    else:
        # Running from source
        base_dir = Path(__file__).parent
        assets_dir = base_dir / "assets"

    return assets_dir / filename


def get_external_sound_dir() -> Path:
    """Return the path to the external user sounds directory.

    Returns:
        Absolute path to 'micmute_sounds' directory.
    """
    if getattr(sys, "frozen", False):
        # Running as compiled EXE - use user's AppData folder
        base_dir = Path.home() / "AppData" / "Local" / "MicMute"
    else:
        # Running from source - use project root
        base_dir = Path(__file__).parent.parent.parent

    return base_dir / "micmute_sounds"


# --- STARTUP HELPERS (Task Scheduler) ---

TASK_XML_TEMPLATE: str = r"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>{AUTHOR}</Author>
    <Description>Start MicMute at startup with High Priority</Description>
    <URI>\MicMuteStartup</URI>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>true</StopIfGoingOnBatteries>
    <AllowHardTerminate>false</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <Priority>0</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{EXE_PATH}</Command>
      <Arguments>{ARGUMENTS}</Arguments>
    </Exec>
  </Actions>
</Task>
"""


def get_run_on_startup() -> bool:
    """Check if the application is set to run on startup via Windows Task Scheduler.

    Returns:
        True if the task exists, False otherwise.
    """
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", "MicMuteStartup"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error checking startup status: {e}")
        return False


def set_run_on_startup(enable: bool) -> None:
    """Enable or disable running the application on startup using Windows Task Scheduler.

    Args:
        enable: True to enable, False to disable.

    Raises:
        RuntimeError: If schtasks fails (e.g., Access Denied and User declined UAC).
    """
    task_name = "MicMuteStartup"

    if enable:
        _create_startup_task(task_name)
    else:
        _delete_startup_task(task_name)


def _create_startup_task(task_name: str) -> None:
    """Create the startup task in Windows Task Scheduler.

    Args:
        task_name: Name of the task to create.

    Raises:
        RuntimeError: If task creation fails.
    """
    # Determine Executable Path and Arguments
    if getattr(sys, "frozen", False):
        exe_path = sys.executable
        arguments = ""
    else:
        exe_path = sys.executable
        if exe_path.endswith("python.exe"):
            pythonw = exe_path.replace("python.exe", "pythonw.exe")
            if Path(pythonw).exists():
                exe_path = pythonw
        script_path = Path(sys.argv[0]).resolve()
        arguments = f'"{script_path}"'

    author = os.getlogin()

    xml_content = TASK_XML_TEMPLATE.format(
        AUTHOR=author, EXE_PATH=exe_path, ARGUMENTS=arguments
    )

    fd, temp_path = tempfile.mkstemp(suffix=".xml")
    os.close(fd)

    try:
        Path(temp_path).write_text(xml_content, encoding="utf-16")
        _run_schtasks_create(task_name, temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def _run_schtasks_create(task_name: str, xml_path: str) -> None:
    """Execute schtasks to create the startup task.

    Args:
        task_name: Name of the task.
        xml_path: Path to the XML task definition.

    Raises:
        RuntimeError: If task creation fails.
    """
    cmd = ["schtasks", "/Create", "/TN", task_name, "/XML", xml_path, "/F"]
    result = subprocess.run(
        cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, check=False
    )

    if result.returncode != 0:
        err_msg = result.stderr.decode("cp1252", errors="ignore").strip()
        if "Access is denied" in err_msg or result.returncode == 5:
            _create_task_elevated(task_name, xml_path)
        else:
            raise RuntimeError(f"schtasks failed: {err_msg}")


def _create_task_elevated(task_name: str, xml_path: str) -> None:
    """Create task with UAC elevation via PowerShell.

    Args:
        task_name: Name of the task.
        xml_path: Path to the XML task definition.

    Raises:
        RuntimeError: If elevation fails or task is not created.
    """
    schtasks_args = f'/Create /TN "{task_name}" /XML "{xml_path}" /F'
    ps_cmd = [
        "powershell",
        "-Command",
        f"Start-Process schtasks -ArgumentList '{schtasks_args}' -Verb RunAs -Wait",
    ]

    ps_result = subprocess.run(
        ps_cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, check=False
    )

    if ps_result.returncode != 0:
        raise RuntimeError("UAC Elevation failed or cancelled.")

    if not get_run_on_startup():
        raise RuntimeError("Task creation failed even after UAC prompt.")


def _delete_startup_task(task_name: str) -> None:
    """Delete the startup task from Windows Task Scheduler.

    Args:
        task_name: Name of the task to delete.
    """
    cmd = ["schtasks", "/Delete", "/TN", task_name, "/F"]
    result = subprocess.run(
        cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, check=False
    )

    if result.returncode != 0:
        err_msg = result.stderr.decode("cp1252", errors="ignore").strip()
        if "Access is denied" in err_msg or result.returncode == 5:
            _delete_task_elevated(task_name)


def _delete_task_elevated(task_name: str) -> None:
    """Delete task with UAC elevation via PowerShell.

    Args:
        task_name: Name of the task.
    """
    schtasks_args = f'/Delete /TN "{task_name}" /F'
    ps_cmd = [
        "powershell",
        "-Command",
        f"Start-Process schtasks -ArgumentList '{schtasks_args}' -Verb RunAs -Wait",
    ]
    subprocess.run(ps_cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)


# --- KEYBOARD HOOK CONSTANTS ---

WH_KEYBOARD_LL: int = 13
WM_KEYDOWN: int = 0x0100
WM_KEYUP: int = 0x0101
WM_SYSKEYDOWN: int = 0x0104
WM_SYSKEYUP: int = 0x0105
VK_LMENU: int = 0xA4
VK_RMENU: int = 0xA5


class KBDLLHOOKSTRUCT(Structure):
    """Structure for low-level keyboard hook events."""

    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulong),
    ]


class LASTINPUTINFO(Structure):
    """Structure for tracking system idle time."""

    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwTime", wintypes.DWORD),
    ]


# C types for hook
LRESULT = c_longlong if sizeof(c_void_p) == 8 else c_long
HOOKPROC = ctypes.CFUNCTYPE(LRESULT, c_int, wintypes.WPARAM, POINTER(KBDLLHOOKSTRUCT))
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


# --- THEME AND IDLE DETECTION ---


def is_system_light_theme() -> bool:
    """Check if the Windows system theme is set to Light mode.

    Returns:
        True if Light theme is active, False otherwise.
    """
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "SystemUsesLightTheme")
            return value == 1
    except Exception:
        return False


def get_idle_duration() -> float:
    """Return the number of seconds the system has been idle.

    Returns:
        Idle time in seconds.
    """
    last_input = LASTINPUTINFO()
    last_input.cbSize = sizeof(last_input)
    if user32.GetLastInputInfo(ctypes.byref(last_input)):
        millis = kernel32.GetTickCount() - last_input.dwTime
        return millis / 1000.0
    return 0.0


def set_high_priority() -> None:
    """Set process priority to High to prevent hook timeouts during high load."""
    try:
        import psutil

        p = psutil.Process()
        p.nice(psutil.HIGH_PRIORITY_CLASS)
        print("Process priority set to HIGH.")
    except ImportError:
        _set_high_priority_ctypes()
    except Exception as e:
        print(f"Failed to set process priority: {e}")


def _set_high_priority_ctypes() -> None:
    """Set high priority using ctypes as fallback."""
    try:
        # HIGH_PRIORITY_CLASS = 0x00000080
        kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), 0x00000080)
        print("Process priority set to HIGH (via ctypes).")
    except Exception as e:
        print(f"Failed to set process priority: {e}")


# --- NATIVE KEYBOARD HOOK ---


class NativeKeyboardHook:
    """Manages a low-level keyboard hook to intercept global hotkeys."""

    def __init__(self, signals: QObject) -> None:
        """Initialize the keyboard hook.

        Args:
            signals: The signals object to emit events to.
        """
        self.signals = signals
        self.hook_id: int | None = None
        self.hook_proc = HOOKPROC(self._hook_callback)
        self.l_alt_down = False
        self.r_alt_down = False
        self.recording_mode = False

        # Optimized config attributes
        self.mode = "toggle"
        self.toggle_vk = 0xB3
        self.mute_vk = 0
        self.unmute_vk = 0
        self.is_collision = False

        # Event Queue for thread-safe, fast communication
        self.event_queue: SimpleQueue[str] = SimpleQueue()

    def update_config(self, full_config: dict[str, Any]) -> None:
        """Update the hook with the full hotkey configuration dictionary.

        Args:
            full_config: The hotkey configuration.
        """
        self.mode = full_config.get("mode", "toggle")
        self.toggle_vk = full_config.get("toggle", {}).get("vk", 0)
        self.mute_vk = full_config.get("mute", {}).get("vk", 0)
        self.unmute_vk = full_config.get("unmute", {}).get("vk", 0)

        # Pre-calculate collision logic
        self.is_collision = (
            self.mode == "separate"
            and self.mute_vk == self.unmute_vk
            and self.mute_vk != 0
        )

    def set_target_vk(self, vk: int) -> None:
        """Set the target virtual key code for the toggle action.

        Args:
            vk: The virtual key code.
        """
        self.toggle_vk = vk

    def start_recording(self) -> None:
        """Enable key recording mode to capture the next key press."""
        self.recording_mode = True

    def stop_recording(self) -> None:
        """Disable key recording mode."""
        self.recording_mode = False

    def install(self) -> None:
        """Install the low-level keyboard hook."""
        h_mod = 0
        self.hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self.hook_proc, h_mod, 0
        )
        if not self.hook_id:
            error_code = kernel32.GetLastError()
            print(f"Failed to install keyboard hook. Error Code: {error_code}")

    def uninstall(self) -> None:
        """Remove the low-level keyboard hook."""
        if self.hook_id:
            user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None

    def _hook_callback(
        self, n_code: int, w_param: wintypes.WPARAM, l_param: POINTER(KBDLLHOOKSTRUCT)
    ) -> LRESULT:
        """Callback function for keyboard events.

        Args:
            n_code: Hook code.
            w_param: Message identifier.
            l_param: Pointer to KBDLLHOOKSTRUCT.

        Returns:
            Result of CallNextHookEx or 1 to consume the event.
        """
        if n_code >= 0:
            kb_struct = l_param.contents
            vk = kb_struct.vkCode
            event = w_param
            is_down = event in (WM_KEYDOWN, WM_SYSKEYDOWN)

            # Recording Mode
            if self.recording_mode and is_down:
                self.signals.key_recorded.emit(vk)
                return 1

            # Hotkey Logic
            if (self.mode == "toggle" and vk == self.toggle_vk) or (
                self.is_collision and vk == self.mute_vk
            ):
                if is_down:
                    self.event_queue.put("toggle")
                return 1

            # Separate Keys (Only if no collision)
            if self.mode == "separate" and not self.is_collision:
                if vk == self.mute_vk:
                    if is_down:
                        self.event_queue.put("mute")
                    return 1
                elif vk == self.unmute_vk:
                    if is_down:
                        self.event_queue.put("unmute")
                    return 1

            # Alt Logic (Hardcoded fallback/secondary)
            if vk == VK_LMENU:
                self.l_alt_down = is_down
                self._check_alts()
            elif vk == VK_RMENU:
                self.r_alt_down = is_down
                self._check_alts()

        return user32.CallNextHookEx(self.hook_id, n_code, w_param, l_param)

    def _check_alts(self) -> None:
        """Check if both Alt keys are pressed simultaneously."""
        if self.l_alt_down and self.r_alt_down:
            self.event_queue.put("toggle")
            self.l_alt_down = False
            self.r_alt_down = False


class HookThread(threading.Thread):
    """Dedicated thread for running the keyboard hook message loop."""

    def __init__(self, signals: QObject, config: dict[str, Any]) -> None:
        """Initialize the hook thread.

        Args:
            signals: Signals object.
            config: Initial hotkey configuration.
        """
        super().__init__(daemon=True)
        self.signals = signals
        self.config = config
        self.hook: NativeKeyboardHook | None = None
        self.thread_id: int | None = None
        self.ready_event = threading.Event()

    def run(self) -> None:
        """Run the thread, installing the hook and starting the message pump."""
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

        if self.hook:
            self.hook.uninstall()

    def stop(self) -> None:
        """Stop the thread and uninstall the hook."""
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
            self.join(1.0)

    def update_config(self, config: dict[str, Any]) -> None:
        """Update the hook configuration safely.

        Args:
            config: New configuration.
        """
        if self.hook:
            self.hook.update_config(config)


# --- WINDOWS AUDIO POLICY CONFIG (Undocumented API) ---

try:
    import comtypes
    from comtypes import client, GUID, IUnknown, COMMETHOD, HRESULT, POINTER, COMObject
    from comtypes.client import CreateObject

    from .com_interfaces import (
        CLSID_MMDeviceEnumerator,
        CLSID_PolicyConfig,
        eCapture,
        DEVICE_STATE_ACTIVE,
        CLSCTX_ALL,
        WAVEFORMATEX,
        PROPERTYKEY,
        PROPVARIANT,
        IMMDevice,
        IMMDeviceCollection,
        IMMDeviceEnumerator,
        IPolicyConfig,
        IAudioMeterInformation,
        IPropertyStore,
        PKEY_Device_FriendlyName,
        IAudioClient,
        IMMNotificationClient,
        eRender,
        eConsole,
        eMultimedia,
        eCommunications,
    )

    HAS_COM: bool = True

    class DeviceChangeListener(COMObject):
        """COM Object for receiving audio device notifications."""

        _com_interfaces_ = [IMMNotificationClient]

        def __init__(self, callback: Callable[[str], None]) -> None:
            """Initialize the listener.

            Args:
                callback: Function to call on default device change.
            """
            super().__init__()
            self.callback = callback

        def OnDeviceStateChanged(
            self, pwstrDeviceId: str, dwNewState: int
        ) -> None:
            """Handle device state change."""
            pass

        def OnDeviceAdded(self, pwstrDeviceId: str) -> None:
            """Handle device added."""
            pass

        def OnDeviceRemoved(self, pwstrDeviceId: str) -> None:
            """Handle device removed."""
            pass

        def OnDefaultDeviceChanged(
            self, flow: int, role: int, pwstrDefaultDeviceId: str
        ) -> None:
            """Handle default device change.

            Args:
                flow: Data flow direction.
                role: Device role.
                pwstrDefaultDeviceId: ID of the new default device.
            """
            if flow == eCapture and role == eConsole:
                if self.callback:
                    self.callback(pwstrDefaultDeviceId)

        def OnPropertyValueChanged(
            self, pwstrDeviceId: str, key: PROPERTYKEY
        ) -> None:
            """Handle property value change."""
            pass

    def set_default_device(device_id: str) -> bool:
        """Set the system default audio device using undocumented PolicyConfig.

        Args:
            device_id: The ID of the device to set as default.

        Returns:
            True if successful, False otherwise.
        """
        try:
            policy_config = CreateObject(CLSID_PolicyConfig, interface=IPolicyConfig)
            # Role: 0=eConsole, 1=eMultimedia, 2=eCommunications
            policy_config.SetDefaultEndpoint(device_id, 0)  # Console
            policy_config.SetDefaultEndpoint(device_id, 1)  # Multimedia
            policy_config.SetDefaultEndpoint(device_id, 2)  # Communications
            return True
        except Exception as e:
            print(f"Failed to set default device: {e}")
            return False

    def get_audio_devices() -> list[dict[str, str]]:
        """Enumerate all active audio capture devices.

        Returns:
            List of dicts with 'id' and 'name' keys.
        """
        devices: list[dict[str, str]] = []
        try:
            enumerator = CreateObject(
                CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator
            )
            collection = enumerator.EnumAudioEndpoints(
                eCapture, DEVICE_STATE_ACTIVE
            )
            count = collection.GetCount()
            for i in range(count):
                device = collection.Item(i)
                dev_id = device.GetId()
                name = "Unknown Device"
                try:
                    props = device.OpenPropertyStore(0)  # STGM_READ
                    val = props.GetValue(PKEY_Device_FriendlyName)
                    if val.vt == 31:  # VT_LPWSTR
                        ptr = val.data[0]
                        name = ctypes.cast(ptr, ctypes.c_wchar_p).value or name
                except Exception:
                    pass
                devices.append({"id": dev_id, "name": name})
        except Exception as e:
            print(f"Error enumerating devices: {e}")
        return devices

except ImportError:
    HAS_COM = False

    def set_default_device(device_id: str) -> bool:
        """Fallback when COM types are not available."""
        print("comtypes not found, cannot set default device.")
        return False

    def get_audio_devices() -> list[dict[str, str]]:
        """Fallback when COM types are not available."""
        return []

    class DeviceChangeListener:
        """Fallback device change listener."""

        def __init__(self, callback: Callable[[str], None]) -> None:
            """Initialize with no-op."""
            pass
