import ctypes
import gc
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QLabel, QMessageBox, QWidget,
                             QGroupBox, QFormLayout, QSpinBox, QComboBox, QSystemTrayIcon,
                             QTabWidget, QCheckBox, QRadioButton, QButtonGroup, QStackedWidget)
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QColor
from pycaw.pycaw import AudioUtilities
from winsound import Beep

from .core import signals, audio
from .utils import VK_LMENU, VK_RMENU

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

# --- THEME DETECTION (EVENT DRIVEN) ---
class ThemeListener(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
    
    def nativeEvent(self, eventType, message):
        msg = ctypes.wintypes.MSG.from_address(message.__int__())
        if msg.message == 0x001A: # WM_SETTINGCHANGE
            signals.theme_changed.emit()
        return super().nativeEvent(eventType, message)

# --- WIDGETS ---

class DeviceSelectionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the microphone to control:"))
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Device Name", "Status", "Mute State"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh List")
        self.refresh_btn.clicked.connect(self.refresh_devices)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.devices_map = {}
        self.refresh_devices()

    def refresh_devices(self):
        self.table.setRowCount(0)
        self.devices_map.clear()
        enumerator = None
        collection = None
        try:
            enumerator = AudioUtilities.GetDeviceEnumerator()
            try:
                default_dev = enumerator.GetDefaultAudioEndpoint(1, 0)
                default_id = default_dev.GetId()
            except: default_id = None
            collection = enumerator.EnumAudioEndpoints(1, 1)
            count = collection.GetCount()
            all_devices = AudioUtilities.GetAllDevices()
            capture_ids = set()
            for i in range(count):
                dev = collection.Item(i)
                capture_ids.add(dev.GetId())
            
            row = 0
            for dev in all_devices:
                if dev.id not in capture_ids: continue
                self.table.insertRow(row)
                name_item = QTableWidgetItem(dev.FriendlyName)
                self.table.setItem(row, 0, name_item)
                status_str = "Default" if dev.id == default_id else ""
                status_item = QTableWidgetItem(status_str)
                if dev.id == default_id:
                    status_item.setForeground(QColor("green"))
                    name_item.setForeground(QColor("green"))
                self.table.setItem(row, 1, status_item)
                try:
                    is_muted = dev.EndpointVolume.GetMute()
                    mute_str = "Muted" if is_muted else "Active"
                except: mute_str = "Unknown"
                self.table.setItem(row, 2, QTableWidgetItem(mute_str))
                self.devices_map[row] = dev.id
                
                # Highlight current selection
                if audio.device_id and dev.id == audio.device_id:
                     self.table.selectRow(row)
                
                row += 1
        except Exception as e:
            # Only show error if visible to avoid spamming if hidden
            if self.isVisible():
                QMessageBox.critical(self, "Error", f"Failed to list devices: {e}")
        finally:
            if collection: del collection
            if enumerator: del enumerator
            gc.collect()

    def get_selected_device_id(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        return self.devices_map.get(row)

class BeepSettingsWidget(QWidget):
    def __init__(self, audio_controller, parent=None):
        super().__init__(parent)
        self.audio = audio_controller
        layout = QVBoxLayout(self)
        
        # Mute Settings
        mute_group = QGroupBox("Mute Action")
        mute_layout = QFormLayout()
        
        self.mute_freq = QSpinBox()
        self.mute_freq.setRange(200, 5000)
        self.mute_freq.setValue(self.audio.beep_config['mute']['freq'])
        self.mute_freq.setSuffix(" Hz")
        mute_layout.addRow("Frequency:", self.mute_freq)
        
        self.mute_dur = QSpinBox()
        self.mute_dur.setRange(50, 1000)
        self.mute_dur.setValue(self.audio.beep_config['mute']['duration'])
        self.mute_dur.setSuffix(" ms")
        mute_layout.addRow("Duration:", self.mute_dur)
        
        self.mute_count = QSpinBox()
        self.mute_count.setRange(1, 5)
        self.mute_count.setValue(self.audio.beep_config['mute']['count'])
        mute_layout.addRow("Count:", self.mute_count)
        
        test_mute_btn = QPushButton("Test Mute Beep")
        test_mute_btn.clicked.connect(self.test_mute)
        mute_layout.addRow(test_mute_btn)
        
        mute_group.setLayout(mute_layout)
        layout.addWidget(mute_group)
        
        # Unmute Settings
        unmute_group = QGroupBox("Unmute Action")
        unmute_layout = QFormLayout()
        
        self.unmute_freq = QSpinBox()
        self.unmute_freq.setRange(200, 5000)
        self.unmute_freq.setValue(self.audio.beep_config['unmute']['freq'])
        self.unmute_freq.setSuffix(" Hz")
        unmute_layout.addRow("Frequency:", self.unmute_freq)
        
        self.unmute_dur = QSpinBox()
        self.unmute_dur.setRange(50, 1000)
        self.unmute_dur.setValue(self.audio.beep_config['unmute']['duration'])
        self.unmute_dur.setSuffix(" ms")
        unmute_layout.addRow("Duration:", self.unmute_dur)
        
        self.unmute_count = QSpinBox()
        self.unmute_count.setRange(1, 5)
        self.unmute_count.setValue(self.audio.beep_config['unmute']['count'])
        unmute_layout.addRow("Count:", self.unmute_count)
        
        test_unmute_btn = QPushButton("Test Unmute Beep")
        test_unmute_btn.clicked.connect(self.test_unmute)
        unmute_layout.addRow(test_unmute_btn)
        
        unmute_group.setLayout(unmute_layout)
        layout.addWidget(unmute_group)

    def test_mute(self):
        freq = self.mute_freq.value()
        dur = self.mute_dur.value()
        count = self.mute_count.value()
        for _ in range(count):
            Beep(freq, dur)

    def test_unmute(self):
        freq = self.unmute_freq.value()
        dur = self.unmute_dur.value()
        count = self.unmute_count.value()
        for _ in range(count):
            Beep(freq, dur)

    def get_config(self):
        return {
            'mute': {
                'freq': self.mute_freq.value(),
                'duration': self.mute_dur.value(),
                'count': self.mute_count.value()
            },
            'unmute': {
                'freq': self.unmute_freq.value(),
                'duration': self.unmute_dur.value(),
                'count': self.unmute_count.value()
            }
        }

class SingleHotkeyInputWidget(QWidget):
    def __init__(self, label_text, initial_vk, hook, parent=None):
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
        self.current_vk = self.combo.itemData(index)

    def start_capture(self):
        self.capture_btn.setText("...")
        self.capture_btn.setEnabled(False)
        # We need a way to know WHICH widget requested capture.
        # For simplicity, we'll set a flag on the parent or use a shared state if needed.
        # But signals are global. We need to check if WE are the active capturer.
        self.is_capturing = True
        self.hook.start_recording()

    def on_key_recorded(self, vk):
        if not getattr(self, 'is_capturing', False):
            return
            
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
        name = VK_MAP.get(self.current_vk, f"Key {self.current_vk}")
        return {'vk': self.current_vk, 'name': name}
    
    def cleanup(self):
        try:
            signals.key_recorded.disconnect(self.on_key_recorded)
        except: pass

class HotkeySettingsWidget(QWidget):
    def __init__(self, audio_controller, hook, parent=None):
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
        mode = 'separate' if self.mode_separate.isChecked() else 'toggle'
        return {
            'mode': mode,
            'toggle': self.input_toggle.get_config(),
            'mute': self.input_mute.get_config(),
            'unmute': self.input_unmute.get_config()
        }
    
    def cleanup(self):
        self.input_toggle.cleanup()
        self.input_mute.cleanup()
        self.input_unmute.cleanup()

class AfkSettingsWidget(QWidget):
    def __init__(self, audio_controller, parent=None):
        super().__init__(parent)
        self.audio = audio_controller
        layout = QFormLayout(self)
        
        self.enabled_cb = QCheckBox("Enable AFK Timeout")
        self.enabled_cb.setChecked(self.audio.afk_config.get('enabled', False))
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 3600) # 10s to 1 hour
        self.timeout_spin.setValue(self.audio.afk_config.get('timeout', 60))
        self.timeout_spin.setSuffix(" seconds")
        
        layout.addRow(self.enabled_cb)
        layout.addRow("Timeout:", self.timeout_spin)
        
        # Enable/Disable spinbox based on checkbox
        self.timeout_spin.setEnabled(self.enabled_cb.isChecked())
        self.enabled_cb.toggled.connect(self.timeout_spin.setEnabled)

    def get_config(self):
        return {
            'enabled': self.enabled_cb.isChecked(),
            'timeout': self.timeout_spin.value()
        }

