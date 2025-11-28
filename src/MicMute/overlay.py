from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QIcon, QPixmap, QCursor
from PySide6.QtSvg import QSvgRenderer

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
        self.icon_unmuted = icon_unmuted_path
        self.icon_muted = icon_muted_path
        self.current_icon_path = self.icon_unmuted
        
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
        self.current_icon_path = self.icon_muted if is_muted else self.icon_unmuted
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
        if self.current_icon_path:
            renderer = QSvgRenderer(self.current_icon_path)
            if renderer.isValid():
                # Scale icon to 65% of container
                icon_size = int(self.width() * 0.65)
                x = (self.width() - icon_size) // 2
                y = (self.height() - icon_size) // 2
                renderer.render(painter, QRect(x, y, icon_size, icon_size))
