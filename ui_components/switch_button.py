from enum import Enum

from PySide6.QtCore import Qt, Property, Signal, QEvent, QPropertyAnimation, QSize
from PySide6.QtGui import QColor, QPainter, QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget, QVBoxLayout, QSizePolicy
from qfluentwidgets import ToolButton, NavigationWidget
from qfluentwidgets.common.overload import singledispatchmethod
from qfluentwidgets.common.style_sheet import FluentStyleSheet, themeColor, ThemeColor, isDarkTheme


class Indicator(ToolButton):
    """ Indicator of switch button """

    checkedChanged = Signal(bool)

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setCheckable(True)
        self.setFixedSize(36, 20)

        self._sliderX = 4
        self.slideAni = QPropertyAnimation(self, b'sliderX', self)
        self.slideAni.setDuration(120)

        self.toggled.connect(self._toggleSlider)

        self.setAttribute(Qt.WA_TranslucentBackground)

    def mouseReleaseEvent(self, e):
        """ toggle checked state when mouse release"""
        super().mouseReleaseEvent(e)
        self.checkedChanged.emit(self.isChecked())

    def _toggleSlider(self):
        self.slideAni.setEndValue(20 if self.isChecked() else 4)
        self.slideAni.start()

    def toggle(self):
        self.setChecked(not self.isChecked())

    def setDown(self, isDown: bool):
        self.isPressed = isDown
        super().setDown(isDown)

    def setHover(self, isHover: bool):
        self.isHover = isHover
        self.update()

    def paintEvent(self, e):
        """ paint indicator """
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        self._drawBackground(painter)
        self._drawCircle(painter)

    def _drawBackground(self, painter: QPainter):
        r = self.height() / 2
        painter.setPen(self._borderColor())
        painter.setBrush(self._backgroundColor())
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), r, r)

    def _drawCircle(self, painter: QPainter):
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._sliderColor())
        painter.drawEllipse(int(self.sliderX), 4, 12, 12)

    def _backgroundColor(self):
        isDark = isDarkTheme()

        if self.isChecked():
            if not self.isEnabled():
                return QColor(255, 255, 255, 41) if isDark else QColor(0, 0, 0, 56)
            if self.isPressed:
                return ThemeColor.LIGHT_2.color()
            elif self.isHover:
                return ThemeColor.LIGHT_1.color()

            return themeColor()
        else:
            if not self.isEnabled():
                return QColor(0, 0, 0, 0)
            if self.isPressed:
                return QColor(255, 255, 255, 18) if isDark else QColor(0, 0, 0, 23)
            elif self.isHover:
                return QColor(255, 255, 255, 10) if isDark else QColor(0, 0, 0, 15)

            return QColor(0, 0, 0, 0)

    def _borderColor(self):
        isDark = isDarkTheme()

        if self.isChecked():
            return self._backgroundColor() if self.isEnabled() else QColor(0, 0, 0, 0)
        else:
            if self.isEnabled():
                return QColor(255, 255, 255, 153) if isDark else QColor(0, 0, 0, 133)

            return QColor(255, 255, 255, 41) if isDark else QColor(0, 0, 0, 56)

    def _sliderColor(self):
        isDark = isDarkTheme()

        if self.isChecked():
            if self.isEnabled():
                return QColor(Qt.black if isDark else Qt.white)

            return QColor(255, 255, 255, 77) if isDark else QColor(255, 255, 255)
        else:
            if self.isEnabled():
                return QColor(255, 255, 255, 201) if isDark else QColor(0, 0, 0, 156)

            return QColor(255, 255, 255, 96) if isDark else QColor(0, 0, 0, 91)

    def getSliderX(self):
        return self._sliderX

    def setSliderX(self, x):
        self._sliderX = max(x, 5)
        self.update()

    sliderX = Property(float, getSliderX, setSliderX)


class IndicatorPosition(Enum):
    """ Indicator position """
    LEFT = 0
    RIGHT = 1


