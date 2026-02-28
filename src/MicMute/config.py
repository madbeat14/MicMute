"""Configuration management for MicMute.

This module provides the ConfigManager class for loading and saving
application settings to a JSON configuration file.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, TypedDict

__all__ = ["CONFIG_FILE", "ConfigManager", "BeepConfig", "SoundConfig"]


def _get_default_config_path() -> str:
    """Get the default config file path.

    When running as a frozen EXE, uses AppData/Local/MicMute to avoid
    permission issues with Program Files or other protected locations.
    When running from source, uses the project root.

    Returns:
        Path to the configuration file.
    """
    if getattr(sys, "frozen", False):
        # Running as compiled EXE - use AppData
        config_dir = Path.home() / "AppData" / "Local" / "MicMute"
        return str(config_dir / "mic_config.json")
    else:
        # Running from source - use project root
        return "mic_config.json"


CONFIG_FILE: str = _get_default_config_path()


class BeepConfig(TypedDict):
    """Configuration for a single beep sound."""

    freq: int
    duration: int
    count: int


class SoundConfig(TypedDict):
    """Configuration for a custom sound file."""

    file: str
    volume: int


class HotkeyConfig(TypedDict):
    """Configuration for a hotkey assignment."""

    vk: int
    name: str


class ConfigManager:
    """Manages loading and saving of application configuration.

    Attributes:
        config_file: Path to the configuration file.
        device_id: ID of the currently selected audio device.
        beep_enabled: Whether beep sounds are enabled.
        sync_ids: List of device IDs to synchronize mute state with.
        audio_mode: Audio feedback mode ('beep' or 'custom').
        beep_config: Configuration for beep sounds.
        sound_config: Configuration for custom sound files.
        hotkey_config: Configuration for global hotkeys.
        afk_config: Configuration for AFK timeout feature.
        osd_config: Configuration for On-Screen Display.
        persistent_overlay: Configuration for persistent overlay.
    """

    def __init__(self, config_file: str | None = None) -> None:
        """Initialize the ConfigManager with default settings.

        Args:
            config_file: Path to the configuration file. Defaults to CONFIG_FILE.
        """
        self.config_file: str = config_file if config_file is not None else CONFIG_FILE
        self.device_id: str | None = None
        self.beep_enabled: bool = True
        self.sync_ids: list[str] = []

        self.audio_mode: str = "beep"  # 'beep' or 'custom'
        self.beep_config: dict[str, BeepConfig] = {
            "mute": {"freq": 650, "duration": 180, "count": 2},
            "unmute": {"freq": 700, "duration": 200, "count": 1},
        }
        self.sound_config: dict[str, SoundConfig] = {
            "mute": {"file": "mute.wav", "volume": 50},
            "unmute": {"file": "unmute.wav", "volume": 50},
        }
        self.hotkey_config: dict[str, Any] = {
            "mode": "toggle",
            "toggle": {"vk": 0xB3, "name": "Media Play/Pause"},
            "mute": {"vk": 0, "name": "None"},
            "unmute": {"vk": 0, "name": "None"},
        }
        self.afk_config: dict[str, Any] = {"enabled": False, "timeout": 60}
        self.osd_config: dict[str, Any] = {
            "enabled": False,
            "duration": 1500,
            "position": "Bottom-Center",
            "size": 150,
        }
        self.persistent_overlay: dict[str, Any] = {
            "enabled": False,
            "show_vu": False,
            "opacity": 80,
            "x": 100,
            "y": 100,
            "position_mode": "Custom",
            "locked": False,
            "sensitivity": 5,
            "device_id": None,
            "scale": 100,
            "theme": "Auto",
        }

    def load_config(self) -> None:
        """Load application settings from the JSON configuration file.

        Handles migration from old configuration formats and validates data.
        """
        config_path = Path(self.config_file)
        if not config_path.exists():
            return

        try:
            with open(config_path, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)

            self._load_basic_settings(data)
            self._load_beep_config(data)
            self._load_sound_config(data)
            self._load_hotkey_config(data)
            self._load_afk_config(data)
            self._load_osd_config(data)
            self._load_overlay_config(data)

        except json.JSONDecodeError as e:
            print(f"Error parsing config file: {e}")
        except Exception as e:
            print(f"Error loading config: {e}")

    def _load_basic_settings(self, data: dict[str, Any]) -> None:
        """Load basic settings from config data.

        Args:
            data: The loaded configuration dictionary.
        """
        self.device_id = data.get("device_id")
        self.beep_enabled = data.get("beep_enabled", True)
        self.audio_mode = data.get("audio_mode", "beep")
        self.sync_ids = data.get("sync_ids", [])

    def _load_beep_config(self, data: dict[str, Any]) -> None:
        """Load beep configuration from config data.

        Args:
            data: The loaded configuration dictionary.
        """
        saved_beeps = data.get("beep_config")
        if saved_beeps and isinstance(saved_beeps, dict):
            for key in ("mute", "unmute"):
                if key in saved_beeps and isinstance(saved_beeps[key], dict):
                    self.beep_config[key].update(saved_beeps[key])

    def _load_sound_config(self, data: dict[str, Any]) -> None:
        """Load sound configuration with migration from old format.

        Args:
            data: The loaded configuration dictionary.
        """
        saved_sounds = data.get("sound_config")
        if not saved_sounds or not isinstance(saved_sounds, dict):
            return

        # Migration: Check if old format (simple key-value)
        # New format: {'mute': {'file': ..., 'volume': ...}, ...}
        # Old format: {'mute': 'path/to/file', ...}
        for key in ("mute", "unmute"):
            val = saved_sounds.get(key)
            if val is None:
                self.sound_config[key]["file"] = f"{key}.wav"
            elif isinstance(val, str):
                # Old format: migrate
                self.sound_config[key]["file"] = val
            elif isinstance(val, dict):
                self.sound_config[key].update(val)

    def _load_hotkey_config(self, data: dict[str, Any]) -> None:
        """Load hotkey configuration with migration from old format.

        Args:
            data: The loaded configuration dictionary.
        """
        saved_hotkey = data.get("hotkey")
        if not saved_hotkey or not isinstance(saved_hotkey, dict):
            return

        # Migration from old format {'vk': ..., 'name': ...}
        if "vk" in saved_hotkey:
            self.hotkey_config["toggle"] = {
                "vk": saved_hotkey["vk"],
                "name": saved_hotkey.get("name", "Unknown"),
            }
        else:
            self.hotkey_config.update(saved_hotkey)

    def _load_afk_config(self, data: dict[str, Any]) -> None:
        """Load AFK configuration from config data.

        Args:
            data: The loaded configuration dictionary.
        """
        saved_afk = data.get("afk")
        if saved_afk and isinstance(saved_afk, dict):
            self.afk_config.update(saved_afk)

    def _load_osd_config(self, data: dict[str, Any]) -> None:
        """Load OSD configuration from config data.

        Args:
            data: The loaded configuration dictionary.
        """
        saved_osd = data.get("osd")
        if saved_osd and isinstance(saved_osd, dict):
            self.osd_config.update(saved_osd)

    def _load_overlay_config(self, data: dict[str, Any]) -> None:
        """Load persistent overlay configuration from config data.

        Args:
            data: The loaded configuration dictionary.
        """
        saved_overlay = data.get("persistent_overlay")
        if saved_overlay and isinstance(saved_overlay, dict):
            self.persistent_overlay.update(saved_overlay)

    def _ensure_config_dir(self) -> bool:
        """Ensure the config file parent directory exists.

        Returns:
            True if directory exists or was created, False otherwise.
        """
        try:
            config_path = Path(self.config_file)
            parent_dir = config_path.parent
            if parent_dir and str(parent_dir) != ".":
                parent_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Warning: Could not create config directory: {e}")
            return False

    def save_config(self) -> None:
        """Save current application settings to the JSON configuration file.

        Writes all configuration to disk in a structured format.
        """
        # Ensure parent directory exists before trying to write
        if not self._ensure_config_dir():
            return

        config_data: dict[str, Any] = {
            "device_id": self.device_id,
            "sync_ids": self.sync_ids,
            "beep_enabled": self.beep_enabled,
            "audio_mode": self.audio_mode,
            "beep_config": self.beep_config,
            "sound_config": self.sound_config,
            "hotkey": self.hotkey_config,
            "afk": self.afk_config,
            "osd": self.osd_config,
            "persistent_overlay": self.persistent_overlay,
        }

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except PermissionError:
            print(f"Permission denied when saving config to {self.config_file}")
        except OSError as e:
            print(f"OS error when saving config: {e}")
        except Exception as e:
            print(f"Unexpected error saving config: {e}")
