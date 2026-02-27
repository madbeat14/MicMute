"""Core audio control functionality for MicMute.

This module provides the main AudioController class for managing audio devices,
volume control, and configuration. It handles interaction with Windows Core Audio
APIs via pycaw.
"""

from __future__ import annotations

import gc
import threading
from typing import Any, cast
from winsound import Beep

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QSoundEffect
from pycaw.pycaw import AudioUtilities

from .config import ConfigManager, BeepConfig, SoundConfig, HotkeyConfig
from .utils import get_internal_asset, get_external_sound_dir

__all__ = ["MuteSignals", "AudioController", "signals", "audio"]


class MuteSignals(QObject):
    """Defines PySide6 signals for application-wide events."""

    # Signal to update the tray icon state
    update_icon: Signal = Signal(bool)
    # Signal when the system or app theme changes
    theme_changed: Signal = Signal()
    # Signal to trigger mute from hook
    toggle_mute: Signal = Signal()
    # Signal to trigger explicit mute state from hook
    set_mute: Signal = Signal(bool)
    # Signal when a key is captured in recording mode
    key_recorded: Signal = Signal(int)
    # Signal when default device changes
    device_changed: Signal = Signal(str)
    # Signal when a setting changes (key, value)
    setting_changed: Signal = Signal(str, object)
    # Signal to exit the application
    exit_app: Signal = Signal()


