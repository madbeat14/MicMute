import ctypes
import gc
from PySide6.QtGui import QColor, QAction
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QLabel, QMessageBox, QWidget,
                             QGroupBox, QFormLayout, QSpinBox, QComboBox, QSystemTrayIcon,
                             QTabWidget, QCheckBox, QRadioButton, QButtonGroup, QStackedWidget,
                             QScrollArea, QMenu, QFileDialog, QLineEdit, QSlider)
from PySide6.QtCore import Qt, QObject, Signal
from pycaw.pycaw import AudioUtilities
from winsound import Beep

from .core import signals, audio
from .utils import VK_LMENU, VK_RMENU, set_default_device

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

# --- WIDGETS ---

class DeviceSelectionWidget(QWidget):
    """
    Widget for listing and selecting audio devices.
    """
    def __init__(self, parent=None):
        """
        Initializes the device selection widget.
        
        Args:
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Table Setup
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Def", "Device Name", "Status", "Link Mute"])
        
        # Column Resizing
        header = self.table.horizontalHeader()
        # Default Indicator
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        # Name
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        # Status
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        # Sync
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh List")
        self.refresh_btn.clicked.connect(self.refresh_devices)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Row -> Device ID
        self.devices_map = {}
        # ID -> Device Object (for status updates)
        self.device_objects = {}
        
        # Listen for external updates
        signals.update_icon.connect(self.update_status_ui)
        signals.device_changed.connect(lambda _: self.refresh_devices())
        
        self.refresh_devices()

    def refresh_devices(self):
        """
        Refreshes the list of available audio devices.
        """
        self.table.setRowCount(0)
        self.devices_map.clear()
        self.device_objects.clear()
        
        try:
            # 1. Get All Devices (Wrappers)
            all_devices_raw = AudioUtilities.GetAllDevices()
            
            # 2. Get Capture IDs for filtering
            enumerator = AudioUtilities.GetDeviceEnumerator()
            # eCapture, eAll
            collection = enumerator.EnumAudioEndpoints(1, 1)
            count = collection.GetCount()
            capture_ids = set()
            for i in range(count):
                dev = collection.Item(i)
                capture_ids.add(dev.GetId())
            
            # Filter
            all_devices = []
            for dev in all_devices_raw:
                if dev.id in capture_ids:
                    all_devices.append(dev)
                    self.device_objects[dev.id] = dev
            
            # 3. Identify Default/Master
            # Always prioritize the actual Windows System Default
            try:
                # eCapture, eConsole
                default_dev = enumerator.GetDefaultAudioEndpoint(1, 0)
                windows_default_id = default_dev.GetId()
                
                # Update App Master to match Windows Default
                # This ensures we always control/sync the actual system default
                if windows_default_id:
                    audio.set_device_by_id(windows_default_id)
                    master_id = windows_default_id
                else:
                    master_id = audio.device_id
            except:
                master_id = audio.device_id

            # Fallback if still no master
            if not master_id and all_devices:
                master_id = all_devices[0].id
                audio.set_device_by_id(master_id)
            
            # 4. Sort: Master first, then others
            master_dev = None
            other_devs = []
            
            for dev in all_devices:
                if dev.id == master_id:
                    master_dev = dev
                else:
                    other_devs.append(dev)
            
            sorted_devices = []
            if master_dev: sorted_devices.append(master_dev)
            sorted_devices.extend(other_devs)
            
            # 5. Populate Table
            for row, dev in enumerate(sorted_devices):
                dev_id = dev.id
                self.table.insertRow(row)
                self.devices_map[row] = dev_id
                
                is_master = (dev_id == master_id)
                
                # Col 0: Default Indicator
                def_item = QTableWidgetItem()
                if is_master:
                    # Star for default
                    def_item.setText("★")
                    def_item.setForeground(QColor("gold"))
                    def_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 0, def_item)
                
                # Col 1: Name
                name = dev.FriendlyName
                name_item = QTableWidgetItem(name)
                if is_master:
                    font = name_item.font()
                    font.setBold(True)
                    name_item.setFont(font)
                    name_item.setForeground(QColor("green"))
                self.table.setItem(row, 1, name_item)
                
                # Col 2: Status
                try:
                    is_muted = dev.EndpointVolume.GetMute()
                    status_str = "Muted" if is_muted else "Unmuted"
                except: status_str = "?"
                status_item = QTableWidgetItem(status_str)
                status_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, status_item)

                # Col 3: Sync Checkbox
                chk_widget = QWidget()
                chk_layout = QHBoxLayout(chk_widget)
                chk_layout.setContentsMargins(0,0,0,0)
                chk_layout.setAlignment(Qt.AlignCenter)
                chk = QCheckBox()
                
                if is_master:
                    chk.setChecked(True)
                    chk.setEnabled(False)
                else:
                    chk.setChecked(dev_id in audio.sync_ids)
                    chk.toggled.connect(lambda checked, did=dev_id: self.on_sync_toggled(did, checked))
                
                chk_layout.addWidget(chk)
                self.table.setCellWidget(row, 3, chk_widget)
                
        except Exception as e:
            if self.isVisible():
                QMessageBox.critical(self, "Error", f"Failed to list devices: {e}")
        finally:
            gc.collect()

    def on_sync_toggled(self, dev_id, checked):
        """
        Handles toggling of device synchronization.
        
        Args:
            dev_id (str): The ID of the device.
            checked (bool): New checked state.
        """
        if checked:
            if dev_id not in audio.sync_ids:
                audio.sync_ids.append(dev_id)
                audio.set_device_mute(dev_id, audio.get_mute_state())
        else:
            if dev_id in audio.sync_ids:
                audio.sync_ids.remove(dev_id)

    def show_context_menu(self, pos):
        """
        Shows context menu for device table items.
        
        Args:
            pos (QPoint): Position of the click.
        """
        item = self.table.itemAt(pos)
        if not item: return
        
        row = item.row()
        dev_id = self.devices_map.get(row)
        if not dev_id: return
        
        if row == 0: return
        
        menu = QMenu(self)
        action_default = QAction("Set as Default Device", self)
        action_default.triggered.connect(lambda: self.set_as_default(dev_id))
        menu.addAction(action_default)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def set_as_default(self, dev_id):
        """
        Sets the specified device as the system default.
        
        Args:
            dev_id (str): The ID of the device to set as default.
        """
        if set_default_device(dev_id):
            if audio.set_device_by_id(dev_id):
                self.refresh_devices()
            else:
                QMessageBox.warning(self, "Error", "Failed to set application device.")
        else:
            QMessageBox.warning(self, "Error", "Failed to set Windows default device.")

    def update_status_ui(self, is_muted):
        """
        Updates the mute status in the UI for all devices.
        
        Args:
            is_muted (bool): Global mute state (unused, checks individual devices).
        """
        for row in range(self.table.rowCount()):
            dev_id = self.devices_map.get(row)
            if not dev_id: continue
            
            dev = self.device_objects.get(dev_id)
            if dev:
                try:
                    muted = dev.EndpointVolume.GetMute()
                    status_str = "Muted" if muted else "Unmuted"
                    self.table.item(row, 2).setText(status_str)
                except: pass

    def get_sync_ids(self):
        """
        Retrieves the list of device IDs selected for synchronization.
        
        Returns:
            list: List of device ID strings.
        """
        ids = []
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 3)
            if widget:
                chk = widget.findChild(QCheckBox)
                if chk and chk.isChecked():
                    dev_id = self.devices_map.get(row)
                    if dev_id:
                        ids.append(dev_id)
        return ids
    
    def get_selected_device_id(self):
        """
        Placeholder for compatibility.
        
        Returns:
            None
        """
        return None

class BeepSettingsWidget(QWidget):
    """
    Widget for configuring beep sounds and custom audio files.
    """
    def __init__(self, audio_controller, parent=None):
        """
        Initializes the beep settings widget.
        
        Args:
            audio_controller (AudioController): The main audio controller instance.
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        self.audio = audio_controller
        layout = QVBoxLayout(self)
        
        # --- Custom Sounds ---
        sound_group = QGroupBox("Custom Sounds (Overrides Beep)")
        sound_layout = QFormLayout()
        
        # Mute Sound
        self.mute_path = QLineEdit()
        self.mute_path.setReadOnly(True)
        self.mute_path.setText(self.audio.sound_config.get('mute') or "")
        
        mute_btns = QHBoxLayout()
        self.btn_browse_mute = QPushButton("Browse")
        self.btn_browse_mute.clicked.connect(lambda: self.browse_sound('mute'))
        self.btn_play_mute = QPushButton("Preview")
        self.btn_play_mute.clicked.connect(lambda: self.preview_sound('mute'))
        mute_btns.addWidget(self.btn_browse_mute)
        mute_btns.addWidget(self.btn_play_mute)
        
        sound_layout.addRow("Mute Sound:", self.mute_path)
        sound_layout.addRow("", mute_btns)
        
        # Unmute Sound
        self.unmute_path = QLineEdit()
        self.unmute_path.setReadOnly(True)
        self.unmute_path.setText(self.audio.sound_config.get('unmute') or "")
        
        unmute_btns = QHBoxLayout()
        self.btn_browse_unmute = QPushButton("Browse")
        self.btn_browse_unmute.clicked.connect(lambda: self.browse_sound('unmute'))
        self.btn_play_unmute = QPushButton("Preview")
        self.btn_play_unmute.clicked.connect(lambda: self.preview_sound('unmute'))
        unmute_btns.addWidget(self.btn_browse_unmute)
        unmute_btns.addWidget(self.btn_play_unmute)
        
        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)

        # --- Beep Settings ---
        mute_group = QGroupBox("Fallback Beep Settings")
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
        
        mute_group.setLayout(mute_layout)
        layout.addWidget(mute_group)
        
        # Unmute Settings
        unmute_group = QGroupBox("Unmute Beep Settings")
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
        
        unmute_group.setLayout(unmute_layout)
        layout.addWidget(unmute_group)

    def browse_sound(self, sound_type):
        """
        Opens a file dialog to select a custom sound file.
        
        Args:
            sound_type (str): 'mute' or 'unmute'.
        """
        path, _ = QFileDialog.getOpenFileName(self, "Select Sound File", "", "Audio Files (*.wav *.mp3)")
        if path:
            if sound_type == 'mute':
                self.mute_path.setText(path)
            else:
                self.unmute_path.setText(path)

    def preview_sound(self, sound_type):
        """
        Previews the selected sound (custom or beep).
        
        Args:
            sound_type (str): 'mute' or 'unmute'.
        """
        # Temporarily use the path from UI to preview
        path = self.mute_path.text() if sound_type == 'mute' else self.unmute_path.text()
        if path and os.path.exists(path):
            # Use AudioController's player but set source manually
            from PySide6.QtCore import QUrl
            self.audio.player.setSource(QUrl.fromLocalFile(path))
            self.audio.player.setVolume(0.5)
            self.audio.player.play()
        else:
            # Fallback test beep
            if sound_type == 'mute': self.test_mute()
            else: self.test_unmute()

    def test_mute(self):
        """
        Plays the configured mute beep sequence.
        """
        freq = self.mute_freq.value()
        dur = self.mute_dur.value()
        count = self.mute_count.value()
        for _ in range(count):
            Beep(freq, dur)

    def test_unmute(self):
        """
        Plays the configured unmute beep sequence.
        """
        freq = self.unmute_freq.value()
        dur = self.unmute_dur.value()
        count = self.unmute_count.value()
        for _ in range(count):
            Beep(freq, dur)

    def get_config(self):
        """
        Retrieves the current beep and sound configuration.
        
        Returns:
            dict: Configuration dictionary.
        """
        return {
            'beep': {
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
            },
            'sound': {
                'mute': self.mute_path.text(),
                'unmute': self.unmute_path.text()
            }
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

class AfkSettingsWidget(QWidget):
    """
    Widget for configuring AFK (Away From Keyboard) timeout settings.
    """
    def __init__(self, audio_controller, parent=None):
        """
        Initializes the AFK settings widget.
        
        Args:
            audio_controller (AudioController): The main audio controller instance.
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        self.audio = audio_controller
        layout = QFormLayout(self)
        
        self.enabled_cb = QCheckBox("Enable AFK Timeout")
        self.enabled_cb.setChecked(self.audio.afk_config.get('enabled', False))
        
        self.timeout_spin = QSpinBox()
        # 10s to 1 hour
        self.timeout_spin.setRange(10, 3600)
        self.timeout_spin.setValue(self.audio.afk_config.get('timeout', 60))
        self.timeout_spin.setSuffix(" seconds")
        
        layout.addRow(self.enabled_cb)
        layout.addRow("Timeout:", self.timeout_spin)
        
        # Enable/Disable spinbox based on checkbox
        self.timeout_spin.setEnabled(self.enabled_cb.isChecked())
        self.enabled_cb.toggled.connect(self.timeout_spin.setEnabled)

    def get_config(self):
        """
        Retrieves the current AFK configuration.
        
        Returns:
            dict: AFK configuration dictionary.
        """
        return {
            'enabled': self.enabled_cb.isChecked(),
            'timeout': self.timeout_spin.value()
        }

class OsdSettingsWidget(QWidget):
    """
    Widget for configuring On-Screen Display (OSD) settings.
    """
    def __init__(self, audio_controller, parent=None):
        """
        Initializes the OSD settings widget.
        
        Args:
            audio_controller (AudioController): The main audio controller instance.
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        self.audio = audio_controller
        layout = QFormLayout(self)
        
        self.enabled_cb = QCheckBox("Enable On-Screen Display (OSD)")
        self.enabled_cb.setChecked(self.audio.osd_config.get('enabled', False))
        
        # Size Control
        self.size_spin = QSpinBox()
        self.size_spin.setRange(50, 500)
        self.size_spin.setSingleStep(10)
        self.size_spin.setValue(self.audio.osd_config.get('size', 150))
        self.size_spin.setSuffix(" px")
        
        # Duration Control
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(500, 5000)
        self.duration_spin.setSingleStep(100)
        self.duration_spin.setValue(self.audio.osd_config.get('duration', 1500))
        self.duration_spin.setSuffix(" ms")
        
        # Position Control (9-Point)
        self.position_combo = QComboBox()
        positions = [
            "Top-Left", "Top-Center", "Top-Right",
            "Middle-Left", "Center", "Middle-Right",
            "Bottom-Left", "Bottom-Center", "Bottom-Right"
        ]
        self.position_combo.addItems(positions)
        self.position_combo.setCurrentText(self.audio.osd_config.get('position', 'Bottom-Center'))
        
        layout.addRow(self.enabled_cb)
        layout.addRow("Size:", self.size_spin)
        layout.addRow("Display Duration:", self.duration_spin)
        layout.addRow("Position:", self.position_combo)
        
    def get_config(self):
        """
        Retrieves the current OSD configuration.
        
        Returns:
            dict: OSD configuration dictionary.
        """
        return {
            'enabled': self.enabled_cb.isChecked(),
            'size': self.size_spin.value(),
            'duration': self.duration_spin.value(),
            'position': self.position_combo.currentText()
        }

class PersistentOverlaySettingsWidget(QWidget):
    """
    Widget for configuring the persistent overlay settings.
    """
    def __init__(self, audio_controller, parent=None):
        """
        Initializes the overlay settings widget.
        
        Args:
            audio_controller (AudioController): The main audio controller instance.
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        self.audio = audio_controller
        layout = QFormLayout(self)
        
        self.enabled_cb = QCheckBox("Show Persistent Microphone State")
        self.enabled_cb.setChecked(self.audio.persistent_overlay.get('enabled', False))
        
        self.vu_cb = QCheckBox("Show Voice Activity (VU Meter)")
        self.vu_cb.setChecked(self.audio.persistent_overlay.get('show_vu', False))
        
        # Device Selection
        self.device_combo = QComboBox()
        self.device_combo.addItem("Default Device", None)
        
        # Populate Devices
        try:
            devices = get_audio_devices()
            for dev in devices:
                self.device_combo.addItem(f"{dev['name']}", dev['id'])
        except: pass
            
        current_dev = self.audio.persistent_overlay.get('device_id')
        index = self.device_combo.findData(current_dev)
        if index >= 0:
            self.device_combo.setCurrentIndex(index)
        
        self.lock_cb = QCheckBox("Lock Overlay Position")
        self.lock_cb.setChecked(self.audio.persistent_overlay.get('locked', False))
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(self.audio.persistent_overlay.get('opacity', 80))
        
        # Position Control
        self.position_combo = QComboBox()
        positions = [
            "Top-Left", "Top-Center", "Top-Right",
            "Middle-Left", "Center", "Middle-Right",
            "Bottom-Left", "Bottom-Center", "Bottom-Right",
            "Custom"
        ]
        self.position_combo.addItems(positions)
        self.position_combo.setCurrentText(self.audio.persistent_overlay.get('position_mode', 'Custom'))
        
        # Sensitivity Control
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        # 1% to 50% threshold
        self.sensitivity_slider.setRange(1, 50)
        self.sensitivity_slider.setValue(self.audio.persistent_overlay.get('sensitivity', 5))
        self.sensitivity_label = QLabel(f"{self.sensitivity_slider.value()}%")
        self.sensitivity_slider.valueChanged.connect(lambda v: self.sensitivity_label.setText(f"{v}%"))
        
        layout.addRow(self.enabled_cb)
        layout.addRow(self.vu_cb)
        layout.addRow("Monitor Device:", self.device_combo)
        
        sens_layout = QHBoxLayout()
        sens_layout.addWidget(self.sensitivity_slider)
        sens_layout.addWidget(self.sensitivity_label)
        layout.addRow("Voice Sensitivity:", sens_layout)
        
        layout.addRow(self.lock_cb)
        layout.addRow("Position:", self.position_combo)
        layout.addRow("Opacity:", self.opacity_slider)
        
        # Dependencies
        self.vu_cb.setEnabled(self.enabled_cb.isChecked())
        self.device_combo.setEnabled(self.enabled_cb.isChecked() and self.vu_cb.isChecked())
        self.lock_cb.setEnabled(self.enabled_cb.isChecked())
        self.opacity_slider.setEnabled(self.enabled_cb.isChecked())
        self.position_combo.setEnabled(self.enabled_cb.isChecked())
        self.sensitivity_slider.setEnabled(self.enabled_cb.isChecked() and self.vu_cb.isChecked())
        
        self.enabled_cb.toggled.connect(self.vu_cb.setEnabled)
        self.enabled_cb.toggled.connect(self.lock_cb.setEnabled)
        self.enabled_cb.toggled.connect(self.opacity_slider.setEnabled)
        self.enabled_cb.toggled.connect(self.position_combo.setEnabled)
        
        def update_sens_enable():
            is_vu = self.enabled_cb.isChecked() and self.vu_cb.isChecked()
            self.sensitivity_slider.setEnabled(is_vu)
            self.sensitivity_label.setEnabled(is_vu)
            self.device_combo.setEnabled(is_vu)
            
        self.enabled_cb.toggled.connect(update_sens_enable)
        self.vu_cb.toggled.connect(update_sens_enable)

    def get_config(self):
        """
        Retrieves the current overlay configuration.
        
        Returns:
            dict: Overlay configuration dictionary.
        """
        return {
            'enabled': self.enabled_cb.isChecked(),
            'show_vu': self.vu_cb.isChecked(),
            'device_id': self.device_combo.currentData(),
            'locked': self.lock_cb.isChecked(),
            'position_mode': self.position_combo.currentText(),
            'opacity': self.opacity_slider.value(),
            'sensitivity': self.sensitivity_slider.value(),
            'x': self.audio.persistent_overlay.get('x', 100),
            'y': self.audio.persistent_overlay.get('y', 100)
        }

# --- MAIN SETTINGS DIALOG ---
class SettingsDialog(QDialog):
    """
    Main settings dialog containing all configuration tabs.
    """
    def __init__(self, audio_controller, hook, parent=None):
        """
        Initializes the settings dialog.
        
        Args:
            audio_controller (AudioController): The main audio controller instance.
            hook (NativeKeyboardHook): The keyboard hook instance.
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        self.audio = audio_controller
        self.hook = hook
        self.setWindowTitle("MicMute Settings")
        self.resize(500, 650)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # Tab 1: General (Device Selection)
        self.device_widget = DeviceSelectionWidget()
        self.tabs.addTab(self.device_widget, "General")
        
        # Tab 2: Audio (Beeps & Sounds)
        self.beep_widget = BeepSettingsWidget(self.audio)
        self.tabs.addTab(self.beep_widget, "Audio")
        
        # Tab 3: Visuals (OSD & Overlay)
        self.visuals_tab = QWidget()
        vis_layout = QVBoxLayout(self.visuals_tab)
        
        vis_layout.addWidget(QLabel("<b>Notification OSD</b>"))
        self.osd_widget = OsdSettingsWidget(self.audio)
        vis_layout.addWidget(self.osd_widget)
        
        vis_layout.addSpacing(10)
        vis_layout.addWidget(QLabel("<b>Persistent Overlay</b>"))
        self.overlay_widget = PersistentOverlaySettingsWidget(self.audio)
        vis_layout.addWidget(self.overlay_widget)
        
        vis_layout.addStretch()
        self.tabs.addTab(self.visuals_tab, "Visuals")
        
        # Tab 4: Misc (Hotkey + AFK)
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
        """
        Saves all settings from all tabs to the configuration.
        """
        # 1. Device
        new_dev_id = self.device_widget.get_selected_device_id()
        if new_dev_id:
            self.audio.set_device_by_id(new_dev_id)
            
        # 1b. Sync IDs
        self.audio.update_sync_ids(self.device_widget.get_sync_ids())
        
        # 2. Beeps
        audio_cfg = self.beep_widget.get_config()
        self.audio.update_beep_config(audio_cfg['beep'])
        self.audio.update_sound_config(audio_cfg['sound'])
        
        # 3. Hotkey
        new_hotkey = self.hotkey_widget.get_config()
        self.audio.update_hotkey_config(new_hotkey)
        self.hook.update_config(new_hotkey)
        
        # 4. AFK
        self.audio.update_afk_config(self.afk_widget.get_config())
        
        # 5. Visuals (OSD & Overlay)
        self.audio.update_osd_config(self.osd_widget.get_config())
        self.audio.update_persistent_overlay(self.overlay_widget.get_config())
        
        self.accept()
        
    def closeEvent(self, event):
        """
        Handles the close event to ensure cleanup.
        
        Args:
            event (QCloseEvent): The close event.
        """
        self.hotkey_widget.cleanup()
        super().closeEvent(event)

# --- LEGACY WRAPPERS (For backwards compatibility / Tray Actions) ---
class DeviceSelectionDialog(QDialog):
    """
    Legacy dialog for selecting a microphone (used by tray menu).
    """
    def __init__(self, parent=None):
        """
        Initializes the device selection dialog.
        
        Args:
            parent (QWidget, optional): Parent widget.
        """
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
        """
        Validates and accepts the selected device.
        """
        self.selected_device_id = self.widget.get_selected_device_id()
        if not self.selected_device_id:
            QMessageBox.warning(self, "No Selection", "Please select a device.")
            return
        self.accept()
