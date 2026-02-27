import pytest
import sys
from unittest.mock import MagicMock, patch, call
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QColor

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


# --- Adaptive Icon Tests ---


def test_adaptive_icon_init_with_dark_icons(qapp):
    """Test StatusOverlay accepts dark icon paths and defaults to light icons."""
    overlay = StatusOverlay(
        "unmuted_white.svg", "muted_white.svg",
        "unmuted_dark.svg", "muted_dark.svg",
    )
    assert overlay.icon_unmuted_dark == "unmuted_dark.svg"
    assert overlay.icon_muted_dark == "muted_dark.svg"
    assert overlay._use_dark_icon is False
    overlay.close()


def test_adaptive_icon_init_without_dark_icons(qapp):
    """Test StatusOverlay works without dark icon paths (backward compat)."""
    overlay = StatusOverlay("unmuted_white.svg", "muted_white.svg")
    assert overlay.icon_unmuted_dark == ""
    assert overlay.icon_muted_dark == ""
    assert overlay._use_dark_icon is False
    overlay.close()


def _make_solid_image(width, height, color):
    """Helper: create a solid-color QImage."""
    img = QImage(width, height, QImage.Format_ARGB32)
    img.fill(color)
    return img


def test_adaptive_icon_dark_background(qapp):
    """When background is dark, white (light) icons should be used."""
    overlay = StatusOverlay(
        "unmuted_white.svg", "muted_white.svg",
        "unmuted_dark.svg", "muted_dark.svg",
    )
    overlay.show()

    # Mock _sample_background_brightness to return dark (50)
    with patch.object(overlay, "_sample_background_brightness", return_value=50.0):
        overlay._use_dark_icon = True  # Start as dark to test switch
        overlay._update_icon_for_background()
        assert overlay._use_dark_icon is False  # Should switch to light icons

    overlay.close()


def test_adaptive_icon_light_background(qapp):
    """When background is light, dark icons should be used."""
    overlay = StatusOverlay(
        "unmuted_white.svg", "muted_white.svg",
        "unmuted_dark.svg", "muted_dark.svg",
    )
    overlay.show()

    # Mock _sample_background_brightness to return light (200)
    with patch.object(overlay, "_sample_background_brightness", return_value=200.0):
        overlay._use_dark_icon = False  # Start as light to test switch
        overlay._update_icon_for_background()
        assert overlay._use_dark_icon is True  # Should switch to dark icons

    overlay.close()


def test_adaptive_icon_hysteresis_no_flicker(qapp):
    """Within hysteresis band, icon state should not change."""
    overlay = StatusOverlay(
        "unmuted_white.svg", "muted_white.svg",
        "unmuted_dark.svg", "muted_dark.svg",
    )
    overlay.show()

    # Brightness = 130 is within the hysteresis band (113-143)
    with patch.object(overlay, "_sample_background_brightness", return_value=130.0):
        # Currently using light icons — should NOT switch
        overlay._use_dark_icon = False
        overlay._update_icon_for_background()
        assert overlay._use_dark_icon is False

        # Currently using dark icons — should NOT switch back either
        overlay._use_dark_icon = True
        overlay._update_icon_for_background()
        assert overlay._use_dark_icon is True

    overlay.close()


def test_current_icon_path_muted_light(qapp):
    """Test _current_icon_path returns white muted icon when not using dark."""
    overlay = StatusOverlay(
        "unmuted_white.svg", "muted_white.svg",
        "unmuted_dark.svg", "muted_dark.svg",
    )
    overlay.is_muted = True
    overlay._use_dark_icon = False
    assert overlay._current_icon_path() == "muted_white.svg"
    overlay.close()


def test_current_icon_path_muted_dark(qapp):
    """Test _current_icon_path returns dark muted icon when using dark."""
    overlay = StatusOverlay(
        "unmuted_white.svg", "muted_white.svg",
        "unmuted_dark.svg", "muted_dark.svg",
    )
    overlay.is_muted = True
    overlay._use_dark_icon = True
    assert overlay._current_icon_path() == "muted_dark.svg"
    overlay.close()


def test_current_icon_path_unmuted_dark(qapp):
    """Test _current_icon_path returns dark unmuted icon when using dark."""
    overlay = StatusOverlay(
        "unmuted_white.svg", "muted_white.svg",
        "unmuted_dark.svg", "muted_dark.svg",
    )
    overlay.is_muted = False
    overlay._use_dark_icon = True
    assert overlay._current_icon_path() == "unmuted_dark.svg"
    overlay.close()


def test_bg_check_timer_interval(qapp):
    """Test that the background check timer uses 2000ms interval."""
    overlay = StatusOverlay("icon_unmuted.svg", "icon_muted.svg")
    assert overlay._bg_check_timer.interval() == 2000
    overlay.close()
