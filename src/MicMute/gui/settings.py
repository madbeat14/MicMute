import os
import shutil
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QSpinBox, QCheckBox, QDialog, QTabWidget, QFileDialog, QLineEdit, QSlider, QComboBox)
from PySide6.QtCore import Qt
from winsound import Beep

from ..core import signals
from ..utils import get_external_sound_dir
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
        self.pending_sounds = {} # Stores full paths of newly selected files
        
        layout = QVBoxLayout(self)
        
        # --- Audio Mode Selection ---
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Audio Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Beeps", "Custom Sounds"])
        
        # Set current mode
        current_mode = self.audio.audio_mode
        self.mode_combo.setCurrentText("Custom Sounds" if current_mode == 'custom' else "Beeps")
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        
        layout.addLayout(mode_layout)
        
        # --- Custom Sounds ---
        self.sound_group = QGroupBox("Custom Sounds")
        sound_layout = QFormLayout()
        
        # Mute Sound
        self.mute_path = QLineEdit()
        self.mute_path.setReadOnly(True)
        # Show only basename
        mute_cfg = self.audio.sound_config.get('mute', {})
        mute_file = mute_cfg.get('file') if isinstance(mute_cfg, dict) else mute_cfg
        self.mute_path.setText(os.path.basename(mute_file) if mute_file else "")
        
        mute_btns = QHBoxLayout()
        self.btn_browse_mute = QPushButton("Browse")
        self.btn_browse_mute.clicked.connect(lambda: self.browse_sound('mute'))
        self.btn_play_mute = QPushButton("Preview")
        self.btn_play_mute.clicked.connect(lambda: self.preview_sound('mute'))
        mute_btns.addWidget(self.btn_browse_mute)
        mute_btns.addWidget(self.btn_play_mute)
        
        # Mute Volume
        self.mute_vol_slider = QSlider(Qt.Horizontal)
        self.mute_vol_slider.setRange(0, 200)
        self.mute_vol_spin = QSpinBox()
        self.mute_vol_spin.setRange(0, 200)
        self.mute_vol_spin.setSuffix("%")
        
        mute_vol = mute_cfg.get('volume', 50) if isinstance(mute_cfg, dict) else 50
        self.mute_vol_slider.setValue(mute_vol)
        self.mute_vol_spin.setValue(mute_vol)
        
        self.mute_vol_slider.valueChanged.connect(self.mute_vol_spin.setValue)
        self.mute_vol_spin.valueChanged.connect(self.mute_vol_slider.setValue)
        
        mute_vol_layout = QHBoxLayout()
        mute_vol_layout.addWidget(self.mute_vol_slider)
        mute_vol_layout.addWidget(self.mute_vol_spin)
        
        sound_layout.addRow("Mute Sound:", self.mute_path)
        sound_layout.addRow("", mute_btns)
        sound_layout.addRow("Volume:", mute_vol_layout)
        
        # Unmute Sound
        self.unmute_path = QLineEdit()
        self.unmute_path.setReadOnly(True)
        # Show only basename
        unmute_cfg = self.audio.sound_config.get('unmute', {})
        unmute_file = unmute_cfg.get('file') if isinstance(unmute_cfg, dict) else unmute_cfg
        self.unmute_path.setText(os.path.basename(unmute_file) if unmute_file else "")
        
        unmute_btns = QHBoxLayout()
        self.btn_browse_unmute = QPushButton("Browse")
        self.btn_browse_unmute.clicked.connect(lambda: self.browse_sound('unmute'))
        self.btn_play_unmute = QPushButton("Preview")
        self.btn_play_unmute.clicked.connect(lambda: self.preview_sound('unmute'))
        unmute_btns.addWidget(self.btn_browse_unmute)
        unmute_btns.addWidget(self.btn_play_unmute)
        
        # Unmute Volume
        self.unmute_vol_slider = QSlider(Qt.Horizontal)
        self.unmute_vol_slider.setRange(0, 200)
        self.unmute_vol_spin = QSpinBox()
        self.unmute_vol_spin.setRange(0, 200)
        self.unmute_vol_spin.setSuffix("%")
        
        unmute_vol = unmute_cfg.get('volume', 50) if isinstance(unmute_cfg, dict) else 50
        self.unmute_vol_slider.setValue(unmute_vol)
        self.unmute_vol_spin.setValue(unmute_vol)
        
        self.unmute_vol_slider.valueChanged.connect(self.unmute_vol_spin.setValue)
        self.unmute_vol_spin.valueChanged.connect(self.unmute_vol_slider.setValue)
        
        unmute_vol_layout = QHBoxLayout()
        unmute_vol_layout.addWidget(self.unmute_vol_slider)
        unmute_vol_layout.addWidget(self.unmute_vol_spin)
        
        sound_layout.addRow("Unmute Sound:", self.unmute_path)
        sound_layout.addRow("", unmute_btns)
        sound_layout.addRow("Volume:", unmute_vol_layout)
        
        self.sound_group.setLayout(sound_layout)
        layout.addWidget(self.sound_group)

        # --- Beep Settings ---
        self.beep_group_mute = QGroupBox("Mute Beep Settings")
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
        
        self.beep_group_mute.setLayout(mute_layout)
        layout.addWidget(self.beep_group_mute)
        
        # Unmute Settings
        self.beep_group_unmute = QGroupBox("Unmute Beep Settings")
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
        
        self.beep_group_unmute.setLayout(unmute_layout)
        layout.addWidget(self.beep_group_unmute)
        
        # Logic
        self.mode_combo.currentTextChanged.connect(self.toggle_mode_visibility)
        self.mode_combo.currentTextChanged.connect(self.apply_mode)
        
        # Instant Apply for Volume (only connect to sliders to avoid duplicate triggers)
        self.mute_vol_slider.valueChanged.connect(self.apply_settings)
        self.unmute_vol_slider.valueChanged.connect(self.apply_settings)
        
        # Initial Visibility
        self.toggle_mode_visibility(self.mode_combo.currentText())

    def apply_settings(self):
        """
        Applies the current sound configuration to the audio controller.
        """
        # We only want to update the sound config, specifically volumes
        # But get_config returns everything. 
        # Ideally we should just update what changed, but updating all sound config is safe.
        # However, get_config does file copying which we don't want on every slider move if pending.
        # But pending sounds are only set on browse, so it's fine.
        
        # Optimization: Construct config directly to avoid file copy overhead if not needed
        # But get_config handles the structure logic.
        # Let's use get_config but be aware of copy. 
        # Actually, get_config clears pending_sounds, so it's a one-time copy.
        # If we drag slider, pending_sounds is empty, so no copy.
        
        full_config = self.get_config()
        self.audio.update_sound_config(full_config['sound'])

    def browse_sound(self, sound_type):
        """
        Opens a file dialog to select a custom sound file.
        Stores path in pending list and updates UI with basename.
        
        Args:
            sound_type (str): 'mute' or 'unmute'.
        """
        path, _ = QFileDialog.getOpenFileName(self, "Select Sound File", get_external_sound_dir(), "Audio Files (*.wav *.mp3)")
        if path:
            self.pending_sounds[sound_type] = path
            basename = os.path.basename(path)
            if sound_type == 'mute':
                self.mute_path.setText(basename)
            else:
                self.unmute_path.setText(basename)
            
            # Instant Apply
            self.apply_settings()

    def preview_sound(self, sound_type):
        """
        Previews the selected sound (custom or beep).
        
        Args:
            sound_type (str): 'mute' or 'unmute'.
        """
        # Check pending first
        path = self.pending_sounds.get(sound_type)
        if not path:
            # Check existing config
            cfg = self.audio.sound_config.get(sound_type, {})
            path = cfg.get('file') if isinstance(cfg, dict) else cfg
            
        if path:
            # If we have a pending path, we might want to play that specific file directly
            # to verify it BEFORE it is saved/copied.
            if os.path.exists(path):
                from PySide6.QtCore import QUrl
                if self.audio.player is None:
                    from PySide6.QtMultimedia import QSoundEffect
                    self.audio.player = QSoundEffect()
                self.audio.player.setSource(QUrl.fromLocalFile(path))
                vol = self.mute_vol_slider.value() if sound_type == 'mute' else self.unmute_vol_slider.value()
                self.audio.player.setVolume(vol / 100.0)
                self.audio.player.play()
                return

        # If no pending path, use the standard play_sound which handles fallbacks
        # This ensures that if the config says "mute2.wav" but it's missing,
        # the preview will trigger the fallback logic (and revert config).
        self.audio.play_sound(sound_type)

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

    def toggle_mode_visibility(self, mode_text):
        is_custom = mode_text == "Custom Sounds"
        self.sound_group.setVisible(is_custom)
        self.beep_group_mute.setVisible(not is_custom)
        self.beep_group_unmute.setVisible(not is_custom)

    def apply_mode(self, mode_text):
        mode = 'custom' if mode_text == "Custom Sounds" else 'beep'
        self.audio.update_audio_mode(mode)

    def on_setting_changed(self, key, value):
        if key == 'audio_mode':
            self.blockSignals(True)
            self.mode_combo.setCurrentText("Custom Sounds" if value == 'custom' else "Beeps")
            self.toggle_mode_visibility(self.mode_combo.currentText())
            self.blockSignals(False)
        elif key == 'beep_config':
            self.blockSignals(True)
            self.mute_freq.setValue(value['mute']['freq'])
            self.mute_dur.setValue(value['mute']['duration'])
            self.mute_count.setValue(value['mute']['count'])
            self.unmute_freq.setValue(value['unmute']['freq'])
            self.unmute_dur.setValue(value['unmute']['duration'])
            self.unmute_count.setValue(value['unmute']['count'])
            self.blockSignals(False)
        elif key == 'sound_config':
            # Update basenames and volumes
            self.blockSignals(True)
            
            mute_cfg = value.get('mute', {})
            mute_file = mute_cfg.get('file') if isinstance(mute_cfg, dict) else mute_cfg
            self.mute_path.setText(os.path.basename(mute_file) if mute_file else "")
            mute_vol = mute_cfg.get('volume', 50) if isinstance(mute_cfg, dict) else 50
            self.mute_vol_slider.setValue(mute_vol)
            self.mute_vol_spin.setValue(mute_vol)
            
            unmute_cfg = value.get('unmute', {})
            unmute_file = unmute_cfg.get('file') if isinstance(unmute_cfg, dict) else unmute_cfg
            self.unmute_path.setText(os.path.basename(unmute_file) if unmute_file else "")
            unmute_vol = unmute_cfg.get('volume', 50) if isinstance(unmute_cfg, dict) else 50
            self.unmute_vol_slider.setValue(unmute_vol)
            self.unmute_vol_spin.setValue(unmute_vol)
            
            self.blockSignals(False)

    def get_config(self):
        """
        Retrieves the current beep and sound configuration.
        Copies pending sounds to local storage.
        
        Returns:
            dict: Configuration dictionary.
        """
        # Process pending copies
        sounds_dir = get_external_sound_dir()
        try:
            os.makedirs(sounds_dir, exist_ok=True)
        except OSError as e:
            print(f"Warning: Could not create sounds directory: {e}")
            # Continue without copying - files will remain in pending
        
        final_sound_config = self.audio.sound_config.copy()
        
        for stype, source_path in self.pending_sounds.items():
            try:
                filename = os.path.basename(source_path)
                dest_path = os.path.join(sounds_dir, filename)
                shutil.copy2(source_path, dest_path)
                
                # Update the specific key in the dict
                if stype not in final_sound_config: final_sound_config[stype] = {}
                final_sound_config[stype]['file'] = dest_path
            except Exception as e:
                print(f"Error copying sound: {e}")
                # Fallback to source path
                if stype not in final_sound_config: final_sound_config[stype] = {}
                final_sound_config[stype]['file'] = source_path
        
        # Update volumes
        if 'mute' not in final_sound_config: final_sound_config['mute'] = {}
        final_sound_config['mute']['volume'] = self.mute_vol_slider.value()
        
        if 'unmute' not in final_sound_config: final_sound_config['unmute'] = {}
        final_sound_config['unmute']['volume'] = self.unmute_vol_slider.value()
        
        # Clear pending as they are now committed (if save is successful)
        # Note: If save fails later, we might lose pending state, but get_config implies intent to save.
        self.pending_sounds.clear()
        
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
            'sound': final_sound_config
        }

    def cleanup(self):
        """Disconnect signals to prevent crashes after widget destruction."""
        try:
            signals.setting_changed.disconnect(self.on_setting_changed)
        except (RuntimeError, TypeError):
            pass

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
        
        # Instant Apply
        self.enabled_cb.toggled.connect(self.apply_settings)
        self.timeout_spin.valueChanged.connect(self.apply_settings)
        
        # Sync
        signals.setting_changed.connect(self.on_setting_changed)

    def apply_settings(self):
        new_config = {
            'enabled': self.enabled_cb.isChecked(),
            'timeout': self.timeout_spin.value()
        }
        self.audio.update_afk_config(new_config)

    def on_setting_changed(self, key, value):
        if key == 'afk':
            self.blockSignals(True)
            self.enabled_cb.setChecked(value.get('enabled', False))
            self.timeout_spin.setValue(value.get('timeout', 60))
            self.blockSignals(False)

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

    def cleanup(self):
        """Disconnect signals to prevent crashes after widget destruction."""
        try:
            signals.setting_changed.disconnect(self.on_setting_changed)
        except (RuntimeError, TypeError):
            pass

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
        
        # Opacity Control
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(self.audio.osd_config.get('opacity', 80))
        
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(10, 100)
        self.opacity_spin.setSuffix("%")
        self.opacity_spin.setValue(self.audio.osd_config.get('opacity', 80))
        
        # Sync Opacity
        self.opacity_slider.valueChanged.connect(self.opacity_spin.setValue)
        self.opacity_spin.valueChanged.connect(self.opacity_slider.setValue)
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_spin)
        
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
        layout.addRow("Opacity:", opacity_layout)
        layout.addRow("Position:", self.pos_combo)
        
        # Instant Apply (only connect to sliders to avoid duplicate triggers)
        self.enabled_cb.toggled.connect(self.apply_settings)
        self.scale_slider.valueChanged.connect(self.apply_settings)
        self.pos_combo.currentTextChanged.connect(self.apply_settings)
        self.opacity_slider.valueChanged.connect(self.apply_settings)
        
        # Sync
        signals.setting_changed.connect(self.on_setting_changed)

    def apply_settings(self):
        pos_map = {
            "Top": "Top-Center",
            "Center": "Center",
            "Bottom": "Bottom-Center"
        }
        new_config = {
            'enabled': self.enabled_cb.isChecked(),
            'size': self.px_spin.value(),
            'duration': 1500,
            'position': pos_map.get(self.pos_combo.currentText(), "Bottom-Center"),
            'opacity': self.opacity_slider.value()
        }
        self.audio.update_osd_config(new_config)

    def on_setting_changed(self, key, value):
        if key == 'osd':
            self.blockSignals(True)
            self.enabled_cb.setChecked(value.get('enabled', False))
            self.px_spin.setValue(value.get('size', 150))
            self.opacity_slider.setValue(value.get('opacity', 80))
            self.opacity_spin.setValue(value.get('opacity', 80))
            
            # Map position back to combo
            current_pos = value.get('position', 'Bottom-Center')
            if "Top" in current_pos: self.pos_combo.setCurrentText("Top")
            elif "Bottom" in current_pos: self.pos_combo.setCurrentText("Bottom")
            else: self.pos_combo.setCurrentText("Center")
            
            self.blockSignals(False)
        
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
            'position': pos_map.get(self.pos_combo.currentText(), "Bottom-Center"),
            'opacity': self.opacity_slider.value()
        }

    def cleanup(self):
        """Disconnect signals to prevent crashes after widget destruction."""
        try:
            signals.setting_changed.disconnect(self.on_setting_changed)
        except (RuntimeError, TypeError):
            # Signal was not connected or already disconnected
            pass

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
        
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(10, 100)
        self.opacity_spin.setSuffix("%")
        self.opacity_spin.setValue(self.audio.persistent_overlay.get('opacity', 80))
        
        # Sync Opacity
        self.opacity_slider.valueChanged.connect(self.opacity_spin.setValue)
        self.opacity_spin.valueChanged.connect(self.opacity_slider.setValue)
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_spin)
        
        # Sensitivity Control
        self.sens_slider = QSlider(Qt.Horizontal)
        self.sens_slider.setRange(1, 100)
        self.sens_slider.setValue(self.audio.persistent_overlay.get('sensitivity', 5))
        
        self.sens_spin = QSpinBox()
        self.sens_spin.setRange(1, 100)
        self.sens_spin.setSuffix("%")
        self.sens_spin.setValue(self.audio.persistent_overlay.get('sensitivity', 5))
        
        # Sync Sensitivity
        self.sens_slider.valueChanged.connect(self.sens_spin.setValue)
        self.sens_spin.valueChanged.connect(self.sens_slider.setValue)
        
        sens_layout = QHBoxLayout()
        sens_layout.addWidget(self.sens_slider)
        sens_layout.addWidget(self.sens_spin)
        
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
        layout.addRow("Opacity:", opacity_layout)
        layout.addRow("Sensitivity:", sens_layout)
        
        # Instant Apply (only connect to sliders to avoid duplicate triggers)
        self.enabled_cb.toggled.connect(self.apply_settings)
        self.vu_cb.toggled.connect(self.apply_settings)
        self.locked_cb.toggled.connect(self.apply_settings)
        self.pos_mode_combo.currentTextChanged.connect(self.apply_settings)
        self.scale_slider.valueChanged.connect(self.apply_settings)
        self.opacity_slider.valueChanged.connect(self.apply_settings)
        self.sens_slider.valueChanged.connect(self.apply_settings)
        
        # Sync
        signals.setting_changed.connect(self.on_setting_changed)

    def apply_settings(self):
        new_config = {
            'enabled': self.enabled_cb.isChecked(),
            'show_vu': self.vu_cb.isChecked(),
            'locked': self.locked_cb.isChecked(),
            'position_mode': self.pos_mode_combo.currentText(),
            'scale': self.scale_slider.value(),
            'opacity': self.opacity_slider.value(),
            'sensitivity': self.sens_slider.value(),
            'x': self.audio.persistent_overlay.get('x', 100),
            'y': self.audio.persistent_overlay.get('y', 100)
        }
        self.audio.update_persistent_overlay(new_config)

    def on_setting_changed(self, key, value):
        if key == 'persistent_overlay':
            self.blockSignals(True)
            self.enabled_cb.setChecked(value.get('enabled', False))
            self.vu_cb.setChecked(value.get('show_vu', False))
            self.locked_cb.setChecked(value.get('locked', False))
            self.pos_mode_combo.setCurrentText(value.get('position_mode', 'Custom'))
            self.scale_slider.setValue(value.get('scale', 100))
            self.opacity_slider.setValue(value.get('opacity', 80))
            self.opacity_spin.setValue(value.get('opacity', 80))
            self.sens_slider.setValue(value.get('sensitivity', 5))
            self.sens_spin.setValue(value.get('sensitivity', 5))
            self.blockSignals(False)

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
            'sensitivity': self.sens_slider.value(),
            'x': self.audio.persistent_overlay.get('x', 100),
            'y': self.audio.persistent_overlay.get('y', 100)
        }

    def cleanup(self):
        """Disconnect signals to prevent crashes after widget destruction."""
        try:
            signals.setting_changed.disconnect(self.on_setting_changed)
        except (RuntimeError, TypeError):
            # Signal was not connected or already disconnected
            pass

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
        hook_instance = getattr(self.hook_thread, 'hook', None) if self.hook_thread else None
        self.hotkey_widget = HotkeySettingsWidget(self.audio, hook_instance)
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
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.on_close_clicked)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)
    
    def on_close_clicked(self):
        """Handler for close button click - applies settings and closes."""
        self.accept()

    def accept(self):
        """
        Applies all settings before closing the dialog.
        """
        # Apply hotkey configuration to the hook
        hotkey_config = self.hotkey_widget.get_config()
        self.audio.update_hotkey_config(hotkey_config)
        self.hook_thread.update_config(hotkey_config)
        
        # Emit signal to notify main window of changes
        self.settings_applied.emit()
        
        super().accept()
    
    def closeEvent(self, event):
        """
        Handles the close event to clean up resources.
        
        Args:
            event (QCloseEvent): The close event.
        """
        self.beep_widget.cleanup()
        self.afk_widget.cleanup()
        self.hotkey_widget.cleanup()
        self.osd_widget.cleanup()
        self.overlay_widget.cleanup()
        super().closeEvent(event)
