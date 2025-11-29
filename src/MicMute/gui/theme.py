import ctypes
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

from ..core import signals

# --- THEME DETECTION (EVENT DRIVEN) ---
class ThemeListener(QWidget):
    """
    Hidden widget that listens for system theme change events.
    """
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
    
    def nativeEvent(self, eventType, message):
        """
        Handles native Windows events to detect theme changes.
        
        Args:
            eventType (bytes): The type of event.
            message (int): The message pointer.
            
        Returns:
            tuple: Result of the superclass nativeEvent.
        """
        msg = ctypes.wintypes.MSG.from_address(message.__int__())
        # WM_SETTINGCHANGE
        if msg.message == 0x001A:
            signals.theme_changed.emit()
        return super().nativeEvent(eventType, message)
