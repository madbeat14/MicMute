"""Main entry point for MicMute application.

This module initializes the Qt application, system tray icon, audio controller,
and all background threads for the MicMute application.
"""

from __future__ import annotations

import gc
import os
import sys
import warnings
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)
from pycaw.pycaw import AudioUtilities

from .config import CONFIG_FILE
from .core import audio, signals
from .gui import SettingsDialog, ThemeListener
from .input_manager import InputManager
from .overlay import MetroOSD, StatusOverlay
from .utils import (
    get_idle_duration,
    is_system_light_theme,
    set_default_device,
    set_high_priority,
    get_run_on_startup,
    set_run_on_startup,
)

# Suppress warnings (e.g., pycaw COM errors)
warnings.simplefilter("ignore", UserWarning)

__all__ = ["main"]

# Get version from package metadata
try:
    from importlib.metadata import version as get_version
    VERSION: str = get_version("micmute")
except Exception:
    # Fallback for development/uninstalled
    try:
        from ._version import __version__ as VERSION
    except ImportError:
        VERSION = "0.0.0+dev"


def _get_assets_dir() -> Path:
    """Get the path to the assets directory.

    Returns:
        Path to the assets directory.
    """
    if getattr(sys, "frozen", False):
        # Running as compiled EXE
        return Path(sys._MEIPASS) / "MicMute" / "assets"
    else:
        # Running from source
        return Path(__file__).parent / "assets"


def _ensure_app_directories() -> None:
    """Ensure all application directories exist.
    
    Creates necessary directories for config and sound files.
    Silently handles permission errors.
    """
    from .config import CONFIG_FILE
    from .utils import get_external_sound_dir
    
    # Ensure config directory exists
    try:
        config_path = Path(CONFIG_FILE)
        if str(config_path.parent) and str(config_path.parent) != ".":
            config_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create config directory: {e}")
    
    # Ensure sounds directory exists
    try:
        sounds_dir = get_external_sound_dir()
        sounds_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create sounds directory: {e}")


def _setup_qt_environment() -> None:
    """Setup Qt environment variables to use proper cache locations.
    
    This prevents Qt from trying to write to protected directories.
    """
    
    # Set Qt cache directory to AppData/Local
    if getattr(sys, "frozen", False):
        qt_cache_dir = Path.home() / "AppData" / "Local" / "MicMute" / "QtCache"
        try:
            qt_cache_dir.mkdir(parents=True, exist_ok=True)
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(Path(sys._MEIPASS) / "PySide6" / "plugins")
            os.environ["QML2_IMPORT_PATH"] = str(Path(sys._MEIPASS) / "PySide6" / "qml")
        except Exception:
            pass


