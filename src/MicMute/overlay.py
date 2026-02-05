from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, Signal, Slot, QThread
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QIcon, QPixmap, QCursor
from PySide6.QtSvg import QSvgRenderer
import ctypes
from ctypes import wintypes
import threading

class MetroOSD(QWidget):
    """
    A Windows 10/11 Metro-style On-Screen Display (OSD) for mute status.
    """
    def __init__(self, icon_unmuted_path, icon_muted_path):
        """
        Initializes the OSD widget.
        
        Args:
            icon_unmuted_path (str): Path to the unmuted icon.
            icon_muted_path (str): Path to the muted icon.
        """
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
        # Fade In
        self.opacity_anim.setDuration(150)
        self.opacity_anim.setEasingCurve(QEasingCurve.OutQuad)
        
        self.fade_out_anim = QPropertyAnimation(self, b"windowOpacity")
        # Fade Out
        self.fade_out_anim.setDuration(500)
        self.fade_out_anim.setEasingCurve(QEasingCurve.InQuad)
        self.fade_out_anim.finished.connect(self.hide)
        
        # Timer
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.start_fade_out)
        
        self.duration = 1500
        self.position = "Bottom-Center"
        self.target_opacity = 0.8
        
    def set_config(self, config):
        """
        Updates the OSD configuration.
        
        Args:
            config (dict): Configuration dictionary.
        """
        self.duration = config.get('duration', 1500)
        self.position = config.get('position', 'Bottom-Center')
        self.osd_size = config.get('size', 150)
        self.target_opacity = config.get('opacity', 80) / 100.0
        self.resize(self.osd_size, self.osd_size)
        
    def show_osd(self, is_muted):
        """
        Displays the OSD with the current mute state.
        
        Args:
            is_muted (bool): True if muted, False otherwise.
        """
        self.current_renderer = self.renderer_muted if is_muted else self.renderer_unmuted
        # Trigger repaint with new icon
        self.update()
        
        # Reset Timer
        self.hide_timer.stop()
        self.fade_out_anim.stop()
        
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            # Position before showing
            self.setWindowOpacity(0.0)
            # Position before showing
            self.apply_position()
            self.show()
            
            # Fade In
            self.opacity_anim.setStartValue(0.0)
            self.opacity_anim.setEndValue(self.target_opacity)
            self.opacity_anim.start()
        else:
            self.setWindowOpacity(self.target_opacity)
            # Ensure position is correct if config changed
            # Ensure position is correct if config changed
            self.apply_position()
            
        self.hide_timer.start(self.duration)
        
    def start_fade_out(self):
        """
        Starts the fade-out animation.
        """
        self.fade_out_anim.setStartValue(self.target_opacity)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.start()
        
    def apply_position(self):
        """
        Calculates and sets the OSD position based on configuration.
        Uses availableGeometry() to respect taskbar.
        """
        # Get screen where cursor is, or primary
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()
            
        geo = screen.availableGeometry()
        w, h = self.width(), self.height()
        # Standard margin
        margin = 40
        
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
                # Slightly higher for Bottom-Center
                y = geo.y() + geo.height() - h - 100
        else: # Middle/Center
            y = geo.y() + (geo.height() - h) // 2
            
        self.move(x, y)
        
    def paintEvent(self, event):
        """
        Handles the paint event to draw the OSD background and icon.
        """
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
    from .utils import IAudioMeterInformation, IMMDeviceEnumerator, CLSID_MMDeviceEnumerator, eCapture, DEVICE_STATE_ACTIVE, CLSCTX_ALL, IAudioClient, WAVEFORMATEX, IMMDevice
    from comtypes import client
    from ctypes import POINTER, cast
    HAS_COM = True
except ImportError:
    HAS_COM = False

from PySide6.QtWidgets import QProgressBar, QHBoxLayout

class AudioMeterWorker(QThread):
    """
    Worker thread for sampling audio meter values.
    Runs COM operations in background to avoid blocking UI.
    """
    peak_detected = Signal(float)
    error_occurred = Signal()
    
    def __init__(self, meter, sensitivity):
        super().__init__()
        self.meter = meter
        self.sensitivity = sensitivity
        self._running = False
        self._lock = threading.Lock()
        
    def set_sensitivity(self, value):
        with self._lock:
            self.sensitivity = value
    
    def stop(self):
        self._running = False
        self.wait(100)  # Wait up to 100ms for thread to finish
        
    def run(self):
        self._running = True
        while self._running:
            try:
                if self.meter:
                    peak_value = self.meter.GetPeakValue()
                    self.peak_detected.emit(peak_value)
            except Exception:
                self.error_occurred.emit()
                break
            # 50ms interval = 20Hz sampling rate
            self.msleep(50)


