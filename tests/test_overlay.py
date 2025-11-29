import pytest
import sys
from unittest.mock import MagicMock, patch
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
