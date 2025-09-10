from PySide6.QtCore import QRect, QRectF, Qt, QSize
from PySide6.QtGui import QPainter, QFontMetrics, QPalette
from PySide6.QtWidgets import QStyleOptionButton, QStyle
from qfluentwidgets import PushButton


class WordWrapPushButton(PushButton):
    """
    A button class that extends PushButton to support automatic text wrapping
    and height adjustment for long text.
    """
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        option = QStyleOptionButton()
        self.initStyleOption(option)

        self.style().drawControl(QStyle.CE_PushButtonBevel, option, painter, self)
        if self.hasFocus():
            self.style().drawPrimitive(QStyle.PE_FrameFocusRect, option, painter, self)

        content_rect = self.style().subElementRect(QStyle.SE_PushButtonContents, option, self)
        margin = 4
        if not self.icon().isNull():
            icon_size = self.iconSize()
            if self.isRightToLeft():
                content_rect.adjust(0, 0, -icon_size.width() - margin, 0)
            else:
                content_rect.adjust(icon_size.width() + margin, 0, 0, 0)

        # Draw centered text with word wrapping
        painter.setPen(self.palette().color(QPalette.ButtonText))
        painter.drawText(content_rect, Qt.AlignCenter | Qt.TextWordWrap, self.text())

        if not self.icon().isNull():
            icon_size = self.iconSize()
            if self.isRightToLeft():
                x = content_rect.right() + margin
            else:
                x = content_rect.left() - icon_size.width() - margin
            y = (self.height() - icon_size.height()) // 2
            icon_rect = QRect(x, y, icon_size.width(), icon_size.height())

            if not self.isEnabled():
                painter.setOpacity(0.3628)
            elif self.isPressed:
                painter.setOpacity(0.786)

            self._drawIcon(self._icon, painter, QRectF(icon_rect))

    def sizeHint(self):
        base_hint = super().sizeHint()
        fm = QFontMetrics(self.font())

        option = QStyleOptionButton()
        self.initStyleOption(option)
        content_rect = self.style().subElementRect(QStyle.SE_PushButtonContents, option, self)

        margin = 4
        if not self.icon().isNull():
            icon_size = self.iconSize()
            if self.isRightToLeft():
                content_rect.adjust(0, 0, -icon_size.width() - margin, 0)
            else:
                content_rect.adjust(icon_size.width() + margin, 0, 0, 0)

        text_rect = fm.boundingRect(content_rect, Qt.TextWordWrap | Qt.AlignCenter, self.text())
        extra = 12  # Additional vertical margin (6 pixels top and bottom)
        height = text_rect.height() + extra

        if not self.icon().isNull():
            icon_h = self.iconSize().height() + extra
            height = max(height, icon_h)

        return QSize(base_hint.width(), height)
