import sys
import os
import gc
import warnings
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QDialog
from PySide6.QtGui import QIcon, QAction

# Suppress warnings (e.g. pycaw COM errors)
warnings.simplefilter("ignore", UserWarning)

from .core import signals, audio, CONFIG_FILE
from .utils import NativeKeyboardHook, is_system_light_theme, get_idle_duration, set_default_device
from pycaw.pycaw import AudioUtilities
from .gui import ThemeListener, DeviceSelectionDialog, SettingsDialog
from .overlay import MetroOSD, StatusOverlay
from PySide6.QtCore import QTimer

# --- CONFIGURATION ---
VERSION = "2.0.0"

# Paths to SVG icons
if getattr(sys, 'frozen', False):
    # Running as compiled EXE
    BASE_DIR = sys._MEIPASS
    ASSETS_DIR = os.path.join(BASE_DIR, "MicMute", "assets")
else:
    # Running from source
    BASE_DIR = os.path.dirname(__file__)
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")

SVG_WHITE_UNMUTED = os.path.join(ASSETS_DIR, "mic_white.svg")
SVG_WHITE_MUTED = os.path.join(ASSETS_DIR, "mic_muted_white.svg")
SVG_BLACK_UNMUTED = os.path.join(ASSETS_DIR, "mic_black.svg")
SVG_BLACK_MUTED = os.path.join(ASSETS_DIR, "mic_muted_black.svg")

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if not audio.find_device():
        print("Warning: No device initially found.")

    # Load Icons
    icon_white_unmuted = QIcon(SVG_WHITE_UNMUTED)
    icon_white_muted = QIcon(SVG_WHITE_MUTED)
    icon_black_unmuted = QIcon(SVG_BLACK_UNMUTED)
    icon_black_muted = QIcon(SVG_BLACK_MUTED)

    tray = QSystemTrayIcon()
    current_mute_state = audio.get_mute_state()
    is_light_theme = is_system_light_theme()
    
    # OSD Initialization
    # We use white icons for the OSD as it has a dark background
    osd = MetroOSD(SVG_WHITE_UNMUTED, SVG_WHITE_MUTED)
    osd.set_config(audio.osd_config)
    
    # Persistent Overlay Initialization
    overlay = StatusOverlay(SVG_WHITE_UNMUTED, SVG_WHITE_MUTED)
    overlay.set_config(audio.persistent_overlay)
    overlay.set_target_device(audio.device_id)
    overlay.config_changed.connect(audio.update_persistent_overlay)
    
    def get_current_icon(muted, light_theme):
        if light_theme: return icon_black_muted if muted else icon_black_unmuted
        else: return icon_white_muted if muted else icon_white_unmuted

    tray.setIcon(get_current_icon(current_mute_state, is_light_theme))
    tray.setToolTip(f"Mic Mute v{VERSION}")
    
    # Listeners
    theme_listener = ThemeListener()
    kb_hook = NativeKeyboardHook(signals)
    kb_hook.update_config(audio.hotkey_config)
    kb_hook.install()
    
    # Menu Functions
    # Dialog Instances
    dialogs = {'settings': None}

    def populate_devices_menu():
        submenu_devices.clear()
        
        try:
            # Get All Devices
            all_devices_raw = AudioUtilities.GetAllDevices()
            enumerator = AudioUtilities.GetDeviceEnumerator()
            collection = enumerator.EnumAudioEndpoints(1, 1) # eCapture, eAll
            count = collection.GetCount()
            capture_ids = set()
            for i in range(count):
                dev = collection.Item(i)
                capture_ids.add(dev.GetId())
            
            # Filter and Sort
            devices = []
            for dev in all_devices_raw:
                if dev.id in capture_ids:
                    devices.append(dev)
            
            # Current Master ID
            current_id = audio.device_id
            
            for dev in devices:
                name = dev.FriendlyName
                dev_id = dev.id
                
                action = QAction(name, menu)
                action.setCheckable(True)
                action.setChecked(dev_id == current_id)
                
                # Handler
                def on_triggered(checked, d_id=dev_id):
                    if set_default_device(d_id):
                        if audio.set_device_by_id(d_id):
                            tray.showMessage("Success", f"Switched to: {name}", QSystemTrayIcon.Information, 2000)
                            overlay.set_target_device(d_id)
                        else:
                            tray.showMessage("Error", "Failed to set application device.", QSystemTrayIcon.Warning, 2000)
                    else:
                        tray.showMessage("Error", "Failed to set Windows default.", QSystemTrayIcon.Warning, 2000)
                
                action.triggered.connect(lambda checked, d_id=dev_id: on_triggered(checked, d_id))
                submenu_devices.addAction(action)
                
        except Exception as e:
            print(f"Error populating menu: {e}")
            error_action = QAction("Error loading devices", menu)
            error_action.setEnabled(False)
            submenu_devices.addAction(error_action)

    def show_settings_dialog():
        try:
            if dialogs['settings'] and dialogs['settings'].isVisible():
                dialogs['settings'].activateWindow()
                dialogs['settings'].raise_()
                return
        except RuntimeError:
            # Object deleted but reference remains
            dialogs['settings'] = None

        dialog = SettingsDialog(audio, kb_hook)
        dialogs['settings'] = dialog
        
        def on_settings_finished(result):
            if result == QDialog.Accepted:
                # Update OSD config after settings close
                osd.set_config(audio.osd_config)
                overlay.set_config(audio.persistent_overlay)
                overlay.set_target_device(audio.device_id)
            dialogs['settings'] = None
            gc.collect()

        dialog.finished.connect(on_settings_finished)
        dialog.show()

    def toggle_beep_setting(checked):
        audio.set_beep_enabled(checked)

    menu = QMenu()
    
    # Select Device Submenu
    submenu_devices = QMenu("Select Microphone", menu)
    submenu_devices.aboutToShow.connect(populate_devices_menu)
    menu.addMenu(submenu_devices)
    
    menu.addSeparator()
    
    # Beep Toggle
    action_beep = QAction("Play Beep Sounds")
    action_beep.setCheckable(True)
    action_beep.setChecked(audio.beep_enabled)
    action_beep.triggered.connect(toggle_beep_setting)
    menu.addAction(action_beep)
    
    # Settings
    action_settings = QAction("Settings")
    action_settings.triggered.connect(show_settings_dialog)
    menu.addAction(action_settings)
    
    menu.addSeparator()
    
    # Exit
    action_exit = QAction("Exit")
    action_exit.triggered.connect(app.quit)
    menu.addAction(action_exit)
    
    tray.setContextMenu(menu)
    tray.show()

    # Updates
    def update_tray_state(is_muted=None):
        nonlocal current_mute_state, is_light_theme
        if is_muted is not None: current_mute_state = is_muted
        new_theme = is_system_light_theme()
        if is_muted is not None or new_theme != is_light_theme:
            is_light_theme = new_theme
            tray.setIcon(get_current_icon(current_mute_state, is_light_theme))
            tray.setToolTip(f"Mic Mute v{VERSION} - {'MUTED' if current_mute_state else 'UNMUTED'}")
        
        # Trigger OSD if muted state changed
        if is_muted is not None:
            if audio.osd_config.get('enabled', False):
                osd.show_osd(is_muted)
            overlay.update_status(is_muted)

    signals.update_icon.connect(lambda m: update_tray_state(is_muted=m))
    signals.theme_changed.connect(lambda: update_tray_state(is_muted=None))
    signals.toggle_mute.connect(audio.toggle_mute)
    signals.set_mute.connect(audio.set_mute_state)
    signals.exit_app.connect(app.quit)

    # AFK Timer
    afk_timer = QTimer()
    def check_afk():
        if not audio.afk_config.get('enabled', False):
            return
        
        idle_time = get_idle_duration()
        timeout = audio.afk_config.get('timeout', 60)
        
        if idle_time >= timeout:
            # Only mute if not already muted
            if not audio.get_mute_state():
                print(f"AFK Detected ({idle_time:.1f}s). Muting...")
                audio.toggle_mute()
                # Optional: Show notification?
                # tray.showMessage("AFK Mute", "Microphone muted due to inactivity.", QSystemTrayIcon.Information, 2000)

    afk_timer.timeout.connect(check_afk)
    afk_timer.start(1000) # Check every 1 second

    print(f"\n{'='*50}")
    print(f"  Microphone Mute Toggle v{VERSION} (Refactored)")
    print(f"  Mode: Non-Admin | Native Hooks | Fully Configurable")
    print(f"{'='*50}")
    print("✓ Ready! Use tray icon to configure.")

    try:
        sys.exit(app.exec())
    finally:
        kb_hook.uninstall()

if __name__ == "__main__":
    main()
