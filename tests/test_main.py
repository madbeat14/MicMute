import pytest
import sys
from unittest.mock import MagicMock, patch

# Mock dependencies that might not be available in test environment or require hardware
with patch.dict(sys.modules, {
    "pycaw.pycaw": MagicMock(),
    "winsound": MagicMock(),
    "PySide6.QtWidgets": MagicMock(),
    "PySide6.QtCore": MagicMock(),
    "PySide6.QtGui": MagicMock(),
}):
    from MicMute.core import AudioController
    from MicMute.utils import is_system_light_theme

def test_audio_controller_init():
    """Test that AudioController initializes with default values."""
    # AudioController delegates config loading to ConfigManager.load_config
    with patch("MicMute.config.ConfigManager.load_config"):
        audio = AudioController()
        assert audio.beep_enabled is True
        # Updated structure check
        assert audio.hotkey_config['toggle']['vk'] == 0xB3

def test_is_system_light_theme():
    """Test theme detection returns boolean."""
    # We can't easily mock registry, but we can check return type
    result = is_system_light_theme()
    assert isinstance(result, bool)
