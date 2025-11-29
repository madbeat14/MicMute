import pytest
import sys
import json
from unittest.mock import MagicMock, patch

# Import core normally.
# The module-level 'audio' object will be created.
# We hope it doesn't crash or block.
from MicMute.core import AudioController, CONFIG_FILE
import MicMute.core

@pytest.fixture
def mock_audio_utilities():
    # Patch AudioUtilities in the module where it is used
    with patch("MicMute.core.AudioUtilities") as mock:
        yield mock

@pytest.fixture
def audio_controller():
    # Create a fresh instance for testing, patching out side effects
    with patch("MicMute.core.AudioController.load_config"), \
         patch("MicMute.core.AudioController.start_device_watcher"):
        controller = AudioController()
        # Set defaults
        controller.beep_enabled = True
        controller.device_id = None
        controller.sync_ids = []
        controller.hotkey_config = {'vk': 0xB3, 'mode': 'toggle'}
        return controller

def test_init_defaults(audio_controller):
    assert audio_controller.beep_enabled is True
    assert audio_controller.device_id is None

def test_load_config(audio_controller):
    config_data = {
        "device_id": "{some-guid}",
        "beep_enabled": False,
        "sync_ids": ["{slave-guid}"],
        "hotkey": {"mode": "separate", "mute": {"vk": 65}, "unmute": {"vk": 66}}
    }
    
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.read.return_value = json.dumps(config_data)
        mock_open.return_value = mock_file
        
        with patch("os.path.exists", return_value=True):
            with patch("json.load", return_value=config_data):
                audio_controller.load_config()
    
    assert audio_controller.device_id == "{some-guid}"
    assert audio_controller.beep_enabled is False

def test_save_config(audio_controller):
    audio_controller.device_id = "{test-guid}"
    
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        with patch("json.dump") as mock_json_dump:
            audio_controller.save_config()
            mock_open.assert_called_with(CONFIG_FILE, 'w')
            args, _ = mock_json_dump.call_args
            assert args[0]['device_id'] == "{test-guid}"

def test_find_device_saved_found(audio_controller, mock_audio_utilities):
    audio_controller.device_id = "{saved-id}"
    
    mock_dev = MagicMock()
    mock_dev.id = "{saved-id}"
    mock_dev.FriendlyName = "Saved Mic"
    
    mock_audio_utilities.GetAllDevices.return_value = [mock_dev]
    
    assert audio_controller.find_device() is True
    assert audio_controller.device == mock_dev

def test_toggle_mute(audio_controller):
    mock_volume = MagicMock()
    mock_volume.GetMute.return_value = 0
    audio_controller.volume = mock_volume
    
    # Patch the class method
    with patch("MicMute.core.AudioController.set_mute_state") as mock_set_mute:
        audio_controller.toggle_mute()
        mock_set_mute.assert_called_with(True)

def test_set_mute_state_change(audio_controller):
    mock_volume = MagicMock()
    mock_volume.GetMute.return_value = 0
    audio_controller.volume = mock_volume
    
    # Patch the signals object in the module
    with patch("MicMute.core.signals.update_icon") as mock_signal:
        # Patch class method for play_sound
        with patch("MicMute.core.AudioController.play_sound") as mock_play:
            audio_controller.set_mute_state(True)
            
            mock_volume.SetMute.assert_called_with(True, None)
            mock_play.assert_called_with('mute')
            mock_signal.emit.assert_called_with(True)
