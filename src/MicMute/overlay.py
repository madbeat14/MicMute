from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, Signal, Slot
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QIcon, QPixmap, QCursor
from PySide6.QtSvg import QSvgRenderer
import ctypes

class MetroOSD(QWidget):
    def __init__(self, icon_unmuted_path, icon_muted_path):
        super().__init__()
        
        # Window Flags
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool | 
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # Visual Config
        self.osd_size = 150
        self.resize(self.osd_size, self.osd_size)
        self.bg_color = QColor(30, 30, 30, 200)
        self.radius = 10
        
        # Icons
        # Icons
        self.icon_unmuted_path = icon_unmuted_path
        self.icon_muted_path = icon_muted_path
        
        # Cache Renderers
        self.renderer_unmuted = QSvgRenderer(self.icon_unmuted_path)
        self.renderer_muted = QSvgRenderer(self.icon_muted_path)
        
        self.current_renderer = self.renderer_unmuted
        
        # Layout & Content
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(Qt.AlignCenter)
        
        # Animation
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(150) # Fade In
        self.opacity_anim.setEasingCurve(QEasingCurve.OutQuad)
        
        self.fade_out_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out_anim.setDuration(500) # Fade Out
        self.fade_out_anim.setEasingCurve(QEasingCurve.InQuad)
        self.fade_out_anim.finished.connect(self.hide)
        
        # Timer
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.start_fade_out)
        
        self.duration = 1500
        self.position = "Bottom-Center"
        
    def set_config(self, config):
        self.duration = config.get('duration', 1500)
        self.position = config.get('position', 'Bottom-Center')
        self.osd_size = config.get('size', 150)
        self.resize(self.osd_size, self.osd_size)
        
    def show_osd(self, is_muted):
        self.current_renderer = self.renderer_muted if is_muted else self.renderer_unmuted
        self.update() # Trigger repaint with new icon
        
        # Reset Timer
        self.hide_timer.stop()
        self.fade_out_anim.stop()
        
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.reposition() # Position before showing
            self.show()
            
            # Fade In
            self.opacity_anim.setStartValue(0.0)
            self.opacity_anim.setEndValue(1.0)
            self.opacity_anim.start()
        else:
            self.setWindowOpacity(1.0)
            self.reposition() # Ensure position is correct if config changed
            
        self.hide_timer.start(self.duration)
        
    def start_fade_out(self):
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.start()
        
    def reposition(self):
        # Get screen where cursor is, or primary
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()
            
        geo = screen.geometry()
        w, h = self.width(), self.height()
        margin = 40 # Standard margin
        
        # Calculate X
        if "Left" in self.position:
            x = geo.x() + margin
        elif "Right" in self.position:
            x = geo.x() + geo.width() - w - margin
        else: # Center/Middle
            x = geo.x() + (geo.width() - w) // 2
            
        # Calculate Y
        if "Top" in self.position:
            y = geo.y() + margin
        elif "Bottom" in self.position:
            y = geo.y() + geo.height() - h - margin
            # Special case: Windows flyout is usually a bit higher, but we stick to margin for consistency
            if self.position == "Bottom-Center":
                y = geo.y() + geo.height() - h - 100 # Slightly higher for Bottom-Center
        else: # Middle/Center
            y = geo.y() + (geo.height() - h) // 2
            
        self.move(x, y)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw Background
        painter.setBrush(QBrush(self.bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), self.radius, self.radius)
        
        # Draw Icon
        if self.current_renderer and self.current_renderer.isValid():
            # Scale icon to 65% of container
            icon_size = int(self.width() * 0.65)
            x = (self.width() - icon_size) // 2
            y = (self.height() - icon_size) // 2
            self.current_renderer.render(painter, QRect(x, y, icon_size, icon_size))

# --- PERSISTENT OVERLAY ---
try:
    from .utils import IAudioMeterInformation, IMMDeviceEnumerator, CLSID_MMDeviceEnumerator, eCapture, DEVICE_STATE_ACTIVE, CLSCTX_ALL, IAudioClient, WAVEFORMATEX
    from comtypes import client
    from ctypes import POINTER, cast
    HAS_COM = True
except ImportError:
    HAS_COM = False

from PySide6.QtWidgets import QProgressBar, QHBoxLayout

