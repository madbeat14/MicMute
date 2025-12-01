import sys
import os
import gc
import warnings
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QDialog, QMessageBox
from PySide6.QtGui import QIcon, QAction, QDesktopServices
from PySide6.QtCore import QTimer, QUrl

# Suppress warnings (e.g. pycaw COM errors)
warnings.simplefilter("ignore", UserWarning)

from .core import signals, audio
from .config import CONFIG_FILE
from .utils import is_system_light_theme, get_idle_duration, set_default_device, set_high_priority, get_run_on_startup, set_run_on_startup
from pycaw.pycaw import AudioUtilities
from .gui import ThemeListener, SettingsDialog
from .overlay import MetroOSD, StatusOverlay
from .input_manager import InputManager

# --- CONFIGURATION ---
VERSION = "2.13.2"

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
    """
    Main entry point for the MicMute application.
    Initializes the Qt application, audio controller, tray icon, and background threads.
    """
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
    # overlay.set_target_device(audio.device_id) # Removed to allow config to control device
    overlay.config_changed.connect(audio.update_persistent_overlay)
    
    def get_current_icon(muted, light_theme):
        """
        Determines the appropriate icon based on mute state and theme.
        
        Args:
            muted (bool): Current mute state.
            light_theme (bool): True if system is in light mode.
            
        Returns:
            QIcon: The appropriate QIcon object.
        """
        if light_theme: return icon_black_muted if muted else icon_black_unmuted
        else: return icon_white_muted if muted else icon_white_unmuted

    tray.setIcon(get_current_icon(current_mute_state, is_light_theme))
    tray.setToolTip(f"MicMute v{VERSION} - {'MUTED' if current_mute_state else 'UNMUTED'}")
    
    # Listeners
    theme_listener = ThemeListener()
    
    # Input Manager (Hooks)
    input_manager = InputManager()
    input_manager.start()
    
    # Menu Functions
    # Dialog Instances
    dialogs = {'settings': None}

    def populate_devices_menu():
        """
        Populates the device selection submenu with available microphones.
        """
        submenu_devices.clear()
        
        try:
            # Get All Devices
            all_devices_raw = AudioUtilities.GetAllDevices()
            enumerator = AudioUtilities.GetDeviceEnumerator()
            # eCapture, eAll
            collection = enumerator.EnumAudioEndpoints(1, 1)
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
        """
        Displays the settings dialog, initializing it if necessary.
        """
        try:
            if dialogs['settings'] and dialogs['settings'].isVisible():
                dialogs['settings'].activateWindow()
                dialogs['settings'].raise_()
                return
        except RuntimeError:
            # Object deleted but reference remains
            dialogs['settings'] = None

        # Pass hook_thread instead of raw hook
        dialog = SettingsDialog(audio, input_manager.hook_thread)
        dialogs['settings'] = dialog
        
        def apply_updates():
            """Applies configuration changes to OSD and Overlay."""
            osd.set_config(audio.osd_config)
            overlay.set_config(audio.persistent_overlay)
            
            # Sync Tray Menu Checkboxes
            action_sound.setChecked(audio.beep_enabled)
            action_osd.setChecked(audio.osd_config.get('enabled', False))
            action_overlay.setChecked(audio.persistent_overlay.get('enabled', False))
        
        dialog.settings_applied.connect(apply_updates)
        
        def on_settings_finished(result):
            # Explicit Cleanup
            dialogs['settings'] = None
            # Schedule C++ deletion
            dialog.deleteLater()
            # Force Python GC
            gc.collect()

        dialog.finished.connect(on_settings_finished)
        dialog.show()

    # Toggle Handlers
    def toggle_beep_setting(checked):
        audio.set_beep_enabled(checked)

    def toggle_osd_setting(checked):
        # Update config and save
        new_config = audio.osd_config.copy()
        new_config['enabled'] = checked
        audio.update_osd_config(new_config)
        # Force OSD hide if disabled
        if not checked:
            osd.hide()

    def toggle_overlay_setting(checked):
        # Update config and save
        new_config = audio.persistent_overlay.copy()
        new_config['enabled'] = checked
        audio.update_persistent_overlay(new_config)
        # Overlay handles its own visibility in set_config
        overlay.set_config(new_config)

    menu = QMenu()
    
    # Select Device Submenu
    submenu_devices = QMenu("Select Microphone", menu)
    submenu_devices.aboutToShow.connect(populate_devices_menu)
    menu.addMenu(submenu_devices)
    
    menu.addSeparator()
    
    # Sound Toggle
    action_sound = QAction("Play Sound on Toggle")
    action_sound.setCheckable(True)
    action_sound.setChecked(audio.beep_enabled)
    action_sound.triggered.connect(toggle_beep_setting)
    menu.addAction(action_sound)
    
    # OSD Toggle
    action_osd = QAction("Enable OSD Notification")
    action_osd.setCheckable(True)
    action_osd.setChecked(audio.osd_config.get('enabled', False))
    action_osd.triggered.connect(toggle_osd_setting)
    menu.addAction(action_osd)
    
    # Overlay Toggle
    action_overlay = QAction("Show Persistent Overlay")
    action_overlay.setCheckable(True)
    action_overlay.setChecked(audio.persistent_overlay.get('enabled', False))
    action_overlay.triggered.connect(toggle_overlay_setting)
    menu.addAction(action_overlay)

    # Start on Boot Toggle
    action_startup = QAction("Start on Boot")
    action_startup.setCheckable(True)
    action_startup.setChecked(get_run_on_startup())
    
    def toggle_startup(checked):
        set_run_on_startup(checked)
        
    action_startup.triggered.connect(toggle_startup)
    menu.addAction(action_startup)
    
    menu.addSeparator()

    # Settings
    action_settings = QAction("Settings")
    action_settings.triggered.connect(show_settings_dialog)
    menu.addAction(action_settings)
    
    # Help
    action_help = QAction("Help")
    action_help.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/madbeat14/MicMute#readme")))
    menu.addAction(action_help)
    
    # About
    action_about = QAction("About")
    
    def show_about():
        QMessageBox.about(
            None,
            "About MicMute",
            f"<b>MicMute v{VERSION}</b><br><br>"
            "Author: madbeat14<br>"
            "A lightweight, non-intrusive microphone mute toggle application with native hooks and overlay."
        )
        
    action_about.triggered.connect(show_about)
    menu.addAction(action_about)
    
    menu.addSeparator()
    
    # Exit
    action_exit = QAction("Exit")
    action_exit.triggered.connect(app.quit)
    menu.addAction(action_exit)
    
    tray.setContextMenu(menu)
    tray.show()

    # Updates
    def update_tray_state(is_muted=None):
        """
        Updates the tray icon and tooltip based on the current state.
        
        Args:
            is_muted (bool, optional): The new mute state. If None, uses current state.
        """
        nonlocal current_mute_state, is_light_theme
        if is_muted is not None: current_mute_state = is_muted
        new_theme = is_system_light_theme()
        if is_muted is not None or new_theme != is_light_theme:
            is_light_theme = new_theme
            tray.setIcon(get_current_icon(current_mute_state, is_light_theme))
            tray.setToolTip(f"MicMute v{VERSION} - {'MUTED' if current_mute_state else 'UNMUTED'}")
        
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
    
    def on_device_changed(new_id):
        """
        Handles changes to the default audio device.
        
        Args:
            new_id (str): The ID of the new default device.
        """
        print(f"Default Device Changed: {new_id}")
        # Automatically switch to the new default device
        if audio.set_device_by_id(new_id):
            # Update Overlay target
            overlay.set_target_device(new_id)
            # Show notification
            tray.showMessage("Device Changed", "Switched to new default microphone.", QSystemTrayIcon.Information, 2000)
            
    signals.device_changed.connect(on_device_changed)

    def on_setting_changed(key, value):
        """
        Handles setting changes from other parts of the app (e.g. Settings Dialog).
        Updates tray menu checkmarks to match.
        """
        # Block signals to prevent feedback loop? 
        # Actually, QAction.setChecked emits triggered? No, usually toggled.
        # But our triggered handlers call audio.set_*, which emits setting_changed.
        # So we MUST block signals on the actions while setting them.
        
        if key == 'beep_enabled':
            action_sound.blockSignals(True)
            action_sound.setChecked(value)
            action_sound.blockSignals(False)
        elif key == 'osd':
            action_osd.blockSignals(True)
            action_osd.setChecked(value.get('enabled', False))
            action_osd.blockSignals(False)
            # Live Update OSD
            osd.set_config(value)
        elif key == 'persistent_overlay':
            action_overlay.blockSignals(True)
            action_overlay.setChecked(value.get('enabled', False))
            action_overlay.blockSignals(False)
            # Live Update Overlay
            overlay.set_config(value)

    signals.setting_changed.connect(on_setting_changed)

    # AFK Timer (Dynamic Throttling)
    afk_timer = QTimer()
    afk_timer.setSingleShot(True)

    def schedule_afk_check():
        """
        Schedules the next AFK check based on the configured timeout.
        """
        if not audio.afk_config.get('enabled', False):
            afk_timer.stop()
            return

        timeout = audio.afk_config.get('timeout', 60)
        idle_time = get_idle_duration()
        
        # Calculate time remaining until timeout
        remaining = timeout - idle_time
        
        if remaining <= 0:
            # Timeout reached
            if not audio.get_mute_state():
                print(f"AFK Detected ({idle_time:.1f}s). Muting...")
                audio.toggle_mute()
            # Check again in a while (e.g. 1 second) to see if user returns or to keep monitoring
            next_interval = 1000
        else:
            # Wait for the remaining time, plus a small buffer (100ms)
            # But don't wait too long in case config changes (though config changes trigger re-schedule)
            # Cap at 5 minutes to be safe, or just trust the math.
            # Let's use the exact remaining time.
            next_interval = int(remaining * 1000) + 100
            
            # Sanity check: never poll faster than 1s unless very close
            if next_interval < 1000: next_interval = 1000

        afk_timer.start(next_interval)

    def on_afk_config_changed(new_config):
        """
        Callback for when AFK configuration changes.
        
        Args:
            new_config (dict): The new AFK configuration.
        """
        # Re-evaluate timer when config changes
        schedule_afk_check()

    # Hook into config changes (we need to add a signal for this in core.py or just poll less aggressively)
    # For now, we'll just start the loop. Ideally `audio` would emit signal on config change.
    # Since we don't have a specific signal for AFK config change in AudioController yet, 
    # we will rely on the loop self-correcting or add a signal later.
    # Actually, let's just start it.
    
    afk_timer.timeout.connect(schedule_afk_check)
    schedule_afk_check()

    # --- HIGH PRIORITY ---
    # Set process priority to High to prevent hook timeouts during gaming
    set_high_priority()

    print(f"\n{'='*50}")
    print(f"  Microphone Mute Toggle v{VERSION} (Refactored)")
    print(f"  Mode: Non-Admin | Native Hooks | Fully Configurable")
    print(f"{'='*50}")
    print("✓ Ready! Use tray icon to configure.")

    try:
        sys.exit(app.exec())
    finally:
        input_manager.stop()

if __name__ == "__main__":
    main()
