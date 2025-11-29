import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QSpinBox, QCheckBox, QDialog, QTabWidget, QFileDialog, QLineEdit, QSlider, QComboBox)
from PySide6.QtCore import Qt
from winsound import Beep

from ..core import signals
from .devices import DeviceSelectionWidget
from .hotkeys import HotkeySettingsWidget

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
        
        # Size Control (Slider + SpinBox)
        # Base size 150px
        base_size = 150
        
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(50, 200) # 50% to 200%
        
        self.px_spin = QSpinBox()
        self.px_spin.setRange(int(base_size * 0.5), int(base_size * 2.0))
        self.px_spin.setSuffix(" px")
        
        # Initial Value
        current_size = self.audio.osd_config.get('size', 150)
        self.px_spin.setValue(current_size)
        # Calculate scale from size
        current_scale = int((current_size / base_size) * 100)
        self.scale_slider.setValue(current_scale)
        
        # Sync Logic
        self.scale_slider.valueChanged.connect(lambda v: self.px_spin.setValue(int(base_size * v / 100)))
        self.px_spin.valueChanged.connect(lambda v: self.scale_slider.setValue(int((v / base_size) * 100)))
        
        size_layout = QHBoxLayout()
        size_layout.addWidget(self.scale_slider)
        size_layout.addWidget(self.px_spin)
        
        # Position Control
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(["Top", "Center", "Bottom"])
        
        # Map config position to combo
        current_pos = self.audio.osd_config.get('position', 'Bottom-Center')
        if "Top" in current_pos: self.pos_combo.setCurrentText("Top")
        elif "Bottom" in current_pos: self.pos_combo.setCurrentText("Bottom")
        else: self.pos_combo.setCurrentText("Center")
        
        layout.addRow(self.enabled_cb)
        layout.addRow("Size:", size_layout)
        layout.addRow("Position:", self.pos_combo)
        
    def get_config(self):
        """
        Retrieves the current OSD configuration.
        
        Returns:
            dict: OSD configuration dictionary.
        """
        # Map combo back to full string if needed, or just use simple string
        # MetroOSD logic handles "Top", "Bottom", else Center.
        # But "Bottom" usually implies Bottom-Center.
        # Let's stick to "Bottom-Center" for bottom to preserve the offset logic if any.
        pos_map = {
            "Top": "Top-Center",
            "Center": "Center",
            "Bottom": "Bottom-Center"
        }
        
        return {
            'enabled': self.enabled_cb.isChecked(),
            'size': self.px_spin.value(),
            'duration': 1500, # Default
            'position': pos_map.get(self.pos_combo.currentText(), "Bottom-Center")
        }

