import pytest
import sys
from unittest.mock import MagicMock, patch

# Mock dependencies
# We rely on real PySide6 or mock it differently if needed.
# For now, let's try without sys.modules hacking.
from MicMute.utils import is_system_light_theme, get_idle_duration

def test_is_system_light_theme_true():
    """Test light theme detection when registry returns 1."""
    with patch("MicMute.utils.winreg") as mock_reg:
        mock_reg.ConnectRegistry.return_value = MagicMock()
        mock_reg.OpenKey.return_value = MagicMock()
        mock_reg.QueryValueEx.return_value = (1, 1)
        assert is_system_light_theme() is True

def test_is_system_light_theme_false():
    """Test light theme detection when registry returns 0."""
    with patch("MicMute.utils.winreg") as mock_reg:
        mock_reg.ConnectRegistry.return_value = MagicMock()
        mock_reg.OpenKey.return_value = MagicMock()
        mock_reg.QueryValueEx.return_value = (0, 1)
        assert is_system_light_theme() is False

def test_is_system_light_theme_error():
    """Test light theme detection handles exceptions gracefully."""
    with patch("MicMute.utils.winreg") as mock_reg:
        mock_reg.ConnectRegistry.side_effect = Exception("Registry Error")
        assert is_system_light_theme() is False

def test_get_idle_duration():
    """Test idle duration calculation."""
    # Patch user32 and kernel32 in the utils module
    with patch("MicMute.utils.user32") as mock_user32, \
         patch("MicMute.utils.kernel32") as mock_kernel32, \
         patch("MicMute.utils.sizeof", return_value=8), \
         patch("MicMute.utils.ctypes.byref") as mock_byref:
        
        mock_user32.GetLastInputInfo.return_value = 1
        mock_kernel32.GetTickCount.return_value = 10000
        
        # We need to handle the structure. 
        # The code does: lastInputInfo = LASTINPUTINFO()
        # We can patch LASTINPUTINFO to return a mock that has dwTime
        with patch("MicMute.utils.LASTINPUTINFO") as MockStruct:
            instance = MockStruct.return_value
            instance.dwTime = 5000
            
            duration = get_idle_duration()
            assert duration == 5.0
