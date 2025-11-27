import ctypes
import gc
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QLabel, QMessageBox, QWidget,
                             QGroupBox, QFormLayout, QSpinBox, QComboBox, QSystemTrayIcon)
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

# --- HOTKEY SETTINGS DIALOG ---
class HotkeySettingsDialog(QDialog):
    def __init__(self, audio_controller, hook, parent=None):
        super().__init__(parent)
        self.audio = audio_controller
        self.hook = hook
        self.setWindowTitle("Hotkey Settings")
        self.resize(400, 200)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        layout = QVBoxLayout(self)
        
        # Current Hotkey Display
        self.current_vk = self.audio.hotkey_config['vk']
        
        # Dropdown
        layout.addWidget(QLabel("Select Hotkey from List:"))
        self.combo = QComboBox()
        self.vk_items = []
        
        # Sort by name for easier finding
        sorted_vks = sorted(VK_MAP.items(), key=lambda item: item[1])
        
        for vk, name in sorted_vks:
            self.combo.addItem(f"{name}", vk)
            self.vk_items.append(vk)
            
        # Add current custom if not in map
        if self.current_vk not in VK_MAP:
            self.combo.addItem(f"Custom Key ({self.current_vk})", self.current_vk)
            self.vk_items.append(self.current_vk)
            
        # Select current
        index = self.combo.findData(self.current_vk)
        if index >= 0:
            self.combo.setCurrentIndex(index)
            
        self.combo.currentIndexChanged.connect(self.on_combo_change)
        layout.addWidget(self.combo)
        
        layout.addSpacing(10)
        
        # Capture Button
        layout.addWidget(QLabel("Or press a key to set:"))
        self.capture_btn = QPushButton("Click to Set Hotkey")
        self.capture_btn.clicked.connect(self.start_capture)
        layout.addWidget(self.capture_btn)
        
        layout.addStretch()
        
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
        
        signals.key_recorded.connect(self.on_key_recorded)

    def on_combo_change(self, index):
        self.current_vk = self.combo.itemData(index)

    def start_capture(self):
        self.capture_btn.setText("Press any key...")
        self.capture_btn.setEnabled(False)
        self.hook.start_recording()

    def on_key_recorded(self, vk):
        self.hook.stop_recording()
        self.current_vk = vk
        self.capture_btn.setText("Click to Set Hotkey")
        self.capture_btn.setEnabled(True)
        
        # Update Combo
        name = VK_MAP.get(vk, f"Key {vk}")
        index = self.combo.findData(vk)
        if index == -1:
            self.combo.addItem(name, vk)
            index = self.combo.count() - 1
        self.combo.setCurrentIndex(index)

    def save_settings(self):
        name = VK_MAP.get(self.current_vk, f"Key {self.current_vk}")
        self.audio.update_hotkey_config({'vk': self.current_vk, 'name': name})
        self.hook.set_target_vk(self.current_vk)
        self.accept()
        
    def closeEvent(self, event):
        self.hook.stop_recording()
        try:
            signals.key_recorded.disconnect(self.on_key_recorded)
        except: pass
        super().closeEvent(event)

# --- BEEP SETTINGS DIALOG ---
class BeepSettingsDialog(QDialog):
    def __init__(self, audio_controller, parent=None):
        super().__init__(parent)
        self.audio = audio_controller
        self.setWindowTitle("Beep Settings")
        self.resize(400, 500)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
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

    def save_settings(self):
        new_config = {
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
        self.audio.update_beep_config(new_config)
        self.accept()

# --- DEVICE SELECTION DIALOG ---
class DeviceSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Microphone")
        self.resize(600, 400)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.selected_device_id = None
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the microphone you want to control with hotkeys:"))
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Device Name", "Status", "Mute State"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_devices)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        self.select_btn = QPushButton("Select")
        self.select_btn.clicked.connect(self.accept_selection)
        self.select_btn.setDefault(True)
        btn_layout.addWidget(self.select_btn)
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
                row += 1
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to list devices: {e}")
        finally:
            if collection: del collection
            if enumerator: del enumerator
            gc.collect()

    def accept_selection(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a device.")
            return
        row = selected_rows[0].row()
        self.selected_device_id = self.devices_map.get(row)
        self.accept()