class OverlaySettingsWidget(QWidget):
    """
    Widget for configuring the Persistent Overlay.
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
        
        self.enabled_cb = QCheckBox("Enable Persistent Overlay")
        self.enabled_cb.setChecked(self.audio.persistent_overlay.get('enabled', False))
        
        self.vu_cb = QCheckBox("Show Voice Activity Meter")
        self.vu_cb.setChecked(self.audio.persistent_overlay.get('show_vu', False))
        
        self.locked_cb = QCheckBox("Lock Position")
        self.locked_cb.setChecked(self.audio.persistent_overlay.get('locked', False))
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(self.audio.persistent_overlay.get('opacity', 80))
        
        # Size Control (Slider + SpinBox)
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(50, 200)
        self.scale_slider.setValue(self.audio.persistent_overlay.get('scale', 100))
        
        self.px_spin = QSpinBox()
        self.px_spin.setRange(20, 80) # 50% to 200% of 40px
        self.px_spin.setSuffix(" px")
        # Initial value
        initial_scale = self.audio.persistent_overlay.get('scale', 100)
        self.px_spin.setValue(int(40 * initial_scale / 100))
        
        # Sync Logic
        self.scale_slider.valueChanged.connect(lambda v: self.px_spin.setValue(int(40 * v / 100)))
        self.px_spin.valueChanged.connect(lambda v: self.scale_slider.setValue(int(v * 100 / 40)))
        
        size_layout = QHBoxLayout()
        size_layout.addWidget(self.scale_slider)
        size_layout.addWidget(self.px_spin)
        
        # Position Mode
        self.pos_mode_combo = QComboBox()
        modes = [
            "Custom",
            "Top-Left", "Top-Center", "Top-Right",
            "Middle-Left", "Center", "Middle-Right",
            "Bottom-Left", "Bottom-Center", "Bottom-Right"
        ]
        self.pos_mode_combo.addItems(modes)
        current_mode = self.audio.persistent_overlay.get('position_mode', 'Custom')
        self.pos_mode_combo.setCurrentText(current_mode)
        
        layout.addRow(self.enabled_cb)
        layout.addRow(self.vu_cb)
        layout.addRow(self.locked_cb)
        layout.addRow("Position:", self.pos_mode_combo)
        layout.addRow("Size (Height):", size_layout)
        layout.addRow("Opacity:", self.opacity_slider)

    def get_config(self):
        """
        Retrieves the current overlay configuration.
        
        Returns:
            dict: Overlay configuration dictionary.
        """
        return {
            'enabled': self.enabled_cb.isChecked(),
            'show_vu': self.vu_cb.isChecked(),
            'locked': self.locked_cb.isChecked(),
            'position_mode': self.pos_mode_combo.currentText(),
            'scale': self.scale_slider.value(),
            'opacity': self.opacity_slider.value(),
            'x': self.audio.persistent_overlay.get('x', 100),
            'y': self.audio.persistent_overlay.get('y', 100)
        }

from PySide6.QtCore import Qt, Signal
from winsound import Beep

# ... (imports)

class SettingsDialog(QDialog):
    """
    Main settings dialog container.
    """
    settings_applied = Signal()

    def __init__(self, audio_controller, hook_thread, parent=None):
        """
        Initializes the settings dialog.
        
        Args:
            audio_controller (AudioController): The main audio controller instance.
            hook_thread (HookThread): The thread managing the keyboard hook.
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        self.audio = audio_controller
        self.hook_thread = hook_thread
        self.setWindowTitle("MicMute Settings")
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # Tab 1: General (Devices)
        self.device_widget = DeviceSelectionWidget()
        self.tabs.addTab(self.device_widget, "Devices")
        
        # Tab 2: Audio (Beeps)
        self.beep_widget = BeepSettingsWidget(self.audio)
        self.tabs.addTab(self.beep_widget, "Audio Feedback")
        
        # Tab 3: Hotkeys
        # We need the hook instance from the thread
        self.hotkey_widget = HotkeySettingsWidget(self.audio, self.hook_thread.hook)
        self.tabs.addTab(self.hotkey_widget, "Hotkeys")
        
        # Tab 4: Misc (AFK, OSD, Overlay)
        misc_widget = QWidget()
        misc_layout = QVBoxLayout(misc_widget)
        
        self.afk_widget = AfkSettingsWidget(self.audio)
        misc_layout.addWidget(self.afk_widget)
        
        self.osd_widget = OsdSettingsWidget(self.audio)
        misc_layout.addWidget(self.osd_widget)
        
        self.overlay_widget = OverlaySettingsWidget(self.audio)
        misc_layout.addWidget(self.overlay_widget)
        
        misc_layout.addStretch()
        self.tabs.addTab(misc_widget, "Misc & Overlay")
        
        layout.addWidget(self.tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.apply_settings)
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

    def apply_settings(self):
        """
        Saves all settings without closing the dialog.
        """
        # 1. Sync IDs
        new_sync_ids = self.device_widget.get_sync_ids()
        self.audio.update_sync_ids(new_sync_ids)
        
        # 2. Beep/Sound
        beep_sound_config = self.beep_widget.get_config()
        self.audio.update_beep_config(beep_sound_config['beep'])
        self.audio.update_sound_config(beep_sound_config['sound'])
        
        # 3. Hotkeys
        new_hotkey_config = self.hotkey_widget.get_config()
        self.audio.update_hotkey_config(new_hotkey_config)
        # Update hook immediately
        if self.hook_thread.hook:
            self.hook_thread.hook.update_config(new_hotkey_config)
            
        # 4. AFK
        new_afk_config = self.afk_widget.get_config()
        self.audio.update_afk_config(new_afk_config)
        
        # 5. OSD
        new_osd_config = self.osd_widget.get_config()
        self.audio.update_osd_config(new_osd_config)
        
        # 6. Overlay
        new_overlay_config = self.overlay_widget.get_config()
        self.audio.update_persistent_overlay(new_overlay_config)
        
        self.settings_applied.emit()
    
    def closeEvent(self, event):
        """
        Handles the close event to clean up resources.
        
        Args:
            event (QCloseEvent): The close event.
        """
        self.hotkey_widget.cleanup()
        super().closeEvent(event)
