import random
import sys

from PySide6.QtCore import Property, QRectF, QPropertyAnimation, QTimer
from PySide6.QtGui import QPainter, QColor, QPainterPath
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication
from qfluentwidgets import PushButton, isDarkTheme, themeColor


#rev.2
class ProgressFillPushButton(PushButton):
    """A PushButton that fills with a smooth progress color from left to right with enhanced features."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._val = 0.0
        self._useAni = True
        self._isPaused = False
        self._isError = False

        # Color settings
        self._lightBarColor = QColor()
        self._darkBarColor = QColor()
        self.lightBackgroundColor = QColor(0, 0, 0, 155)
        self.darkBackgroundColor = QColor(255, 255, 255, 155)

        # Animation setup
        self.ani = QPropertyAnimation(self, b'val', self)
        self.ani.setDuration(150)

    def getVal(self):
        return self._val

    def setVal(self, value: float):
        self._val = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw button background
        rect = self.rect()
        path = QPainterPath()
        radius = 6
        path.addRoundedRect(rect, radius, radius)
        painter.setClipPath(path)

        # Draw progress background
        bc = self.darkBackgroundColor if isDarkTheme() else self.lightBackgroundColor
        painter.fillRect(rect, bc)

        # Draw progress bar
        if self._val > 0:
            progress_width = int(self.width() * self._val)
            progress_rect = QRectF(0, 0, progress_width, self.height())
            painter.fillRect(progress_rect, self.barColor())

        super().paintEvent(event)

    def set_progress(self, percentage: float):
        """Start progress animation with the given percentage."""
        if self._isPaused or self._isError:
            return

        target = max(0.0, min(1.0, percentage))
        if self._val >= target:
            return

        if not self._useAni:
            self.setVal(target)
            return

        self.ani.stop()
        self.ani.setEndValue(target)
        self.ani.start()

    def pause(self):
        """Pause the progress animation."""
        self._isPaused = True
        self.ani.pause()
        self.update()

    def resume(self):
        """Resume the progress animation."""
        self._isPaused = False
        self._isError = False
        self.ani.resume()
        self.update()

    def error(self):
        """Set progress state to error."""
        self._isError = True
        self.ani.stop()
        self.update()

    def reset(self):
        """Reset progress to initial state."""
        self._val = 0.0
        self._isPaused = False
        self._isError = False
        self.ani.stop()
        self.update()

    def barColor(self):
        """Get the appropriate bar color based on the current state."""
        if self._isPaused:
            return QColor(252, 225, 0) if isDarkTheme() else QColor(157, 93, 0)

        if self._isError:
            return QColor(255, 153, 164) if isDarkTheme() else QColor(196, 43, 28)

        return self.darkBarColor() if isDarkTheme() else self.lightBarColor()

    def lightBarColor(self):
        return self._lightBarColor if self._lightBarColor.isValid() else themeColor()

    def darkBarColor(self):
        return self._darkBarColor if self._darkBarColor.isValid() else themeColor()

    def setCustomBarColor(self, light, dark):
        """Set custom bar colors for light and dark themes."""
        self._lightBarColor = QColor(light)
        if not dark:
            self._darkBarColor = self._generate_dark_color(self._lightBarColor)
        self._darkBarColor = QColor(dark)
        self.update()

    def setCustomBackgroundColor(self, light, dark):
        """Set custom background colors for light and dark themes."""
        self.lightBackgroundColor = QColor(light)
        self.darkBackgroundColor = QColor(dark)
        self.update()

    def _generate_dark_color(self, color: QColor) -> QColor:
        """ Generate appropriate dark theme color from light theme color """
        h, s, l, a = color.getHslF()

        if l < 0.3:  # 어두운 색상은 더 밝게
            new_l = min(0.7, l * 2.5)
            new_s = max(0.4, s * 0.85)  # 채도를 약간 줄이고 최소값 보장
        elif l > 0.7:  # 밝은 색상은 더 어둡게
            new_l = l * 0.6
            new_s = max(0.3, s * 0.8)  # 채도를 줄이되 너무 칙칙하지 않게
        else:  # 중간 톤은 적당히 어둡게 조정
            new_l = max(0.5, l * 0.85)
            new_s = max(0.4, s * 0.7)  # 채도를 크게 줄이지 않음

        # 채도의 상한선 제한 (너무 선명한 색 방지)
        new_s = min(0.7, new_s)

        return QColor.fromHslF(h, new_s, new_l, a)

    # Property definitions
    useAni = Property(bool, lambda self: self._useAni, lambda self, v: setattr(self, '_useAni', v))
    val = Property(float, getVal, setVal)


class TestApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Progress Fill PushButton Test")
        self.resize(400, 200)

        self.layout = QVBoxLayout(self)

        self.progress_button = ProgressFillPushButton(self)
        self.progress_button.setText("Start Progress")
        self.progress_button.setCustomBarColor(QColor("#001e36"), None)
        self.layout.addWidget(self.progress_button)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)

        self.progress_button.clicked.connect(self.start_progress)

        self.current_progress = 0.0

    def start_progress(self):
        self.progress_button.reset()
        self.current_progress = 0.0
        self.timer.start(random.randint(100, 500))

    def update_progress(self):
        if self.current_progress >= 1.0:
            self.timer.stop()
            self.progress_button.setText("Progress Complete")
        else:
            self.current_progress += random.uniform(0.05, 0.15)
            self.progress_button.set_progress(self.current_progress)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    test_app = TestApp()
    test_app.show()

    sys.exit(app.exec())
