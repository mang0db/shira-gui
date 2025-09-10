import sys

import qfluentwidgets
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QPoint, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QWidget, QVBoxLayout, QLabel, QApplication
)


class ToolTipSlider(qfluentwidgets.Slider):
    def __init__(self, *args, always_show_tooltip=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._tooltipFormat = "{}"
        self._tooltip = CustomToolTip(text='', parent=self)
        self._tooltip.hide()
        self._always_show_tooltip = always_show_tooltip

        self._tooltip_min = None
        self._tooltip_max = None
        self._original_min = self.minimum()
        self._original_max = self.maximum()

        # 항상 표시 모드일 때는 초기화 후 툴팁을 보여줌
        if self._always_show_tooltip:
            self._delayed_show_tooltip()

    def _delayed_show_tooltip(self):
        """위젯이 완전히 초기화된 후 툴팁을 표시"""
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._show_always_tooltip)

    def _show_always_tooltip(self):
        """항상 표시 모드에서 툴팁을 보여줌"""
        if self._always_show_tooltip:
            self._showTooltip()

    def set_always_show_tooltip(self, always_show: bool):
        """항상 표시 모드를 동적으로 변경"""
        self._always_show_tooltip = always_show
        if always_show:
            self._showTooltip()
        else:
            self.hideTooltip()

    def setRange(self, min_val: int, max_val: int):
        """
        슬라이더의 범위를 설정하고, 툴팁 계산에 사용될
        원본 최소/최대값을 갱신합니다.
        """
        super().setRange(min_val, max_val)
        self._original_min = self.minimum()
        self._original_max = self.maximum()
        # 항상 표시 모드일 경우, 범위가 변경되었으므로 툴팁을 즉시 업데이트합니다.
        if self._always_show_tooltip:
            self._showTooltip()

    def set_tooltip_minmax(self, min_val: float, max_val: float):
        self._tooltip_min = min_val
        self._tooltip_max = max_val
        # 항상 표시 모드일 때는 값이 변경되면 툴팁 업데이트
        if self._always_show_tooltip:
            self._showTooltip()

    def reset_tooltip_minmax(self):
        self._tooltip_min = None
        self._tooltip_max = None
        # 항상 표시 모드일 때는 값이 변경되면 툴팁 업데이트
        if self._always_show_tooltip:
            self._showTooltip()

    def _map_value(self, value):
        if self._tooltip_min is None or self._tooltip_max is None:
            return value
        ratio = (value - self._original_min) / (self._original_max - self._original_min)
        mapped_value = self._tooltip_min + ratio * (self._tooltip_max - self._tooltip_min)
        return mapped_value

    def setTooltipFormat(self, format_string: str):
        self._tooltipFormat = format_string
        # 항상 표시 모드일 때는 포맷이 변경되면 툴팁 업데이트
        if self._always_show_tooltip:
            self._showTooltip()

    def setTooltipPlacement(self, placement: str):
        """
        set tooltip placement
        :param placement: 'above', 'below', 'left', 'right'
        """
        if hasattr(self._tooltip, 'setTooltipPlacement'):
            self._tooltip.setTooltipPlacement(placement)
            # 항상 표시 모드일 때는 위치가 변경되면 툴팁 업데이트
            if self._always_show_tooltip:
                self._showTooltip()

    def _showTooltip(self, pos=None):
        mapped_value = self._map_value(self.value())
        formatted_value = self._tooltipFormat.format(mapped_value)

        old_size = self._tooltip.size()
        self._tooltip.setText(formatted_value)
        self._tooltip.adjustSize()

        new_size = self._tooltip.size()
        if pos is None:
            pos = self.handle.rect().center()
            global_pos = self.handle.mapToGlobal(pos)
        else:
            global_pos = pos

        if self._tooltip.isVisible() and old_size != new_size:
            self.sizeAnimation = QPropertyAnimation(self._tooltip, b"size")
            self.sizeAnimation.setDuration(150)
            self.sizeAnimation.setStartValue(old_size)
            self.sizeAnimation.setEndValue(new_size)
            self.sizeAnimation.start()

        final_pos = self._tooltip.calculatePosition(global_pos, new_size)
        self._tooltip.move(final_pos)
        self._tooltip.show()

    def hideTooltip(self):
        # 항상 표시 모드가 아닐 때만 숨김
        if not self._always_show_tooltip:
            self._tooltip.hide()

    def setValue(self, value):
        super().setValue(value)
        # 항상 표시 모드일 때는 값이 변경되면 툴팁 업데이트
        if self._always_show_tooltip:
            self._showTooltip()

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        self._showTooltip()

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        self._showTooltip()

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if self.rect().contains(e.position().toPoint()):
            self._showTooltip()
        else:
            self.hideTooltip()

    def enterEvent(self, e):
        super().enterEvent(e)
        self._showTooltip()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self.hideTooltip()


