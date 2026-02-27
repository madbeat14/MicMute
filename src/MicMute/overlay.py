"""On-Screen Display and overlay widgets for MicMute.

This module provides OSD notifications and persistent overlay widgets
for displaying microphone mute status and voice activity.
"""

from __future__ import annotations

import ctypes
import threading
from typing import Any, ClassVar

from PySide6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QRect,
    Signal,
    Slot,
    QThread,
)
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QIcon, QPixmap, QCursor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QApplication,
    QHBoxLayout,
)

__all__ = ["MetroOSD", "StatusOverlay", "AudioMeterWorker"]


class MetroOSD(QWidget):
    """A Windows 10/11 Metro-style On-Screen Display (OSD) for mute status.

    Displays a temporary overlay showing the current microphone mute state
    with smooth fade in/out animations.

    Attributes:
        osd_size: Size of the OSD widget in pixels.
        bg_color: Background color with alpha transparency.
        radius: Corner radius for rounded rectangle.
        duration: How long the OSD stays visible in milliseconds.
        position: Position on screen (e.g., 'Bottom-Center').
        target_opacity: Target opacity level (0.0-1.0).
    """

    def __init__(self, icon_unmuted_path: str, icon_muted_path: str) -> None:
        """Initialize the OSD widget.

        Args:
            icon_unmuted_path: Path to the unmuted icon.
            icon_muted_path: Path to the muted icon.
        """
        super().__init__()

        # Window Flags
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        # Animation
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(150)
        self.opacity_anim.setEasingCurve(QEasingCurve.OutQuad)

        self.fade_out_anim = QPropertyAnimation(self, b"windowOpacity")
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

    def set_config(self, config: dict[str, Any]) -> None:
        """Update the OSD configuration.

        Args:
            config: Configuration dictionary with keys:
                - duration: Display duration in milliseconds
                - position: Screen position string
                - size: Widget size in pixels
                - opacity: Opacity percentage (0-100)
        """
        self.duration = config.get("duration", 1500)
        self.position = config.get("position", "Bottom-Center")
        self.osd_size = config.get("size", 150)
        self.target_opacity = config.get("opacity", 80) / 100.0
        self.resize(self.osd_size, self.osd_size)

    def show_osd(self, is_muted: bool) -> None:
        """Display the OSD with the current mute state.

        Args:
            is_muted: True if muted, False otherwise.
        """
        self.current_renderer = (
            self.renderer_muted if is_muted else self.renderer_unmuted
        )
        self.update()

        # Reset Timer
        self.hide_timer.stop()
        self.fade_out_anim.stop()

        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.apply_position()
            self.show()

            # Fade In
            self.opacity_anim.setStartValue(0.0)
            self.opacity_anim.setEndValue(self.target_opacity)
            self.opacity_anim.start()
        else:
            self.setWindowOpacity(self.target_opacity)
            self.apply_position()

        self.hide_timer.start(self.duration)

    def start_fade_out(self) -> None:
        """Start the fade-out animation."""
        self.fade_out_anim.setStartValue(self.target_opacity)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.start()

    def apply_position(self) -> None:
        """Calculate and set the OSD position based on configuration.

        Uses availableGeometry() to respect taskbar.
        """
        # Get screen where cursor is, or primary
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()

        geo = screen.availableGeometry()
        w, h = self.width(), self.height()
        margin = 40

        # Calculate X
        if "Left" in self.position:
            x = geo.x() + margin
        elif "Right" in self.position:
            x = geo.x() + geo.width() - w - margin
        else:  # Center/Middle
            x = geo.x() + (geo.width() - w) // 2

        # Calculate Y
        if "Top" in self.position:
            y = geo.y() + margin
        elif "Bottom" in self.position:
            y = geo.y() + geo.height() - h - margin
            if self.position == "Bottom-Center":
                y = geo.y() + geo.height() - h - 100
        else:  # Middle/Center
            y = geo.y() + (geo.height() - h) // 2

        self.move(x, y)

    def paintEvent(self, event: Any) -> None:
        """Handle the paint event to draw the OSD background and icon.

        Args:
            event: The paint event.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw Background
        painter.setBrush(QBrush(self.bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), self.radius, self.radius)

        # Draw Icon
        if self.current_renderer and self.current_renderer.isValid():
            icon_size = int(self.width() * 0.65)
            x = (self.width() - icon_size) // 2
            y = (self.height() - icon_size) // 2
            self.current_renderer.render(
                painter, QRect(x, y, icon_size, icon_size)
            )


# --- PERSISTENT OVERLAY ---

try:
    from .utils import (
        IAudioMeterInformation,
        IMMDeviceEnumerator,
        CLSID_MMDeviceEnumerator,
        eCapture,
        DEVICE_STATE_ACTIVE,
        CLSCTX_ALL,
        IAudioClient,
        IMMDevice,
    )
    from comtypes import client
    from ctypes import POINTER, cast

    HAS_COM: bool = True
except ImportError:
    HAS_COM = False


class AudioMeterWorker(QThread):
    """Worker thread for sampling audio meter values.

    Runs COM operations in background to avoid blocking UI.

    Signals:
        peak_detected: Emitted with the current peak value (float).
        error_occurred: Emitted when an error occurs.
    """

    peak_detected: Signal = Signal(float)
    error_occurred: Signal = Signal()

    def __init__(self, meter: Any, sensitivity: float) -> None:
        """Initialize the worker.

        Args:
            meter: The IAudioMeterInformation COM object.
            sensitivity: The sensitivity threshold for peak detection.
        """
        super().__init__()
        self.meter = meter
        self.sensitivity = sensitivity
        self._running = False
        self._lock = threading.Lock()

    def set_sensitivity(self, value: float) -> None:
        """Update the sensitivity threshold thread-safely.

        Args:
            value: New sensitivity value.
        """
        with self._lock:
            self.sensitivity = value

    def stop(self) -> None:
        """Stop the worker thread gracefully."""
        self._running = False
        self.wait(100)  # Wait up to 100ms for thread to finish

    def run(self) -> None:
        """Run the meter sampling loop.

        Samples the audio meter at 50ms intervals (20Hz) until stopped.
        """
        self._running = True
        while self._running:
            try:
                if self.meter:
                    peak_value = self.meter.GetPeakValue()
                    self.peak_detected.emit(peak_value)
            except Exception:
                self.error_occurred.emit()
                break
            self.msleep(50)


class StatusOverlay(QWidget):
    """A persistent overlay widget showing microphone status and voice activity.

    Displays a small floating widget with mute status icon and optional
    voice activity indicator. Supports drag positioning and automatic
    topmost window management.

    Attributes:
        config_changed: Signal emitted when configuration changes.
    """

    config_changed: Signal = Signal(dict)

    # Windows API constants for forcing topmost
    HWND_TOPMOST: ClassVar[int] = -1
    SWP_NOMOVE: ClassVar[int] = 0x0002
    SWP_NOSIZE: ClassVar[int] = 0x0001
    SWP_NOACTIVATE: ClassVar[int] = 0x0010
    SWP_SHOWWINDOW: ClassVar[int] = 0x0040

    def __init__(self, icon_unmuted_path: str, icon_muted_path: str) -> None:
        """Initialize the overlay widget.

        Args:
            icon_unmuted_path: Path to the unmuted icon.
            icon_muted_path: Path to the muted icon.
        """
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.icon_unmuted = icon_unmuted_path
        self.icon_muted = icon_muted_path
        self.is_muted = False
        self.show_vu = False
        self.target_device_id: str | None = None

        # Pixmap cache: keyed by (path, size) to avoid recreating QIcon every update
        self._pixmap_cache: dict[tuple[str, int], QPixmap] = {}

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)

        # Icon Label
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        layout.addWidget(self.icon_label)

        # Activity LED (Dot)
        self.led_dot = QLabel()
        self.led_dot.setFixedSize(10, 10)
        self.led_dot.setStyleSheet("""
            background-color: transparent;
            border-radius: 5px;
        """)
        layout.addWidget(self.led_dot)

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
        self.offset: Any | None = None

        # Audio Meter
        self.meter: Any | None = None
        self.meter_worker: AudioMeterWorker | None = None
        self.audio_client: Any | None = None

        # Topmost Timer - Re-assert topmost position periodically
        self.topmost_timer = QTimer()
        self.topmost_timer.setInterval(500)
        self.topmost_timer.timeout.connect(self._force_topmost)

        # Visibility Monitor
        self.visibility_timer = QTimer()
        self.visibility_timer.setInterval(3000)
        self.visibility_timer.timeout.connect(self._visibility_check)
        self._consecutive_hidden_count = 0

        self.resize(60, 40)

        self.position_mode = "Custom"
        self.locked = False
        self.current_config: dict[str, Any] = {}
        self.sensitivity = 0.05
        self.is_active = False

    def _force_topmost(self) -> None:
        """Force the window to the top of the TOPMOST Z-order using Windows API.

        Always re-asserts topmost position so that other TOPMOST windows
        (e.g. fullscreen apps, game overlays) cannot sit above this widget.
        """
        if not self.isVisible():
            return

        try:
            hwnd = int(self.winId())
            if hwnd == 0:
                return

            # Always call SetWindowPos to re-assert our position at the very
            # top of the TOPMOST stack, even when WS_EX_TOPMOST is already set.
            # Without this, other TOPMOST windows can appear above us.
            ctypes.windll.user32.SetWindowPos(
                hwnd,
                self.HWND_TOPMOST,
                0,
                0,
                0,
                0,
                self.SWP_NOMOVE
                | self.SWP_NOSIZE
                | self.SWP_NOACTIVATE
                | self.SWP_SHOWWINDOW,
            )
        except Exception:
            pass

    def _visibility_check(self) -> None:
        """Check if the overlay is actually visible and on top.

        Verifies Qt visibility, minimized state, and that the
        WS_EX_TOPMOST extended style has not been stripped by another
        application or the OS.
        """
        is_config_enabled = self.current_config.get("enabled", False)

        if is_config_enabled and not self.isVisible():
            self._consecutive_hidden_count += 1
            if self._consecutive_hidden_count >= 2:
                print("[Overlay] Auto-restoring: overlay enabled but not visible")
                self.show()
                self._force_topmost()
                self._consecutive_hidden_count = 0
            return

        if not self.isVisible():
            self._consecutive_hidden_count = 0
            return

        try:
            hwnd = int(self.winId())
            if hwnd == 0:
                return

            is_minimized = ctypes.windll.user32.IsIconic(hwnd)

            if is_minimized:
                self._consecutive_hidden_count += 1
                if self._consecutive_hidden_count >= 2:
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE = 9
                    self._force_topmost()
                    self._consecutive_hidden_count = 0
            else:
                self._consecutive_hidden_count = 0

            # Verify WS_EX_TOPMOST style hasn't been stripped
            GWL_EXSTYLE = -20
            WS_EX_TOPMOST = 0x00000008
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if not (ex_style & WS_EX_TOPMOST):
                print("[Overlay] WS_EX_TOPMOST lost, re-asserting...")
                self._force_topmost()
        except Exception:
            pass

    def showEvent(self, event: Any) -> None:
        """Override show event to ensure topmost status is applied.

        Args:
            event: The show event.
        """
        super().showEvent(event)
        self._force_topmost()

    def raise_(self) -> None:
        """Override raise_ to also force topmost."""
        super().raise_()
        self._force_topmost()

    def set_config(
        self, config: dict[str, Any], initial_mute_state: bool | None = None
    ) -> None:
        """Update the overlay configuration.

        Args:
            config: Configuration dictionary.
            initial_mute_state: Initial mute state for startup sync.
        """
        self.current_config = config.copy()

        is_enabled = config.get("enabled", False)
        self.show_vu = config.get("show_vu", False)

        self.set_target_device(config.get("device_id"))

        opacity = config.get("opacity", 80) / 100.0
        self.setWindowOpacity(opacity)

        self.led_dot.setVisible(self.show_vu)

        scale = config.get("scale", 100) / 100.0

        base_h = 40
        base_w = 60 if self.show_vu else 45
        base_icon = 24

        h = int(base_h * scale)
        w = int(base_w * scale)
        icon_s = int(base_icon * scale)

        self.resize(w, h)
        self.icon_size = icon_s
        self.icon_label.setFixedSize(icon_s, icon_s)

        path = self.icon_muted if self.is_muted else self.icon_unmuted
        self.icon_label.setPixmap(self._get_cached_pixmap(path, icon_s))

        self.position_mode = config.get("position_mode", "Custom")
        self.locked = config.get("locked", False)
        self.sensitivity = config.get("sensitivity", 5) / 100.0

        if self.position_mode == "Custom":
            x = config.get("x", 100)
            y = config.get("y", 100)
            self.move(x, y)
        else:
            self.apply_position()

        if is_enabled:
            if initial_mute_state is not None:
                self.is_muted = initial_mute_state

            self.show()
            self._force_topmost()
            self.topmost_timer.start()
            self.visibility_timer.start()
            self.update_status(self.is_muted)
        else:
            self.hide()
            self.stop_meter()
            self.topmost_timer.stop()
            self.visibility_timer.stop()

    def set_target_device(
        self, device_id: str | None, fallback_device_id: str | None = None
    ) -> None:
        """Set the target device for the VU meter.

        Args:
            device_id: The ID of the device to monitor.
            fallback_device_id: Fallback device ID if device_id is None.
        """
        if device_id is None and fallback_device_id is not None:
            device_id = fallback_device_id

        self.target_device_id = device_id
        if self.meter_worker and self.meter_worker.isRunning():
            self.stop_meter()
            self.start_meter()

    def apply_position(self) -> None:
        """Move the overlay to a predefined position on the screen.

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

        if "Left" in self.position_mode:
            x += margin
        elif "Right" in self.position_mode:
            x += geo.width() - w - margin
        else:
            x += (geo.width() - w) // 2

        if "Top" in self.position_mode:
            y += margin
        elif "Bottom" in self.position_mode:
            y += geo.height() - h - margin
        else:
            y += (geo.height() - h) // 2

        self.move(x, y)

    def _get_cached_pixmap(self, path: str, size: int) -> QPixmap:
        """Return a cached pixmap, creating it only if not already cached.

        Args:
            path: Path to the icon file.
            size: Desired pixmap size in pixels.

        Returns:
            The cached QPixmap.
        """
        key = (path, size)
        if key not in self._pixmap_cache:
            self._pixmap_cache[key] = QIcon(path).pixmap(size, size)
        return self._pixmap_cache[key]

    def update_status(self, is_muted: bool) -> None:
        """Update the visual status of the overlay.

        Args:
            is_muted: True if muted, False otherwise.
        """
        self.is_muted = is_muted

        path = self.icon_muted if is_muted else self.icon_unmuted
        size = getattr(self, "icon_size", 24)
        self.icon_label.setPixmap(self._get_cached_pixmap(path, size))

        is_enabled = self.current_config.get("enabled", False)
        should_run_meter = (not is_muted) and is_enabled and self.show_vu

        if not should_run_meter:
            self.stop_meter()
            self.set_active(False)
        else:
            self.start_meter()

    def set_active(self, active: bool) -> None:
        """Update the activity LED state.

        Args:
            active: True if voice activity is detected.
        """
        if self.is_active == active:
            return
        self.is_active = active

        color = "#00FF00" if active else "transparent"
        self.led_dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 5px;
        """)

    def start_meter(self) -> None:
        """Start the audio meter for the target device.

        Uses a background thread to avoid blocking the UI.
        """
        if not HAS_COM:
            return
        if self.meter_worker and self.meter_worker.isRunning():
            return

        try:
            enumerator = client.CreateObject(
                CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator
            )

            device: Any | None = None
            if self.target_device_id:
                try:
                    device_unk = enumerator.GetDevice(self.target_device_id)
                    device = device_unk.QueryInterface(IMMDevice)
                except Exception:
                    print(f"Could not find device with ID: {self.target_device_id}")

            if not device:
                device_unk = enumerator.GetDefaultAudioEndpoint(eCapture, 0)
                device = device_unk.QueryInterface(IMMDevice)

            meter_unk = device.Activate(
                IAudioMeterInformation._iid_, CLSCTX_ALL, None
            )
            self.meter = meter_unk.QueryInterface(IAudioMeterInformation)

            # Start Audio Client to ensure meter works
            client_unk = device.Activate(IAudioClient._iid_, CLSCTX_ALL, None)
            self.audio_client = client_unk.QueryInterface(IAudioClient)

            fmt = self.audio_client.GetMixFormat()
            self.audio_client.Initialize(0, 0, 1000000, 0, fmt, None)
            self.audio_client.Start()

            self.meter_worker = AudioMeterWorker(self.meter, self.sensitivity)
            self.meter_worker.peak_detected.connect(self.on_peak_detected)
            self.meter_worker.error_occurred.connect(self.stop_meter)
            self.meter_worker.start()
        except Exception as e:
            print(f"Error starting meter: {e}")

    def stop_meter(self) -> None:
        """Stop the audio meter and release resources."""
        if self.meter_worker:
            try:
                self.meter_worker.peak_detected.disconnect(self.on_peak_detected)
                self.meter_worker.error_occurred.disconnect(self.stop_meter)
            except (RuntimeError, TypeError):
                pass  # Already disconnected
            self.meter_worker.stop()
            self.meter_worker = None

        self.meter = None

        if self.audio_client:
            try:
                self.audio_client.Stop()
            except Exception:
                pass
            self.audio_client = None

        self.set_active(False)

    @Slot(float)
    def on_peak_detected(self, peak_value: float) -> None:
        """Handle peak detection from worker thread.

        Args:
            peak_value: The detected peak value.
        """
        is_loud = peak_value > self.sensitivity
        self.set_active(is_loud)

    # Dragging Logic
    def mousePressEvent(self, event: Any) -> None:
        """Handle mouse press for dragging.

        Args:
            event: The mouse event.
        """
        if self.locked:
            return
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event: Any) -> None:
        """Handle mouse move for dragging.

        Args:
            event: The mouse event.
        """
        if self.locked:
            return
        if self.dragging and self.offset:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event: Any) -> None:
        """Handle mouse release to save new position.

        Args:
            event: The mouse event.
        """
        if self.dragging:
            self.dragging = False
            self.current_config["x"] = self.x()
            self.current_config["y"] = self.y()
            self.current_config["position_mode"] = "Custom"
            self.config_changed.emit(self.current_config)
            self._force_topmost()

    def closeEvent(self, event: Any) -> None:
        """Handle the close event to ensure cleanup.

        Args:
            event: The close event.
        """
        self.stop_meter()
        self.topmost_timer.stop()
        self.visibility_timer.stop()
        super().closeEvent(event)
