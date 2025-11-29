import pytest
import sys
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QDialog, QCheckBox, QSpinBox, QComboBox
from PySide6.QtCore import Qt

# Ensure QApp exists
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

# Import module to patch object on it
import MicMute.gui
from MicMute.gui import SettingsDialog, DeviceSelectionWidget, HotkeySettingsWidget

@pytest.fixture
def mock_audio():
    audio = MagicMock()
    audio.beep_enabled = True
    audio.beep_config = {'mute': {'freq': 1, 'duration': 1, 'count': 1}, 'unmute': {'freq': 1, 'duration': 1, 'count': 1}}
    audio.sound_config = {'mute': '', 'unmute': ''}
    audio.hotkey_config = {'mode': 'toggle', 'toggle': {'vk': 0xB3}, 'mute': {'vk': 0}, 'unmute': {'vk': 0}}
    audio.afk_config = {'enabled': False, 'timeout': 60}
    audio.osd_config = {'enabled': False, 'size': 150, 'duration': 1500, 'position': 'Bottom-Center'}
    audio.persistent_overlay = {'enabled': False, 'show_vu': False, 'opacity': 80, 'x': 100, 'y': 100, 'position_mode': 'Custom', 'locked': False, 'sensitivity': 5}
    audio.sync_ids = []
    audio.device_id = None
    return audio

@pytest.fixture
def mock_hook():
    hook = MagicMock()
    return hook

def test_settings_dialog_init(qapp, mock_audio, mock_hook):
    """Test that SettingsDialog initializes without error."""
    # Use patch.object to be absolutely sure we are patching the right thing
    # Also patch global audio object used by DeviceSelectionWidget
    with patch.object(MicMute.gui, "AudioUtilities") as mock_au, \
         patch.object(MicMute.gui, "audio", mock_audio):
        
        mock_au.GetAllDevices.return_value = []
        mock_au.GetDeviceEnumerator.return_value = MagicMock()
        
        dialog = SettingsDialog(mock_audio, mock_hook)
        assert dialog.windowTitle() == "MicMute Settings"
        dialog.close()

def test_device_selection_widget(qapp, mock_audio):
    """Test device selection widget population."""
    # Patch AudioUtilities in gui module
    # AND patch the global 'audio' object in gui module because DeviceSelectionWidget uses it
    with patch.object(MicMute.gui, "AudioUtilities") as mock_au, \
         patch.object(MicMute.gui, "audio", mock_audio):
        
        # Mock devices
        dev1 = MagicMock()
        dev1.id = "{id1}"
        dev1.GetId.return_value = "{id1}"
        dev1.FriendlyName = "Mic 1"
        dev1.EndpointVolume.GetMute.return_value = 0
        
        dev2 = MagicMock()
        dev2.id = "{id2}"
        dev2.GetId.return_value = "{id2}"
        dev2.FriendlyName = "Mic 2"
        dev2.EndpointVolume.GetMute.return_value = 1
        
        mock_au.GetAllDevices.return_value = [dev1, dev2]
        
        # Mock Enumerator for capture IDs
        mock_enum = MagicMock()
        mock_coll = MagicMock()
        mock_coll.GetCount.return_value = 2
        mock_coll.Item.side_effect = [dev1, dev2]
        mock_enum.EnumAudioEndpoints.return_value = mock_coll
        mock_au.GetDeviceEnumerator.return_value = mock_enum
        
        widget = DeviceSelectionWidget()
        
        # Check table rows
        assert widget.table.rowCount() == 2
        assert widget.table.item(0, 1).text() == "Mic 1"
        assert widget.table.item(1, 1).text() == "Mic 2"

def test_hotkey_settings_widget(qapp, mock_audio, mock_hook):
    """Test hotkey settings widget."""
    mock_audio.hotkey_config = {'mode': 'toggle', 'toggle': {'vk': 65, 'name': 'A'}}
    
    widget = HotkeySettingsWidget(mock_audio, mock_hook)
    
    # Check initial state
    assert widget.mode_toggle.isChecked()
    assert widget.input_toggle.current_vk == 65
    
    # Get config
    config = widget.get_config()
    assert config['mode'] == 'toggle'
    assert config['toggle']['vk'] == 65

def test_afk_settings_widget(qapp, mock_audio):
    """Test AFK settings widget."""
    from MicMute.gui import AfkSettingsWidget
    mock_audio.afk_config = {'enabled': True, 'timeout': 120}
    
    widget = AfkSettingsWidget(mock_audio)
    
    assert widget.enabled_cb.isChecked() is True
    assert widget.timeout_spin.value() == 120
    
    # Change value
    widget.timeout_spin.setValue(300)
    config = widget.get_config()
    assert config['timeout'] == 300

def test_osd_settings_widget(qapp, mock_audio):
    """Test OSD settings widget."""
    from MicMute.gui import OsdSettingsWidget
    mock_audio.osd_config = {'enabled': True, 'size': 200, 'duration': 1000, 'position': 'Top-Left'}
    
    widget = OsdSettingsWidget(mock_audio)
    
    assert widget.enabled_cb.isChecked() is True
    assert widget.size_spin.value() == 200
    assert widget.position_combo.currentText() == 'Top-Left'