class CustomToolTip(qfluentwidgets.ToolTip):
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)

        self.setObjectName("CustomToolTip")
        self.setStyleSheet("""
        QFrame#container {
            background-color: rgba(245, 245, 245, 242);
            border-radius: 4px;
            padding: 4px 8px;
        }
        QLabel#contentLabel {
            color: black;
            font-size: 12px;
        }
        """)

        shadow_effect = QGraphicsDropShadowEffect(self)
        shadow_effect.setBlurRadius(15)
        shadow_effect.setOffset(0, 4)
        shadow_effect.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow_effect)

        self.sizeAnimation = QPropertyAnimation(self, b"size")
        self.sizeAnimation.setDuration(150)
        self.sizeAnimation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._placement = 'above'  #(above, below, left, right)

        self.setDuration(-1)

    def setTooltipPlacement(self, placement: str):
        """
        set tooltip placement
        :param placement: 'above', 'below', 'left', 'right'
        """
        self._placement = placement

    def setText(self, text):
        old_size = self.size()
        super().setText(text)
        self.adjustSize()
        new_size = self.size()
        if self.isVisible() and old_size != new_size:
            self.sizeAnimation.setStartValue(old_size)
            self.sizeAnimation.setEndValue(new_size)
            self.sizeAnimation.start()

    def _createContainer(self):
        container = QFrame(self)
        container.setObjectName("container")
        container.setMinimumWidth(45)
        container.setMinimumHeight(25)
        return container

    def calculatePosition(self, handle_pos: QPoint, tooltip_size):
        x = handle_pos.x() - tooltip_size.width() // 2
        y = handle_pos.y() - tooltip_size.height()
        gap = 10

        if self._placement == 'below':
            y = handle_pos.y() + gap
        elif self._placement == 'above':
            y = handle_pos.y() - tooltip_size.height() - gap
        elif self._placement == 'left':
            x = handle_pos.x() - tooltip_size.width() - gap
            y = handle_pos.y() - tooltip_size.height() // 2
        elif self._placement == 'right':
            x = handle_pos.x() + gap
            y = handle_pos.y() - tooltip_size.height() // 2

        return QPoint(x, y)


class ExampleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ToolTipSlider Example")
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        # 일반 슬라이더 (hover시에만 표시)
        self.label1 = QLabel("일반 슬라이더 (hover시 표시):", self)
        layout.addWidget(self.label1)

        self.slider1 = ToolTipSlider(Qt.Horizontal, self)
        self.slider1.setRange(0, 100)
        self.slider1.set_tooltip_minmax(0.0, 1.0)
        self.slider1.setTooltipFormat("{:.2f}")
        self.slider1.setTooltipPlacement("above")
        layout.addWidget(self.slider1)

        self.slider1.valueChanged.connect(lambda v: self.label1.setText(f"일반 슬라이더: {(v):.2f}"))

        # 항상 표시 슬라이더
        self.label2 = QLabel("항상 표시 슬라이더:", self)
        layout.addWidget(self.label2)

        self.slider2 = ToolTipSlider(Qt.Horizontal, always_show_tooltip=True, parent=self)
        self.slider2.setRange(1, 8)
        self.slider2.set_tooltip_minmax(1, 8)
        self.slider2.setTooltipFormat("{:.0f}")
        self.slider2.setTooltipPlacement("below")
        layout.addWidget(self.slider2)

        self.slider2.valueChanged.connect(lambda v: self.label2.setText(f"항상 표시 슬라이더: {(v):.1f}"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ExampleWindow()
    window.show()
    sys.exit(app.exec())