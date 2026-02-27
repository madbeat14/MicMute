import pytest
import sys
from unittest.mock import MagicMock, patch, call
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

# Import Overlay components
# We need to patch QPainter or ensure it doesn't crash in headless
from MicMute.overlay import MetroOSD, StatusOverlay

def test_metro_osd_init(qapp):
    """Test MetroOSD initialization."""
    osd = MetroOSD("icon_unmuted.svg", "icon_muted.svg")
    assert osd.windowFlags() & Qt.FramelessWindowHint
    assert osd.testAttribute(Qt.WA_TranslucentBackground)
    osd.close()

def test_metro_osd_show(qapp):
    """Test showing OSD."""
    osd = MetroOSD("icon_unmuted.svg", "icon_muted.svg")
    config = {'enabled': True, 'duration': 100, 'position': 'Bottom-Center', 'size': 150}
    osd.set_config(config)
    
    # We can't easily test visual rendering, but we can test state
    osd.show_osd(True) # Muted
    assert osd.isVisible()
    osd.close()

def test_status_overlay_init(qapp):
    """Test StatusOverlay initialization."""
    overlay = StatusOverlay("icon_unmuted.svg", "icon_muted.svg")
    assert overlay.windowFlags() & Qt.WindowStaysOnTopHint
    overlay.close()

def test_status_overlay_config(qapp):
    """Test updating overlay config."""
    overlay = StatusOverlay("icon_unmuted.svg", "icon_muted.svg")
    config = {
        'enabled': True,
        'show_vu': False,
        'opacity': 50,
        'x': 10,
        'y': 10,
        'position_mode': 'Custom',
        'locked': True,
        'sensitivity': 5
    }
    overlay.set_config(config)
    
    assert overlay.windowOpacity() == pytest.approx(0.5, abs=0.01)
    assert overlay.x() == 10
    assert overlay.y() == 10
    overlay.close()


def test_force_topmost_always_calls_setwindowpos(qapp):
    """Test that _force_topmost always calls SetWindowPos without rate-limiting."""
    overlay = StatusOverlay("icon_unmuted.svg", "icon_muted.svg")
    overlay.show()

    with patch("ctypes.windll.user32.SetWindowPos") as mock_swp:
        # Call twice rapidly — both should execute (no rate-limiter)
        overlay._force_topmost()
        overlay._force_topmost()
        assert mock_swp.call_count == 2

    overlay.close()


def test_force_topmost_after_drag(qapp):
    """Test that _force_topmost is called after mouse drag release."""
    overlay = StatusOverlay("icon_unmuted.svg", "icon_muted.svg")
    overlay.current_config = {"enabled": True}
    overlay.show()

    with patch.object(overlay, "_force_topmost") as mock_ft:
        # Simulate drag
        overlay.dragging = True
        overlay.offset = None  # Prevent actual move

        # Create a mock event for mouseReleaseEvent
        event = MagicMock()
        overlay.mouseReleaseEvent(event)
        mock_ft.assert_called()

    overlay.close()


def test_show_event_calls_force_topmost_directly(qapp):
    """Test that showEvent calls _force_topmost directly (no timer delay)."""
    overlay = StatusOverlay("icon_unmuted.svg", "icon_muted.svg")

    with patch.object(overlay, "_force_topmost") as mock_ft:
        # show() triggers showEvent internally with the correct QShowEvent
        overlay.show()
        mock_ft.assert_called()

    overlay.close()


def test_visibility_check_detects_lost_topmost_style(qapp):
    """Test that _visibility_check re-asserts topmost when WS_EX_TOPMOST is stripped."""
    overlay = StatusOverlay("icon_unmuted.svg", "icon_muted.svg")
    overlay.current_config = {"enabled": True}
    overlay.show()

    with patch("ctypes.windll.user32.IsIconic", return_value=False), \
         patch("ctypes.windll.user32.GetWindowLongW", return_value=0), \
         patch.object(overlay, "_force_topmost") as mock_ft:
        overlay._visibility_check()
        # Should detect missing WS_EX_TOPMOST and call _force_topmost
        mock_ft.assert_called()

    overlay.close()


def test_topmost_timer_interval(qapp):
    """Test that the topmost timer uses 500ms interval for fast recovery."""
    overlay = StatusOverlay("icon_unmuted.svg", "icon_muted.svg")
    assert overlay.topmost_timer.interval() == 500
    overlay.close()
