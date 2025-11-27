import sys
import os
import gc
import warnings
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction

# Suppress warnings (e.g. pycaw COM errors)
warnings.simplefilter("ignore", UserWarning)

from .core import signals, audio, CONFIG_FILE
from .utils import NativeKeyboardHook, is_system_light_theme
from .gui import ThemeListener, DeviceSelectionDialog, BeepSettingsDialog, HotkeySettingsDialog

# --- CONFIGURATION ---
VERSION = "1.7.0"

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
    
    def get_current_icon(muted, light_theme):
        if light_theme: return icon_black_muted if muted else icon_black_unmuted
        else: return icon_white_muted if muted else icon_white_unmuted

    tray.setIcon(get_current_icon(current_mute_state, is_light_theme))
    tray.setToolTip(f"Mic Mute v{VERSION}")
    
    # Listeners
    theme_listener = ThemeListener()
    kb_hook = NativeKeyboardHook(signals)
    kb_hook.set_target_vk(audio.hotkey_config['vk'])
    kb_hook.install()
    
    # Menu
    def show_select_dialog():
        dialog = DeviceSelectionDialog()
        if dialog.exec():
            if dialog.selected_device_id:
                if audio.set_device_by_id(dialog.selected_device_id):
                    tray.showMessage("Success", "Microphone selected!", QSystemTrayIcon.Information, 2000)
                else:
                    tray.showMessage("Error", "Failed to connect.", QSystemTrayIcon.Warning, 2000)
        gc.collect()

    def show_beep_settings():
        dialog = BeepSettingsDialog(audio)
        dialog.exec()
        gc.collect()

    def show_hotkey_settings():
        dialog = HotkeySettingsDialog(audio, kb_hook)
        dialog.exec()
        gc.collect()

    def toggle_beep_setting(checked):
        audio.set_beep_enabled(checked)

    menu = QMenu()
    
    # Select Device
    action_select = QAction("Select Microphone...")
    action_select.triggered.connect(show_select_dialog)
    menu.addAction(action_select)
    
    menu.addSeparator()
    
    # Beep Toggle
    action_beep = QAction("Play Beep Sounds")
    action_beep.setCheckable(True)
    action_beep.setChecked(audio.beep_enabled)
    action_beep.triggered.connect(toggle_beep_setting)
    menu.addAction(action_beep)
    
    # Beep Settings
    action_beep_settings = QAction("Beep Settings...")
    action_beep_settings.triggered.connect(show_beep_settings)
    menu.addAction(action_beep_settings)
    
    # Hotkey Settings
    action_hotkey = QAction("Hotkey Settings...")
    action_hotkey.triggered.connect(show_hotkey_settings)
    menu.addAction(action_hotkey)
    
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

    signals.update_icon.connect(lambda m: update_tray_state(is_muted=m))
    signals.theme_changed.connect(lambda: update_tray_state(is_muted=None))
    signals.toggle_mute.connect(audio.toggle_mute)
    signals.exit_app.connect(app.quit)

    print(f"\n{'='*50}")
    print(f"  Microphone Mute Toggle v{VERSION} (Final)")
    print(f"  Mode: Non-Admin | Native Hooks | Fully Configurable")
    print(f"{'='*50}")
    print("✓ Ready! Use tray icon to configure.")

    try:
        sys.exit(app.exec())
    finally:
        kb_hook.uninstall()

if __name__ == "__main__":
    main()
