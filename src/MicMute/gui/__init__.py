"""GUI components for MicMute.

This package contains all UI-related components including settings dialogs,
device selection widgets, hotkey configuration, and theme detection.
"""

from __future__ import annotations

from .theme import ThemeListener
from .devices import DeviceSelectionWidget
from .hotkeys import SingleHotkeyInputWidget, HotkeySettingsWidget
from .settings import (
    SettingsDialog,
    BeepSettingsWidget,
    AfkSettingsWidget,
    OsdSettingsWidget,
    OverlaySettingsWidget,
)

__all__ = [
    "ThemeListener",
    "DeviceSelectionWidget",
    "SingleHotkeyInputWidget",
    "HotkeySettingsWidget",
    "SettingsDialog",
    "BeepSettingsWidget",
    "AfkSettingsWidget",
    "OsdSettingsWidget",
    "OverlaySettingsWidget",
]