class CustomSwitchButton(NavigationWidget):
    """ Switch button class with icon and text support """

    checkedChanged = Signal(bool)

    @singledispatchmethod
    def __init__(self, parent: QWidget = None, indicatorPos=IndicatorPosition.LEFT):
        super().__init__(parent=parent, isSelectable = False)
        self._text = ""
        self._offText = ""
        self._onText = ""
        self._offIcon = None
        self._onIcon = None
        self.__spacing = 12
        self._isCompact = False
        self._iconSize = QSize(20, 20)

        self.indicatorPos = indicatorPos
        self.mainLayout = QVBoxLayout(self)
        self.hBox = QHBoxLayout()
        self.indicator = Indicator(self)
        self.iconLabel = QLabel(self)
        self.textLabel = QLabel(self)

        self.__initWidget()

    @__init__.register
    def _(self, text: str = '', parent: QWidget = None, indicatorPos=IndicatorPosition.LEFT):
        self.__init__(parent, indicatorPos)
        self._offText = text
        self.setText(text)

    def __initWidget(self):
        """ initialize widgets """
        self.setAttribute(Qt.WA_StyledBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.installEventFilter(self)

        self.setFixedSize(70, 60)
        self.hBox.setAlignment(Qt.AlignLeft)

        self.hBox.setSpacing(self.__spacing)
        self.hBox.setContentsMargins(0, 26, 0, 0)

        self.indicator.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.iconLabel.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.iconLabel.setAttribute(Qt.WA_TranslucentBackground)
        self.iconLabel.setStyleSheet("background: transparent;")
        self.textLabel.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.hBox.addWidget(self.indicator)
        self.hBox.addWidget(self.iconLabel)
        self.hBox.addWidget(self.textLabel)

        self.mainLayout.setContentsMargins(2, 0, 2, 0)
        self.mainLayout.addLayout(self.hBox)

        # 아이콘 레이블 초기 설정
        self.iconLabel.setAlignment(Qt.AlignCenter)

        # Default style sheet
        FluentStyleSheet.SWITCH_BUTTON.apply(self)

        # Connect signals
        self.indicator.toggled.connect(self._updateText)
        self.indicator.toggled.connect(self.checkedChanged)

    def eventFilter(self, obj, e: QEvent):
        if obj is self and self.isEnabled():
            if e.type() == QEvent.MouseButtonPress:
                self.indicator.setDown(True)
            elif e.type() == QEvent.MouseButtonRelease:
                self.indicator.setDown(False)
                self.indicator.toggle()
            elif e.type() == QEvent.Enter:
                self.indicator.setHover(True)
            elif e.type() == QEvent.Leave:
                self.indicator.setHover(False)

        return super().eventFilter(obj, e)

    def isChecked(self):
        return self.indicator.isChecked()

    def setChecked(self, isChecked):
        """ set checked state """
        self.indicator.setChecked(isChecked)
        self._updateText()

    def toggleChecked(self):
        """ toggle checked state """
        self.indicator.setChecked(not self.indicator.isChecked())

    def _updateText(self):
        """ Update text and icon based on current state """
        is_checked = self.isChecked()
        icon = self._onIcon if is_checked else self._offIcon
        text = self._onText if is_checked else self._offText

        if icon:
            self.iconLabel.setPixmap(icon.pixmap(self._iconSize))
        else:
            self.iconLabel.clear()

        if not self._isCompact:
            self.textLabel.setText(text)
            self.textLabel.setVisible(bool(text))
        else:
            self.textLabel.setVisible(False)

        self.adjustSize()

    def getText(self):
        return self._text

    def setText(self, text: str):
        """ Set text for the label """
        self._text = text
        self._offText = text  # Default to using text as off text
        self.textLabel.setText(text)
        self.textLabel.setVisible(bool(text) and not self._isCompact)
        self.adjustSize()

    def setOnIcon(self, icon: QIcon):
        """ Set icon for ON state """
        self._onIcon = icon
        if self.isChecked():
            self._updateText()

    def setOffIcon(self, icon: QIcon):
        """ Set icon for OFF state """
        self._offIcon = icon
        if not self.isChecked():
            self._updateText()

    def setIconSize(self, size: QSize):
        """ Set size for icons """
        self._iconSize = size
        self._updateText()

    def getSpacing(self):
        return self.__spacing

    def setSpacing(self, spacing):
        self.__spacing = spacing
        self.hBox.setSpacing(spacing)
        self.update()

    def getOnText(self):
        return self._onText

    def setOnText(self, text: str):
        """ Set text for ON state """
        self._onText = text
        if self.isChecked():
            self._updateText()

    def getOffText(self):
        return self._offText

    def setOffText(self, text: str):
        """ Set text for OFF state """
        self._offText = text
        if not self.isChecked():
            self._updateText()

    def setCompacted(self, compacted: bool):
        """ Toggle compact mode - icon above the switch """
        if self._isCompact == compacted:
            return

        self._isCompact = compacted

        if compacted:
            # 컴팩트 모드: 아이콘을 스위치 위로 이동
            self.iconLabel.setParent(None)
            self.iconLabel.setParent(self)
            self.iconLabel.show()
            self.iconLabel.setGeometry(
                (36 - self._iconSize.width()) // 2,
                8,
                self._iconSize.width(),
                self._iconSize.height()
            )
            self.textLabel.hide()
        else:
            # 확장 모드: 아이콘을 수평 레이아웃으로 되돌림
            self.iconLabel.setParent(None)
            self.hBox.insertWidget(1, self.iconLabel)
            self.textLabel.setVisible(bool(self._text))

        self._updateText()
        self.adjustSize()

    def resizeEvent(self, event):
        """ Handle resize events to maintain layout """
        super().resizeEvent(event)
        if self._isCompact and self.iconLabel:
            self.iconLabel.setGeometry(
                (36 - self._iconSize.width()) // 2,
                8,
                self._iconSize.width(),
                self._iconSize.height()
            )

    spacing = Property(int, getSpacing, setSpacing)
    checked = Property(bool, isChecked, setChecked)
    text = Property(str, getText, setText)
    onText = Property(str, getOnText, setOnText)
    offText = Property(str, getOffText, setOffText)