# --- MAIN SETTINGS DIALOG ---
class SettingsDialog(QDialog):
    def __init__(self, audio_controller, hook, parent=None):
        super().__init__(parent)
        self.audio = audio_controller
        self.hook = hook
        self.setWindowTitle("MicMute Settings")
        self.resize(500, 600)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # Tab 1: General (Device Selection)
        self.device_widget = DeviceSelectionWidget()
        self.tabs.addTab(self.device_widget, "General")
        
        # Tab 2: Audio (Beeps)
        self.beep_widget = BeepSettingsWidget(self.audio)
        self.tabs.addTab(self.beep_widget, "Audio")
        
        # Tab 3: Misc (Hotkey + AFK)
        self.misc_tab = QWidget()
        misc_layout = QVBoxLayout(self.misc_tab)
        
        misc_layout.addWidget(QLabel("<b>Hotkey Settings</b>"))
        self.hotkey_widget = HotkeySettingsWidget(self.audio, self.hook)
        misc_layout.addWidget(self.hotkey_widget)
        
        misc_layout.addSpacing(10)
        misc_layout.addWidget(QLabel("<b>AFK Timeout</b>"))
        self.afk_widget = AfkSettingsWidget(self.audio)
        misc_layout.addWidget(self.afk_widget)
        
        misc_layout.addStretch()
        self.tabs.addTab(self.misc_tab, "Misc")
        
        layout.addWidget(self.tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setDefault(True)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def save_settings(self):
        # 1. Device
        new_dev_id = self.device_widget.get_selected_device_id()
        if new_dev_id:
            self.audio.set_device_by_id(new_dev_id)
        
        # 2. Beeps
        self.audio.update_beep_config(self.beep_widget.get_config())
        
        # 3. Hotkey
        new_hotkey = self.hotkey_widget.get_config()
        self.audio.update_hotkey_config(new_hotkey)
        self.hook.update_config(new_hotkey)
        
        # 4. AFK
        self.audio.update_afk_config(self.afk_widget.get_config())
        
        self.accept()
        
    def closeEvent(self, event):
        self.hotkey_widget.cleanup()
        super().closeEvent(event)

# --- LEGACY WRAPPERS (For backwards compatibility / Tray Actions) ---
class DeviceSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Microphone")
        self.resize(600, 400)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        layout = QVBoxLayout(self)
        self.widget = DeviceSelectionWidget()
        layout.addWidget(self.widget)
        
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        select_btn = QPushButton("Select")
        select_btn.clicked.connect(self.accept_selection)
        select_btn.setDefault(True)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(select_btn)
        layout.addLayout(btn_layout)
        
        self.selected_device_id = None

    def accept_selection(self):
        self.selected_device_id = self.widget.get_selected_device_id()
        if not self.selected_device_id:
            QMessageBox.warning(self, "No Selection", "Please select a device.")
            return
        self.accept()