class StatusOverlay(QWidget):
    """
    A persistent overlay widget showing microphone status and voice activity.
    """
    # Signal emitted when configuration changes (e.g. position)
    config_changed = Signal(dict)
    
    # Windows API constants for forcing topmost
    HWND_TOPMOST = -1
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040

    def __init__(self, icon_unmuted_path, icon_muted_path):
        """
        Initializes the overlay widget.
        
        Args:
            icon_unmuted_path (str): Path to the unmuted icon.
            icon_muted_path (str): Path to the muted icon.
        """
        super().__init__()
        
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool | 
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
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
        self.meter_worker = None
        
        # Topmost Timer - Re-assert topmost position periodically
        # 2000ms to reduce GUI thread load when settings is open
        self.topmost_timer = QTimer()
        self.topmost_timer.setInterval(2000)  # Every 2000ms (was 500ms)
        self.topmost_timer.timeout.connect(self._force_topmost)
        
        # Visibility Monitor - Detect when window is hidden/buried and auto-restore
        self.visibility_timer = QTimer()
        self.visibility_timer.setInterval(3000)  # Check every 3000ms (was 1000ms)
        self.visibility_timer.timeout.connect(self._visibility_check)
        self._last_visible_state = False
        self._consecutive_hidden_count = 0
        self._last_topmost_time = 0  # Track last SetWindowPos call
        
        self.resize(60, 40)
        
        self.position_mode = 'Custom'
        self.locked = False
        self.current_config = {}
        # Default 5%
        self.sensitivity = 0.05
        self.is_active = False
    
    def _force_topmost(self):
        """
        Forces the window to the topmost Z-order using Windows API.
        This is more reliable than Qt's WindowStaysOnTopHint alone.
        Rate-limited to prevent GUI thread flooding.
        """
        if not self.isVisible():
            return
            
        # Rate limiting: Don't call more than once every 500ms
        import time
        current_time = int(time.time() * 1000)
        if current_time - self._last_topmost_time < 500:
            return
        self._last_topmost_time = current_time
            
        try:
            hwnd = int(self.winId())
            if hwnd == 0 or hwnd is None:
                return
            
            # Check if already topmost before calling SetWindowPos
            # This avoids unnecessary window operations that cause flicker
            current_ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE = -20
            WS_EX_TOPMOST = 0x00000008
            
            # Only force topmost if not already topmost
            if not (current_ex_style & WS_EX_TOPMOST):
                # Use SetWindowPos with HWND_TOPMOST to force topmost Z-order
                ctypes.windll.user32.SetWindowPos(
                    hwnd,
                    self.HWND_TOPMOST,
                    0, 0, 0, 0,
                    self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOACTIVATE | self.SWP_SHOWWINDOW
                )
            
        except Exception:
            pass
            
    def _visibility_check(self):
        """
        Checks if the overlay is actually visible and on top.
        Simplified to reduce GUI thread load - only checks essential conditions.
        """
        is_config_enabled = self.current_config.get('enabled', False)
        
        # If overlay is enabled in config but Qt thinks it's not visible, force show it
        if is_config_enabled and not self.isVisible():
            self._consecutive_hidden_count += 1
            if self._consecutive_hidden_count >= 2:
                print("[Overlay] Auto-restoring: overlay enabled but not visible")
                self.show()
                self._consecutive_hidden_count = 0
            return
        
        if not self.isVisible():
            self._consecutive_hidden_count = 0
            return
            
        try:
            hwnd = int(self.winId())
            if hwnd == 0 or hwnd is None:
                return
            
            # Only check if minimized - skip expensive WindowFromPoint checks
            is_minimized = ctypes.windll.user32.IsIconic(hwnd)
            
            if is_minimized:
                self._consecutive_hidden_count += 1
                if self._consecutive_hidden_count >= 2:
                    # Restore if minimized
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE = 9
                    self._consecutive_hidden_count = 0
            else:
                self._consecutive_hidden_count = 0
                
        except Exception:
            # Silently ignore to prevent spam
            pass
            
    def showEvent(self, event):
        """
        Override show event to ensure topmost status is applied immediately.
        """
        super().showEvent(event)
        # Force topmost once with a small delay to allow window to fully show
        QTimer.singleShot(50, self._force_topmost)
        
    def raise_(self):
        """
        Override raise_ to also force topmost.
        """
        super().raise_()
        self._force_topmost()
        
    def set_config(self, config, initial_mute_state=None):
        """
        Updates the overlay configuration.
        
        Args:
            config (dict): Configuration dictionary.
            initial_mute_state (bool, optional): Initial mute state for startup sync.
                                               If provided, synchronizes overlay with this state.
        """
        self.current_config = config.copy()
        
        # Soft Dependency Logic:
        # We always process the config, but visibility and meter state depend on 'enabled'.
        
        is_enabled = config.get('enabled', False)
        self.show_vu = config.get('show_vu', False)
        
        if not is_enabled:
            self.hide()
            self.stop_meter()
            self.topmost_timer.stop()
            # We still update internal state/position so it's ready when enabled
        
        # Update Target Device
        self.set_target_device(config.get('device_id'))
        
        opacity = config.get('opacity', 80) / 100.0
        self.setWindowOpacity(opacity)
        
        # LED Visibility depends on both Overlay Enabled AND Show VU
        self.led_dot.setVisible(self.show_vu)
        
        # Scaling
        scale = config.get('scale', 100) / 100.0
        
        # Base dimensions
        base_h = 40
        base_w = 60 if self.show_vu else 45
        base_icon = 24
        base_led = 10
        
        # Scaled dimensions
        h = int(base_h * scale)
        w = int(base_w * scale)
        icon_s = int(base_icon * scale)
        led_s = int(base_led * scale)
        
        self.resize(w, h)
        self.icon_size = icon_s
        self.icon_label.setFixedSize(icon_s, icon_s)
        self.led_dot.setFixedSize(led_s, led_s)
        
        # Update Icon Pixmap size
        path = self.icon_muted if self.is_muted else self.icon_unmuted
        pixmap = QIcon(path).pixmap(icon_s, icon_s)
        self.icon_label.setPixmap(pixmap)
        
        # Position
        self.position_mode = config.get('position_mode', 'Custom')
        self.locked = config.get('locked', False)
        self.sensitivity = config.get('sensitivity', 5) / 100.0
        
        if self.position_mode == 'Custom':
            x = config.get('x', 100)
            y = config.get('y', 100)
            self.move(x, y)
        else:
            self.apply_position()
        
        if is_enabled:
            # FIX: Sync initial mute state if provided (from startup)
            # This ensures the overlay knows the actual current mute state
            # before attempting to show and start the meter
            if initial_mute_state is not None:
                self.is_muted = initial_mute_state
            
            self.show()
            # Force topmost immediately and start timers
            self._force_topmost()
            self.topmost_timer.start()
            self.visibility_timer.start()
            # Refresh state (will start meter if needed based on actual mute state)
            self.update_status(self.is_muted)
        else:
            # Ensure meter and timers are stopped if disabled
            self.stop_meter()
            self.topmost_timer.stop()
            self.visibility_timer.stop()

    def set_target_device(self, device_id, fallback_device_id=None):
        """
        Sets the target device for the VU meter.
        
        Args:
            device_id (str): The ID of the device to monitor.
            fallback_device_id (str, optional): Fallback device ID if device_id is None.
        """
        # FIX: Use fallback device if primary device_id is not specified
        # This ensures the overlay uses the correct audio device on startup
        if device_id is None and fallback_device_id is not None:
            device_id = fallback_device_id
            
        self.target_device_id = device_id
        # Restart meter if running to switch device
        if self.meter_worker and self.meter_worker.isRunning():
            self.stop_meter()
            self.start_meter()

    def apply_position(self):
        """
        Moves the overlay to a predefined position on the screen.
        Uses availableGeometry() to respect taskbar.
        """
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()
            
        geo = screen.availableGeometry()
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
        """
        Updates the visual status of the overlay.
        
        Args:
            is_muted (bool): True if muted, False otherwise.
        """
        self.is_muted = is_muted
        
        # Update Icon
        path = self.icon_muted if is_muted else self.icon_unmuted
        size = getattr(self, 'icon_size', 24)
        pixmap = QIcon(path).pixmap(size, size)
        self.icon_label.setPixmap(pixmap)
        
        # Manage Meter
        # We only run the meter if:
        # 1. Not muted
        # 2. Overlay is enabled in config (we check current_config instead of isVisible for startup reliability)
        # 3. VU meter is enabled
        
        is_enabled = self.current_config.get('enabled', False)
        should_run_meter = (not is_muted) and is_enabled and self.show_vu
        
        if not should_run_meter:
            self.stop_meter()
            self.set_active(False)
        else:
            self.start_meter()

    def set_active(self, active):
        """
        Updates the activity LED state.
        
        Args:
            active (bool): True if voice activity is detected.
        """
        if self.is_active == active: return
        self.is_active = active
        
        # Bright Green or Transparent
        color = "#00FF00" if active else "transparent"
        self.led_dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 5px;
        """)

    def start_meter(self):
        """
        Starts the audio meter for the target device.
        Uses a background thread to avoid blocking the UI.
        """
        if not HAS_COM: return
        if self.meter_worker and self.meter_worker.isRunning(): return
        
        try:
            # Create Enumerator
            enumerator = client.CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
            
            device = None
            if self.target_device_id:
                try:
                    # GetDevice takes ID string
                    device_unk = enumerator.GetDevice(self.target_device_id)
                    device = device_unk.QueryInterface(IMMDevice)
                except Exception:
                    print(f"Could not find device with ID: {self.target_device_id}")
            
            if not device:
                # Fallback to default
                # eCapture, eConsole/0
                device_unk = enumerator.GetDefaultAudioEndpoint(eCapture, 0)
                device = device_unk.QueryInterface(IMMDevice)
            
            # Activate Meter
            meter_unk = device.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
            self.meter = meter_unk.QueryInterface(IAudioMeterInformation)
            
            # Start Audio Client to ensure meter works
            # This is CRITICAL: We need to initialize and start an audio stream
            # because some devices won't report meter values unless a stream is active.
            client_unk = device.Activate(IAudioClient._iid_, CLSCTX_ALL, None)
            self.audio_client = client_unk.QueryInterface(IAudioClient)
            
            fmt = self.audio_client.GetMixFormat()
            # ShareMode=0 (Shared), Flags=0, Duration=100ms (1000000 reftimes)
            self.audio_client.Initialize(0, 0, 1000000, 0, fmt, None)
            self.audio_client.Start()
            
            # Start worker thread instead of timer
            self.meter_worker = AudioMeterWorker(self.meter, self.sensitivity)
            self.meter_worker.peak_detected.connect(self.on_peak_detected)
            self.meter_worker.error_occurred.connect(self.stop_meter)
            self.meter_worker.start()
        except Exception as e:
            print(f"Error starting meter: {e}")
            pass

    def stop_meter(self):
        """
        Stops the audio meter and releases resources.
        """
        if self.meter_worker:
            self.meter_worker.stop()
            self.meter_worker = None
        
        self.meter = None
        
        if hasattr(self, 'audio_client') and self.audio_client:
            try:
                self.audio_client.Stop()
            except:
                pass
            self.audio_client = None
            
        self.set_active(False)
    
    @Slot(float)
    def on_peak_detected(self, peak_value):
        """
        Called when the worker thread detects a peak value.
        Runs on main thread via signal/slot.
        """
        is_loud = peak_value > self.sensitivity
        self.set_active(is_loud)

    @Slot()
    def sample_audio(self):
        """
        DEPRECATED: Now handled by AudioMeterWorker thread.
        Kept for compatibility.
        """
        pass

    # Dragging Logic
    def mousePressEvent(self, event):
        """
        Handles mouse press for dragging.
        """
        if self.locked: return
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        """
        Handles mouse move for dragging.
        """
        if self.locked: return
        if self.dragging and self.offset:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        """
        Handles mouse release to save new position.
        """
        if self.dragging:
            self.dragging = False
            # Save new position and switch to Custom mode
            self.current_config['x'] = self.x()
            self.current_config['y'] = self.y()
            self.current_config['position_mode'] = 'Custom'
            self.config_changed.emit(self.current_config)

    def closeEvent(self, event):
        """
        Handles the close event to ensure cleanup.
        """
        self.stop_meter()
        self.topmost_timer.stop()
        self.visibility_timer.stop()
        super().closeEvent(event)
