"""Theme detection for MicMute.

This module provides the ThemeListener class for detecting system theme changes.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from ..core import signals

__all__ = ["ThemeListener"]


class ThemeListener(QWidget):
    """Hidden widget that listens for system theme change events.

    Uses native Windows events to detect when the system theme changes
    and emits a signal to update the UI accordingly.
    """

    def __init__(self) -> None:
        """Initialize the theme listener."""
        super().__init__()
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

    def nativeEvent(self, event_type: bytes, message: object) -> tuple[bool, int] | None:
        """Handle native Windows events to detect theme changes.

        Args:
            event_type: The type of event.
            message: The message pointer.

        Returns:
            Tuple of (handled, result) or None if not handled.
        """
        msg = wintypes.MSG.from_address(message.__int__())  # type: ignore[union-attr]
        # WM_SETTINGCHANGE
        if msg.message == 0x001A:
            signals.theme_changed.emit()
        return super().nativeEvent(event_type, message)