class StatusOverlay(QWidget):
    config_changed = Signal(dict)

    def __init__(self, icon_unmuted_path, icon_muted_path):
        super().__init__()
        
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.icon_unmuted = icon_unmuted_path
        self.icon_muted = icon_muted_path
        self.is_muted = False
        self.show_vu = False
        self.target_device_id = None
        
        # Layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.layout.setSpacing(5)
        
        # Icon Label
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.layout.addWidget(self.icon_label)
        
        # Activity LED (Dot)
        self.led_dot = QLabel()
        self.led_dot.setFixedSize(10, 10)
        self.led_dot.setStyleSheet("""
            background-color: transparent;
            border-radius: 5px;
        """)
        self.layout.addWidget(self.led_dot)
        
        # Styling
        self.setStyleSheet("""
            StatusOverlay {
                background-color: rgba(30, 30, 30, 200);
                border-radius: 15px;
                border: 1px solid #444;
            }
        """)
        
        # Dragging
        self.dragging = False
        self.offset = None
        
        # Audio Meter
        self.meter = None
        self.meter_timer = QTimer()
        self.meter_timer.setInterval(50) # 20Hz
        self.meter_timer.timeout.connect(self.sample_audio)
        
        self.resize(60, 40)
        
        self.position_mode = 'Custom'
        self.locked = False
        self.current_config = {}
        self.sensitivity = 0.05 # Default 5%
        self.is_active = False
        
    def set_config(self, config):
        self.current_config = config.copy()
        if not config.get('enabled', False):
            self.hide()
            self.stop_meter()
            return
            
        self.show_vu = config.get('show_vu', False)
        
        # Update Target Device
        self.set_target_device(config.get('device_id'))
        
        opacity = config.get('opacity', 80) / 100.0
        self.setWindowOpacity(opacity)
        
        self.led_dot.setVisible(self.show_vu)
        
        # Resize based on content
        width = 60 if self.show_vu else 45
        self.resize(width, 40)
        
        # Position
        self.position_mode = config.get('position_mode', 'Custom')
        self.locked = config.get('locked', False)
        self.sensitivity = config.get('sensitivity', 5) / 100.0
        
        if self.position_mode == 'Custom':
            x = config.get('x', 100)
            y = config.get('y', 100)
            self.move(x, y)
        else:
            self.reposition_predefined()
        
        self.show()
        self.update_status(self.is_muted) # Refresh state

    def set_target_device(self, device_id):
        self.target_device_id = device_id
        # Restart meter if running to switch device
        if self.meter_timer.isActive():
            self.stop_meter()
            self.start_meter()

    def reposition_predefined(self):
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()
            
        geo = screen.geometry()
        w, h = self.width(), self.height()
        margin = 20
        
        x, y = geo.x(), geo.y()
        
        # Horizontal
        if "Left" in self.position_mode:
            x += margin
        elif "Right" in self.position_mode:
            x += geo.width() - w - margin
        else: # Center/Middle
            x += (geo.width() - w) // 2
            
        # Vertical
        if "Top" in self.position_mode:
            y += margin
        elif "Bottom" in self.position_mode:
            y += geo.height() - h - margin
        else: # Middle/Center
            y += (geo.height() - h) // 2
            
        self.move(x, y)

    def update_status(self, is_muted):
        self.is_muted = is_muted
        
        # Update Icon
        path = self.icon_muted if is_muted else self.icon_unmuted
        pixmap = QIcon(path).pixmap(24, 24)
        self.icon_label.setPixmap(pixmap)
        
        # Manage Meter
        if is_muted or not self.isVisible() or not self.show_vu:
            self.stop_meter()
            self.set_active(False)
        else:
            self.start_meter()

    def set_active(self, active):
        if self.is_active == active: return
        self.is_active = active
        
        color = "#00FF00" if active else "transparent" # Bright Green or Transparent
        self.led_dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 5px;
        """)

    def start_meter(self):
        if not HAS_COM: return
        if self.meter_timer.isActive(): return
        
        try:
            # Create Enumerator
            enumerator = client.CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
            
            device = None
            if self.target_device_id:
                try:
                    # GetDevice takes ID string
                    device = enumerator.GetDevice(self.target_device_id)
                except Exception:
                    print(f"Could not find device with ID: {self.target_device_id}")
            
            if not device:
                # Fallback to default
                device = enumerator.GetDefaultAudioEndpoint(eCapture, 0) # eCapture, eConsole/0 (Role doesn't matter much for default)
            
            # Activate Meter
            # Activate returns POINTER(POINTER(IUnknown)), so we need to dereference or cast?
            # In our definition: (['out', 'retval'], POINTER(POINTER(IUnknown)), 'ppInterface')
            # comtypes handles the double pointer for retval usually.
            # But wait, our definition in utils.py for Activate returns POINTER(POINTER(IUnknown)).
            # Let's check debug_audio.py usage:
            # meter_unk = device.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
            # meter = meter_unk.QueryInterface(IAudioMeterInformation)
            
            meter_unk = device.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
            # meter = meter_unk.QueryInterface(IAudioMeterInformation) # This fails if type is POINTER(IUnknown)
            self.meter = cast(meter_unk, POINTER(IAudioMeterInformation))
            
            # Start Audio Client to ensure meter works
            client_unk = device.Activate(IAudioClient._iid_, CLSCTX_ALL, None)
            self.audio_client = cast(client_unk, POINTER(IAudioClient))
            fmt = self.audio_client.GetMixFormat()
            # ShareMode=0 (Shared), Flags=0, Duration=100ms (1000000 reftimes)
            self.audio_client.Initialize(0, 0, 1000000, 0, fmt, None)
            self.audio_client.Start()
            
            self.meter_timer.start()
        except Exception as e:
            print(f"Error starting meter: {e}")
            pass

    def stop_meter(self):
        self.meter_timer.stop()
        self.meter = None
        
        if hasattr(self, 'audio_client') and self.audio_client:
            try:
                self.audio_client.Stop()
            except:
                pass
            self.audio_client = None
            
        self.set_active(False)

    @Slot()
    def sample_audio(self):
        if not self.meter: return
        try:
            # GetPeakValue returns the float value directly because of ['out'] parameter
            peak_value = self.meter.GetPeakValue()
            
            # Threshold Logic
            is_loud = peak_value > self.sensitivity
            self.set_active(is_loud)
            
        except Exception:
            self.stop_meter()

    # Dragging Logic
    def mousePressEvent(self, event):
        if self.locked: return
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if self.locked: return
        if self.dragging and self.offset:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            # Save new position and switch to Custom mode
            self.current_config['x'] = self.x()
            self.current_config['y'] = self.y()
            self.current_config['position_mode'] = 'Custom'
            self.config_changed.emit(self.current_config)

    def closeEvent(self, event):
        self.stop_meter()
        super().closeEvent(event)
