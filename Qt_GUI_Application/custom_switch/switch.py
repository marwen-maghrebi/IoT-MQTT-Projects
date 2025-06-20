from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtGui import QPainter, QColor

class CustomSwitch(QCheckBox):
    def __init__(self, parent=None, 
                 width=65, 
                 height=30,
                 bg_color="#777777", 
                 circle_color="#DDD", 
                 active_color="#aa00ff",
                 animation_curve=QEasingCurve.OutQuad,
                 animation_duration=300):
        super().__init__(parent)
        
        self.setFixedSize(width, height)
        self.setCursor(Qt.PointingHandCursor)
        
        # Colors
        self._bg_color = bg_color
        self._circle_color = circle_color
        self._active_color = active_color
        
        # Animation
        self._animation_curve = animation_curve
        self._animation_duration = animation_duration
        
        # Circle properties
        self._circle_radius = height - 1
        self._circle_x = 2
        self._circle_y = 2
        self._circle_end_pos = width - self._circle_radius - 1
        
        # Initialize animation
        self._animation = QPropertyAnimation(self, b"circle_position")
        self._animation.setEasingCurve(self._animation_curve)
        self._animation.setDuration(self._animation_duration)
        
        # Connect signal
        self.toggled.connect(self._animate_circle)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        bg_rect = self.rect()
        bg_color = QColor(self._active_color if self.isChecked() else self._bg_color)
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(bg_rect, bg_rect.height()/2, bg_rect.height()/2)
        
        # Draw circle
        painter.setBrush(QColor(self._circle_color))
        painter.drawEllipse(QPoint(int(self._circle_x + self._circle_radius/2), 
                                 int(self._circle_y + self._circle_radius/2)), 
                          int(self._circle_radius/2), int(self._circle_radius/2))
    
    def _animate_circle(self, checked):
        self._animation.stop()
        self._animation.setStartValue(self._circle_x)
        target_x = self._circle_end_pos if checked else 3
        self._animation.setEndValue(target_x)
        self._animation.start()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self.isChecked())
        super().mousePressEvent(event)
    
    def get_circle_position(self):
        return self._circle_x
    
    def set_circle_position(self, pos):
        self._circle_x = pos
        self.update()
        
    circle_position = pyqtProperty(int, get_circle_position, set_circle_position)