class AudioController:
    """Manages audio devices, volume control, and configuration.

    Handles interaction with Windows Core Audio APIs via pycaw.

    Attributes:
        volume: The endpoint volume interface for the current device.
        device: The current audio device object.
        config_manager: Manages loading and saving of configuration.
        player: QSoundEffect player for custom sounds.
        device_listener: COM object for receiving device change notifications.
        enumerator: Device enumerator for registering callbacks.
    """

    __slots__ = [
        "volume",
        "device",
        "config_manager",
        "BEEP_ERROR",
        "player",
        "device_listener",
        "enumerator",
        "__weakref__",
    ]

    def __init__(self) -> None:
        """Initialize the AudioController with default settings and load configuration."""
        self.volume: Any | None = None
        self.device: Any | None = None
        self.config_manager = ConfigManager()
        self.BEEP_ERROR = (200, 500)

        # Audio Player
        self.player: QSoundEffect | None = None

        self.device_listener: Any | None = None
        self.enumerator: Any | None = None

        self.config_manager.load_config()

    # Property proxies for backward compatibility and ease of use
    @property
    def device_id(self) -> str | None:
        """Get the current device ID."""
        return self.config_manager.device_id

    @device_id.setter
    def device_id(self, value: str | None) -> None:
        """Set the current device ID."""
        self.config_manager.device_id = value

    @property
    def beep_enabled(self) -> bool:
        """Get whether beep sounds are enabled."""
        return self.config_manager.beep_enabled

    @beep_enabled.setter
    def beep_enabled(self, value: bool) -> None:
        """Set whether beep sounds are enabled."""
        self.config_manager.beep_enabled = value

    @property
    def audio_mode(self) -> str:
        """Get the current audio mode ('beep' or 'custom')."""
        return self.config_manager.audio_mode

    @audio_mode.setter
    def audio_mode(self, value: str) -> None:
        """Set the audio mode ('beep' or 'custom')."""
        self.config_manager.audio_mode = value

    @property
    def sync_ids(self) -> list[str]:
        """Get the list of synchronized device IDs."""
        return self.config_manager.sync_ids

    @sync_ids.setter
    def sync_ids(self, value: list[str]) -> None:
        """Set the list of synchronized device IDs."""
        self.config_manager.sync_ids = value

    @property
    def beep_config(self) -> dict[str, BeepConfig]:
        """Get the beep configuration."""
        return self.config_manager.beep_config

    @beep_config.setter
    def beep_config(self, value: dict[str, BeepConfig]) -> None:
        """Set the beep configuration."""
        self.config_manager.beep_config = value

    @property
    def sound_config(self) -> dict[str, SoundConfig]:
        """Get the sound configuration."""
        return self.config_manager.sound_config

    @sound_config.setter
    def sound_config(self, value: dict[str, SoundConfig]) -> None:
        """Set the sound configuration."""
        self.config_manager.sound_config = value

    @property
    def hotkey_config(self) -> dict[str, Any]:
        """Get the hotkey configuration."""
        return self.config_manager.hotkey_config

    @hotkey_config.setter
    def hotkey_config(self, value: dict[str, Any]) -> None:
        """Set the hotkey configuration."""
        self.config_manager.hotkey_config = value

    @property
    def afk_config(self) -> dict[str, Any]:
        """Get the AFK configuration."""
        return self.config_manager.afk_config

    @afk_config.setter
    def afk_config(self, value: dict[str, Any]) -> None:
        """Set the AFK configuration."""
        self.config_manager.afk_config = value

    @property
    def osd_config(self) -> dict[str, Any]:
        """Get the OSD configuration."""
        return self.config_manager.osd_config

    @osd_config.setter
    def osd_config(self, value: dict[str, Any]) -> None:
        """Set the OSD configuration."""
        self.config_manager.osd_config = value

    @property
    def persistent_overlay(self) -> dict[str, Any]:
        """Get the persistent overlay configuration."""
        return self.config_manager.persistent_overlay

    @persistent_overlay.setter
    def persistent_overlay(self, value: dict[str, Any]) -> None:
        """Set the persistent overlay configuration."""
        self.config_manager.persistent_overlay = value

    def start_device_watcher(self) -> None:
        """Start the background thread for monitoring audio device changes."""
        try:
            from .utils import (
                DeviceChangeListener,
                CLSID_MMDeviceEnumerator,
                IMMDeviceEnumerator,
            )
            from comtypes import client

            self.enumerator = client.CreateObject(
                CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator
            )
            self.device_listener = DeviceChangeListener(self.on_device_changed_callback)
            self.enumerator.RegisterEndpointNotificationCallback(self.device_listener)
            print("Background device watcher started.")
        except Exception as e:
            print(f"Failed to start device watcher: {e}")

    def on_device_changed_callback(self, new_device_id: str) -> None:
        """Callback triggered when the default audio device changes.

        Args:
            new_device_id: The ID of the new default device.
        """
        # Called from COM thread
        signals.device_changed.emit(new_device_id)

    def save_config(self) -> None:
        """Save current application settings to the JSON configuration file."""
        self.config_manager.save_config()

    def _update_and_save(self, attr: str, signal_key: str, value: Any) -> None:
        """Update a config attribute, save to disk, and emit a signal.

        Args:
            attr: The attribute name on self (e.g. 'beep_config').
            signal_key: The key string to emit via setting_changed signal.
            value: The new value.
        """
        setattr(self, attr, value)
        self.save_config()
        signals.setting_changed.emit(signal_key, value)

    def set_beep_enabled(self, enabled: bool) -> None:
        """Enable or disable the beep sound effect.

        Args:
            enabled: True to enable, False to disable.
        """
        self._update_and_save("beep_enabled", "beep_enabled", enabled)

    def update_audio_mode(self, mode: str) -> None:
        """Update the audio feedback mode.

        Args:
            mode: 'beep' or 'custom'.

        Raises:
            ValueError: If mode is not 'beep' or 'custom'.
        """
        if mode not in ("beep", "custom"):
            raise ValueError(f"Invalid audio mode: {mode}. Must be 'beep' or 'custom'.")
        self._update_and_save("audio_mode", "audio_mode", mode)

    def update_beep_config(self, new_config: dict[str, BeepConfig]) -> None:
        """Update the configuration for beep sounds.

        Args:
            new_config: New beep configuration dictionary.
        """
        self._update_and_save("beep_config", "beep_config", new_config)

    def update_hotkey_config(self, new_config: dict[str, Any]) -> None:
        """Update the global hotkey configuration.

        Args:
            new_config: New hotkey configuration dictionary.
        """
        self._update_and_save("hotkey_config", "hotkey", new_config)

    def update_afk_config(self, new_config: dict[str, Any]) -> None:
        """Update the AFK (Away From Keyboard) feature configuration.

        Args:
            new_config: New AFK configuration dictionary.
        """
        self._update_and_save("afk_config", "afk", new_config)

    def update_osd_config(self, new_config: dict[str, Any]) -> None:
        """Update the On-Screen Display (OSD) configuration.

        Args:
            new_config: New OSD configuration dictionary.
        """
        self._update_and_save("osd_config", "osd", new_config)

    def update_persistent_overlay(self, new_config: dict[str, Any]) -> None:
        """Update the persistent overlay configuration.

        Args:
            new_config: New overlay configuration dictionary.
        """
        self._update_and_save("persistent_overlay", "persistent_overlay", new_config)

    def update_sync_ids(self, ids: list[str]) -> None:
        """Update the list of synchronized device IDs.

        Args:
            ids: List of device IDs to sync with the main device.
        """
        self._update_and_save("sync_ids", "sync_ids", ids)

    def find_device(self) -> bool:
        """Locate and initialize the target audio device.

        Returns:
            True if a device was found and set, False otherwise.
        """
        try:
            all_devices = AudioUtilities.GetAllDevices()

            if self.device_id:
                found_dev = next(
                    (d for d in all_devices if d.id == self.device_id), None
                )
                if found_dev:
                    print(f"Found saved device: {found_dev.FriendlyName}")
                    self.set_device_object(found_dev)
                    return True

                print("Saved device not found, falling back to default...")

            try:
                enumerator = AudioUtilities.GetDeviceEnumerator()
                default_dev = enumerator.GetDefaultAudioEndpoint(1, 0)
                default_id = default_dev.GetId()

                found_default = next(
                    (d for d in all_devices if d.id == default_id), None
                )
                if found_default:
                    print(f"Using system default: {found_default.FriendlyName}")
                    self.device_id = found_default.id
                    self.set_device_object(found_default)
                    return True
            except Exception:
                pass

            return False
        except Exception as e:
            print(f"Error finding device: {e}")
            return False
        finally:
            gc.collect()

    def set_device_object(self, dev: Any) -> None:
        """Set the active audio device object and initialize volume control.

        Args:
            dev: The pycaw device object.
        """
        self.device = dev
        self.volume = dev.EndpointVolume
        signals.update_icon.emit(self.get_mute_state())

    def set_device_by_id(self, dev_id: str) -> bool:
        """Set the active device by its ID and save the preference.

        Args:
            dev_id: The ID of the device to set.

        Returns:
            True if successful, False otherwise.
        """
        self.device_id = dev_id
        self.save_config()
        return self.find_device()

    def toggle_mute(self) -> None:
        """Toggle the mute state of the current device."""
        if not self.volume:
            return
        try:
            current = self.volume.GetMute()
            self.set_mute_state(not current)
        except Exception:
            if self.beep_enabled:
                Beep(*self.BEEP_ERROR)

    def set_device_mute(self, dev: Any, state: bool) -> None:
        """Mute a specific device object.

        Args:
            dev: The pycaw device object.
            state: True to mute, False to unmute.
        """
        try:
            dev.EndpointVolume.SetMute(state, None)
        except Exception:
            pass

    def set_mute_state(self, new_state: bool) -> None:
        """Set the mute state of the current device and synchronized devices.

        Args:
            new_state: True to mute, False to unmute.
        """
        if not self.volume:
            return
        try:
            current = self.volume.GetMute()
            if current != new_state:
                self.volume.SetMute(new_state, None)

                # Play Sound (Custom or Beep)
                sound_type = "mute" if new_state else "unmute"
                self.play_sound(sound_type)

            # Sync Slaves (Enumerate once, then match)
            if self.sync_ids:
                sync_set = {sid for sid in self.sync_ids if sid != self.device_id}
                if sync_set:
                    try:
                        all_devices = AudioUtilities.GetAllDevices()
                        for dev in all_devices:
                            if dev.id in sync_set:
                                self.set_device_mute(dev, new_state)
                    except Exception:
                        pass

            # Emit signal AFTER syncing so UI reads correct states
            if current != new_state:
                signals.update_icon.emit(new_state)

        except Exception as e:
            print(f"Error setting mute state: {e}")

    def update_sound_config(self, new_config: dict[str, SoundConfig]) -> None:
        """Update the configuration for custom sound files.

        Args:
            new_config: New sound configuration dictionary.
        """
        self._update_and_save("sound_config", "sound_config", new_config)

    def play_sound(self, sound_type: str) -> None:
        """Play custom sound if set, else fallback to beep.

        Handles hybrid asset management (Internal vs External).

        Args:
            sound_type: 'mute' or 'unmute'.

        Raises:
            ValueError: If sound_type is not 'mute' or 'unmute'.
        """
        if sound_type not in ("mute", "unmute"):
            raise ValueError(f"Invalid sound_type: {sound_type}. Must be 'mute' or 'unmute'.")

        if not self.beep_enabled:
            return

        # Fallback Beep Function
        def run_beep() -> None:
            try:
                cfg = self.beep_config[sound_type]
                for _ in range(cfg["count"]):
                    Beep(cfg["freq"], cfg["duration"])
            except Exception:
                pass

        # Check Audio Mode
        if self.audio_mode == "beep":
            threading.Thread(target=run_beep, daemon=True).start()
            return

        # Custom Mode Logic

        sound_cfg = self.sound_config.get(sound_type, {})
        # Handle case where config might still be old string
        if isinstance(sound_cfg, str):
            filename = sound_cfg
            volume = 50
        else:
            filename = sound_cfg.get("file")
            volume = sound_cfg.get("volume", 50)

        path: str | None = None

        if not filename or filename == "DEFAULT":
            internal_path = get_internal_asset(f"{sound_type}.wav")
            if internal_path.exists():
                path = str(internal_path)
        else:
            # Custom file - check external sounds directory first
            external_path = get_external_sound_dir() / filename
            if external_path.exists():
                path = str(external_path)
            else:
                # Fallback to internal assets
                internal_path = get_internal_asset(filename)
                if internal_path.exists():
                    path = str(internal_path)
                else:
                    # Final fallback to default internal asset
                    print(f"Custom sound '{filename}' not found. Reverting to default.")
                    default_internal = get_internal_asset(f"{sound_type}.wav")
                    if default_internal.exists():
                        path = str(default_internal)
                        # Update Config to reflect revert
                        if sound_type in self.sound_config:
                            self.sound_config[sound_type]["file"] = f"{sound_type}.wav"
                            self.config_manager.save_config()
                            signals.setting_changed.emit("sound_config", self.sound_config)
                    else:
                        print(f"Default sound for {sound_type} not found in assets.")

        # Play
        if path:
            try:
                if self.player is None:
                    self.player = QSoundEffect()

                self.player.setSource(QUrl.fromLocalFile(path))
                # Apply volume (0-100 -> 0.0-1.0)
                self.player.setVolume(volume / 100.0)
                self.player.play()
                return
            except Exception as e:
                print(f"Error playing sound '{path}': {e}")
                # Fallback to beep on error
                threading.Thread(target=run_beep, daemon=True).start()
        else:
            # No path found - Fallback to beep
            threading.Thread(target=run_beep, daemon=True).start()

    def get_mute_state(self) -> bool:
        """Retrieve the current mute state of the active device.

        Returns:
            True if muted, False otherwise.
        """
        if self.volume:
            try:
                return cast(bool, self.volume.GetMute())
            except Exception:
                return False
        return False


# Global signal instance
signals = MuteSignals()

# Global audio controller instance
audio = AudioController()