def main() -> int:
    """Main entry point for the MicMute application.

    Initializes the Qt application, audio controller, tray icon,
    and background threads.

    Returns:
        Application exit code.
    """
    # Setup Qt environment before creating QApplication
    _setup_qt_environment()
    
    # Ensure directories before anything else
    _ensure_app_directories()
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Initialize audio device
    if not audio.find_device():
        print("Warning: No device initially found.")

    # Setup paths
    assets_dir = _get_assets_dir()
    svg_white_unmuted = str(assets_dir / "mic_white.svg")
    svg_white_muted = str(assets_dir / "mic_muted_white.svg")
    svg_black_unmuted = str(assets_dir / "mic_black.svg")
    svg_black_muted = str(assets_dir / "mic_muted_black.svg")

    # Load Icons
    icon_white_unmuted = QIcon(svg_white_unmuted)
    icon_white_muted = QIcon(svg_white_muted)
    icon_black_unmuted = QIcon(svg_black_unmuted)
    icon_black_muted = QIcon(svg_black_muted)

    def get_current_icon(muted: bool, light_theme: bool) -> QIcon:
        """Determine the appropriate icon based on mute state and theme.

        Args:
            muted: Current mute state.
            light_theme: True if system is in light mode.

        Returns:
            The appropriate QIcon object.
        """
        if light_theme:
            return icon_black_muted if muted else icon_black_unmuted
        return icon_white_muted if muted else icon_white_unmuted

    # Initialize tray icon
    tray = QSystemTrayIcon()
    current_mute_state = audio.get_mute_state()
    is_light_theme = is_system_light_theme()

    tray.setIcon(get_current_icon(current_mute_state, is_light_theme))
    tray.setToolTip(f"MicMute v{VERSION} - {'MUTED' if current_mute_state else 'UNMUTED'}")

    # OSD Initialization
    osd = MetroOSD(svg_white_unmuted, svg_white_muted)
    osd.set_config(audio.osd_config)

    # Persistent Overlay Initialization
    overlay = StatusOverlay(
        svg_white_unmuted, svg_white_muted,
        svg_black_unmuted, svg_black_muted,
    )
    overlay.set_config(audio.persistent_overlay, initial_mute_state=current_mute_state)
    overlay.set_target_device(
        audio.persistent_overlay.get("device_id"),
        fallback_device_id=audio.device_id,
    )
    overlay.config_changed.connect(audio.update_persistent_overlay)

    # Listeners
    theme_listener = ThemeListener()

    # Input Manager (Hooks)
    input_manager = InputManager()
    input_manager.start()

    # Dialog Instances
    dialogs: dict[str, QDialog | None] = {"settings": None}

    def populate_devices_menu(menu: QMenu, submenu_devices: QMenu) -> None:
        """Populate the device selection submenu with available microphones.

        Args:
            menu: The parent menu.
            submenu_devices: The submenu to populate.
        """
        submenu_devices.clear()

        try:
            # Get All Devices
            all_devices_raw = AudioUtilities.GetAllDevices()
            enumerator = AudioUtilities.GetDeviceEnumerator()
            collection = enumerator.EnumAudioEndpoints(1, 1)  # eCapture, eAll
            count = collection.GetCount()
            capture_ids: set[str] = set()
            for i in range(count):
                dev = collection.Item(i)
                capture_ids.add(dev.GetId())

            # Filter and Sort
            devices = [dev for dev in all_devices_raw if dev.id in capture_ids]
            current_id = audio.device_id

            for dev in devices:
                name = dev.FriendlyName
                dev_id = dev.id

                action = QAction(name, menu)
                action.setCheckable(True)
                action.setChecked(dev_id == current_id)

                def on_triggered(checked: bool, d_id: str = dev_id, dev_name: str = name) -> None:
                    try:
                        if set_default_device(d_id):
                            if audio.set_device_by_id(d_id):
                                tray.showMessage(
                                    "Success",
                                    f"Switched to: {dev_name}",
                                    QSystemTrayIcon.Information,
                                    2000,
                                )
                                overlay.set_target_device(d_id)
                            else:
                                tray.showMessage(
                                    "Error",
                                    "Failed to set application device.",
                                    QSystemTrayIcon.Warning,
                                    2000,
                                )
                        else:
                            tray.showMessage(
                                "Error",
                                "Failed to set Windows default.",
                                QSystemTrayIcon.Warning,
                                2000,
                            )
                    except Exception as e:
                        print(f"Error switching device: {e}")
                        tray.showMessage(
                            "Error",
                            f"Device error: {e}",
                            QSystemTrayIcon.Warning,
                            2000,
                        )

                action.triggered.connect(lambda checked, d_id=dev_id: on_triggered(checked, d_id))
                submenu_devices.addAction(action)

        except Exception as e:
            print(f"Error populating menu: {e}")
            error_action = QAction("Error loading devices", menu)
            error_action.setEnabled(False)
            submenu_devices.addAction(error_action)

    def show_settings_dialog() -> None:
        """Display the settings dialog, initializing it if necessary."""
        try:
            if dialogs["settings"] and dialogs["settings"].isVisible():
                dialogs["settings"].activateWindow()
                dialogs["settings"].raise_()
                return
        except RuntimeError:
            dialogs["settings"] = None

        dialog = SettingsDialog(audio, input_manager.hook_thread)
        dialogs["settings"] = dialog

        def apply_updates() -> None:
            """Apply configuration changes to OSD and Overlay."""
            osd.set_config(audio.osd_config)
            overlay.set_config(audio.persistent_overlay)

            # Sync Tray Menu Checkboxes
            action_sound.setChecked(audio.beep_enabled)
            action_osd.setChecked(audio.osd_config.get("enabled", False))
            action_overlay.setChecked(audio.persistent_overlay.get("enabled", False))

        dialog.settings_applied.connect(apply_updates)

        def on_settings_finished(result: int) -> None:
            """Handle dialog close."""
            dialogs["settings"] = None
            dialog.deleteLater()
            gc.collect()

        dialog.finished.connect(on_settings_finished)
        dialog.show()

    # Toggle Handlers
    def toggle_beep_setting(checked: bool) -> None:
        """Toggle beep sound setting."""
        audio.set_beep_enabled(checked)

    def toggle_osd_setting(checked: bool) -> None:
        """Toggle OSD notification setting."""
        new_config = audio.osd_config.copy()
        new_config["enabled"] = checked
        audio.update_osd_config(new_config)
        if not checked:
            osd.hide()

    def toggle_overlay_setting(checked: bool) -> None:
        """Toggle persistent overlay setting."""
        new_config = audio.persistent_overlay.copy()
        new_config["enabled"] = checked
        audio.update_persistent_overlay(new_config)
        overlay.set_config(new_config)

    # Build Menu
    menu = QMenu()

    # Select Device Submenu
    submenu_devices = QMenu("Select Microphone", menu)
    submenu_devices.aboutToShow.connect(lambda: populate_devices_menu(menu, submenu_devices))
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
    action_osd.setChecked(audio.osd_config.get("enabled", False))
    action_osd.triggered.connect(toggle_osd_setting)
    menu.addAction(action_osd)

    # Overlay Toggle
    action_overlay = QAction("Show Persistent Overlay")
    action_overlay.setCheckable(True)
    action_overlay.setChecked(audio.persistent_overlay.get("enabled", False))
    action_overlay.triggered.connect(toggle_overlay_setting)
    menu.addAction(action_overlay)

    # Start on Boot Toggle
    action_startup = QAction("Start on Boot")
    action_startup.setCheckable(True)
    action_startup.setChecked(get_run_on_startup())
    action_startup.triggered.connect(set_run_on_startup)
    menu.addAction(action_startup)

    menu.addSeparator()

    # Settings
    action_settings = QAction("Settings")
    action_settings.triggered.connect(show_settings_dialog)
    menu.addAction(action_settings)

    # Help
    action_help = QAction("Help")
    action_help.triggered.connect(
        lambda: QDesktopServices.openUrl(
            QUrl("https://github.com/madbeat14/MicMute#readme")
        )
    )
    menu.addAction(action_help)

    # About
    action_about = QAction("About")

    def show_about() -> None:
        """Show the about dialog."""
        QMessageBox.about(
            None,
            "About MicMute",
            f"<b>MicMute v{VERSION}</b><br><br>"
            "Author: madbeat14<br>"
            "A lightweight, non-intrusive microphone mute toggle application "
            "with native hooks and overlay.",
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
    def update_tray_state(is_muted: bool | None = None) -> None:
        """Update the tray icon and tooltip based on the current state.

        Args:
            is_muted: The new mute state. If None, uses current state.
        """
        nonlocal current_mute_state, is_light_theme
        if is_muted is not None:
            current_mute_state = is_muted
        new_theme = is_system_light_theme()
        if is_muted is not None or new_theme != is_light_theme:
            is_light_theme = new_theme
            tray.setIcon(get_current_icon(current_mute_state, is_light_theme))
            tray.setToolTip(
                f"MicMute v{VERSION} - {'MUTED' if current_mute_state else 'UNMUTED'}"
            )

        if is_muted is not None:
            if audio.osd_config.get("enabled", False):
                osd.show_osd(is_muted)
            overlay.update_status(is_muted)

    signals.update_icon.connect(lambda m: update_tray_state(is_muted=m))
    signals.theme_changed.connect(lambda: update_tray_state(is_muted=None))
    signals.toggle_mute.connect(audio.toggle_mute)
    signals.set_mute.connect(audio.set_mute_state)
    signals.exit_app.connect(app.quit)

    # Initial sync
    overlay.is_muted = current_mute_state
    update_tray_state(current_mute_state)

    def on_device_changed(new_id: str) -> None:
        """Handle changes to the default audio device.

        Args:
            new_id: The ID of the new default device.
        """
        print(f"Default Device Changed: {new_id}")
        if audio.set_device_by_id(new_id):
            overlay.set_target_device(new_id)
            tray.showMessage(
                "Device Changed",
                "Switched to new default microphone.",
                QSystemTrayIcon.Information,
                2000,
            )

    signals.device_changed.connect(on_device_changed)

    def on_setting_changed(key: str, value: Any) -> None:
        """Handle setting changes from other parts of the app.

        Args:
            key: The setting key.
            value: The new setting value.
        """
        if key == "beep_enabled":
            action_sound.blockSignals(True)
            action_sound.setChecked(value)
            action_sound.blockSignals(False)
        elif key == "osd":
            action_osd.blockSignals(True)
            action_osd.setChecked(value.get("enabled", False))
            action_osd.blockSignals(False)
            osd.set_config(value)
        elif key == "persistent_overlay":
            action_overlay.blockSignals(True)
            action_overlay.setChecked(value.get("enabled", False))
            action_overlay.blockSignals(False)
            overlay.set_config(value)
            overlay.set_target_device(
                value.get("device_id"), fallback_device_id=audio.device_id
            )

    signals.setting_changed.connect(on_setting_changed)

    # AFK Timer (Dynamic Throttling)
    afk_timer = QTimer()
    afk_timer.setSingleShot(True)

    def schedule_afk_check() -> None:
        """Schedule the next AFK check based on the configured timeout."""
        if not audio.afk_config.get("enabled", False):
            afk_timer.stop()
            return

        timeout = audio.afk_config.get("timeout", 60)
        idle_time = get_idle_duration()
        remaining = timeout - idle_time

        if remaining <= 0:
            if not audio.get_mute_state():
                print(f"AFK Detected ({idle_time:.1f}s). Muting...")
                audio.toggle_mute()
            next_interval = 1000
        else:
            next_interval = int(remaining * 1000) + 100
            if next_interval < 1000:
                next_interval = 1000

        afk_timer.start(next_interval)

    afk_timer.timeout.connect(schedule_afk_check)
    schedule_afk_check()

    # High Priority
    set_high_priority()

    print(f"\n{'=' * 50}")
    print(f"  Microphone Mute Toggle v{VERSION} (Optimized)")
    print(f"  Mode: Non-Admin | Native Hooks | Fully Configurable")
    print(f"{'=' * 50}")
    print("Ready! Use tray icon to configure.")

    try:
        return app.exec()
    finally:
        input_manager.stop()


if __name__ == "__main__":
    sys.exit(main())
