import pytest
import sys
import json
from unittest.mock import MagicMock, patch

# Import core normally.
# The module-level 'audio' object will be created.
# We hope it doesn't crash or block.
from MicMute.core import AudioController
from MicMute.config import CONFIG_FILE
import MicMute.core

@pytest.fixture
def mock_audio_utilities():
    # Patch AudioUtilities in the module where it is used
    with patch("MicMute.core.AudioUtilities") as mock:
        yield mock

@pytest.fixture
def audio_controller():
    # Create a fresh instance for testing, patching out side effects.
    # AudioController delegates config loading to ConfigManager, so we
    # patch ConfigManager.load_config to avoid file I/O during tests.
    with patch("MicMute.config.ConfigManager.load_config"):
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
    """Test that loading config updates AudioController's properties via config_manager."""
    config_data = {
        "device_id": "{some-guid}",
        "beep_enabled": False,
        "sync_ids": ["{slave-guid}"],
        "hotkey": {"mode": "separate", "mute": {"vk": 65}, "unmute": {"vk": 66}}
    }

    # AudioController delegates config loading to self.config_manager.
    # Patch Path.exists so the config file is "found", then json.load returns our data.
    with patch("pathlib.Path.exists", return_value=True), \
         patch("json.load", return_value=config_data), \
         patch("builtins.open", MagicMock()):
        audio_controller.config_manager.load_config()

    assert audio_controller.device_id == "{some-guid}"
    assert audio_controller.beep_enabled is False

def test_save_config(audio_controller):
    audio_controller.device_id = "{test-guid}"
    
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        with patch("json.dump") as mock_json_dump:
            audio_controller.save_config()
            mock_open.assert_called_with(CONFIG_FILE, 'w', encoding='utf-8')
            args, _ = mock_json_dump.call_args
            assert args[0]['device_id'] == "{test-guid}"

def test_find_device_saved_found(audio_controller, mock_audio_utilities):
    audio_controller.device_id = "{saved-id}"
    
    mock_dev = MagicMock()
    mock_dev.id = "{saved-id}"
    mock_dev.FriendlyName = "Saved Mic"
    mock_dev.EndpointVolume = MagicMock()
    
    mock_audio_utilities.GetAllDevices.return_value = [mock_dev]
    
    with patch("MicMute.core.signals.update_icon"):
        result = audio_controller.find_device()
    assert result is True
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
