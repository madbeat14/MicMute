from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, 
                             QPushButton, QGroupBox, QRadioButton, QButtonGroup, QStackedWidget)
from ..core import signals
from ..utils import VK_LMENU, VK_RMENU

# VK Map for Dropdown
VK_MAP = {
    0x70: "F1", 0x71: "F2", 0x72: "F3", 0x73: "F4",
    0x74: "F5", 0x75: "F6", 0x76: "F7", 0x77: "F8",
    0x78: "F9", 0x79: "F10", 0x7A: "F11", 0x7B: "F12",
    0x7C: "F13", 0x7D: "F14", 0x7E: "F15", 0x7F: "F16",
    0x80: "F17", 0x81: "F18", 0x82: "F19", 0x83: "F20",
    0x84: "F21", 0x85: "F22", 0x86: "F23", 0x87: "F24",
    0x13: "Pause/Break", 0x2C: "Print Screen", 0x91: "Scroll Lock",
    0xB3: "Media Play/Pause", 0xB2: "Media Stop",
    0xB0: "Media Next", 0xB1: "Media Prev",
    0xAD: "Volume Mute", 0xAE: "Volume Down", 0xAF: "Volume Up"
}

class SingleHotkeyInputWidget(QWidget):
    """
    Widget for capturing and setting a single hotkey.
    """
    def __init__(self, label_text, initial_vk, hook, parent=None):
        """
        Initializes the hotkey input widget.
        
        Args:
            label_text (str): Label for the input.
            initial_vk (int): Initial virtual key code.
            hook (NativeKeyboardHook): The keyboard hook instance.
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        self.hook = hook
        self.current_vk = initial_vk
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(QLabel(label_text))
        
        self.combo = QComboBox()
        self.vk_items = []
        
        # Sort by name for easier finding
        sorted_vks = sorted(VK_MAP.items(), key=lambda item: item[1])
        
        for vk, name in sorted_vks:
            self.combo.addItem(f"{name}", vk)
            self.vk_items.append(vk)
            
        # Add current custom if not in map
        if self.current_vk not in VK_MAP and self.current_vk != 0:
            self.combo.addItem(f"Custom Key ({self.current_vk})", self.current_vk)
            self.vk_items.append(self.current_vk)
            
        # Select current
        index = self.combo.findData(self.current_vk)
        if index >= 0:
            self.combo.setCurrentIndex(index)
        
        self.combo.currentIndexChanged.connect(self.on_combo_change)
        layout.addWidget(self.combo)
        
        self.capture_btn = QPushButton("Set")
        self.capture_btn.setFixedWidth(50)
        self.capture_btn.clicked.connect(self.start_capture)
        layout.addWidget(self.capture_btn)
        
        signals.key_recorded.connect(self.on_key_recorded)

    def on_combo_change(self, index):
        """
        Handles changes in the hotkey dropdown.
        
        Args:
            index (int): Selected index.
        """
        self.current_vk = self.combo.itemData(index)

    def start_capture(self):
        """
        Starts capturing a key press for hotkey assignment.
        """
        if self.hook is None:
            return
        self.capture_btn.setText("...")
        self.capture_btn.setEnabled(False)
        # We need a way to know WHICH widget requested capture.
        # For simplicity, we'll set a flag on the parent or use a shared state if needed.
        # But signals are global. We need to check if WE are the active capturer.
        self.is_capturing = True
        self.hook.start_recording()

    def on_key_recorded(self, vk):
        """
        Callback when a key is recorded during capture.
        
        Args:
            vk (int): The virtual key code recorded.
        """
        if not getattr(self, 'is_capturing', False):
            return
        
        if self.hook:
            self.hook.stop_recording()
        self.is_capturing = False
        self.current_vk = vk
        self.capture_btn.setText("Set")
        self.capture_btn.setEnabled(True)
        
        # Update Combo
        name = VK_MAP.get(vk, f"Key {vk}")
        index = self.combo.findData(vk)
        if index == -1:
            self.combo.addItem(name, vk)
            index = self.combo.count() - 1
        self.combo.setCurrentIndex(index)

    def get_config(self):
        """
        Retrieves the configured hotkey.
        
        Returns:
            dict: Hotkey configuration {'vk': int, 'name': str}.
        """
        name = VK_MAP.get(self.current_vk, f"Key {self.current_vk}")
        return {'vk': self.current_vk, 'name': name}
    
    def cleanup(self):
        """
        Disconnects signals to prevent memory leaks.
        """
        try:
            signals.key_recorded.disconnect(self.on_key_recorded)
        except: pass

class HotkeySettingsWidget(QWidget):
    """
    Widget for configuring global hotkeys (Toggle or Separate).
    """
    def __init__(self, audio_controller, hook, parent=None):
        """
        Initializes the hotkey settings widget.
        
        Args:
            audio_controller (AudioController): The main audio controller instance.
            hook (NativeKeyboardHook): The keyboard hook instance.
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        self.audio = audio_controller
        self.hook = hook
        
        layout = QVBoxLayout(self)
        
        # Mode Selection
        mode_group = QGroupBox("Hotkey Mode")
        mode_layout = QHBoxLayout()
        self.mode_toggle = QRadioButton("Single Toggle Key")
        self.mode_separate = QRadioButton("Separate Mute/Unmute Keys")
        
        self.mode_group_btn = QButtonGroup()
        self.mode_group_btn.addButton(self.mode_toggle, 0)
        self.mode_group_btn.addButton(self.mode_separate, 1)
        
        mode_layout.addWidget(self.mode_toggle)
        mode_layout.addWidget(self.mode_separate)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Stacked Widget for Inputs
        self.stack = QStackedWidget()
        
        # Page 1: Toggle
        self.page_toggle = QWidget()
        toggle_layout = QVBoxLayout(self.page_toggle)
        self.input_toggle = SingleHotkeyInputWidget(
            "Toggle Hotkey:", 
            self.audio.hotkey_config.get('toggle', {}).get('vk', 0xB3), 
            self.hook
        )
        toggle_layout.addWidget(self.input_toggle)
        toggle_layout.addStretch()
        self.stack.addWidget(self.page_toggle)
        
        # Page 2: Separate
        self.page_separate = QWidget()
        separate_layout = QVBoxLayout(self.page_separate)
        self.input_mute = SingleHotkeyInputWidget(
            "Mute Hotkey:", 
            self.audio.hotkey_config.get('mute', {}).get('vk', 0), 
            self.hook
        )
        self.input_unmute = SingleHotkeyInputWidget(
            "Unmute Hotkey:", 
            self.audio.hotkey_config.get('unmute', {}).get('vk', 0), 
            self.hook
        )
        separate_layout.addWidget(self.input_mute)
        separate_layout.addWidget(self.input_unmute)
        separate_layout.addStretch()
        self.stack.addWidget(self.page_separate)
        
        layout.addWidget(self.stack)
        
        # Set Initial State
        current_mode = self.audio.hotkey_config.get('mode', 'toggle')
        if current_mode == 'separate':
            self.mode_separate.setChecked(True)
            self.stack.setCurrentIndex(1)
        else:
            self.mode_toggle.setChecked(True)
            self.stack.setCurrentIndex(0)
            
        self.mode_group_btn.idToggled.connect(self.stack.setCurrentIndex)

    def get_config(self):
        """
        Retrieves the current hotkey configuration.
        
        Returns:
            dict: Hotkey configuration dictionary.
        """
        mode = 'separate' if self.mode_separate.isChecked() else 'toggle'
        return {
            'mode': mode,
            'toggle': self.input_toggle.get_config(),
            'mute': self.input_mute.get_config(),
            'unmute': self.input_unmute.get_config()
        }
    
    def cleanup(self):
        """
        Cleans up child widgets.
        """
        self.input_toggle.cleanup()
        self.input_mute.cleanup()
        self.input_unmute.cleanup()
