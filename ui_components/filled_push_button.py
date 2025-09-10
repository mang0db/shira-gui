from PySide6.QtCore import Qt, Property
from PySide6.QtGui import QColor
from qfluentwidgets import PushButton, ThemeColor, qconfig, Theme


class FilledPushButton(PushButton):
    """ Filled push button with customizable background color """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._background_color = ThemeColor.PRIMARY.color()
        self._dark_background_color = ThemeColor.DARK_1.color()
        self._update_style()

        # Connect theme change signal
        qconfig.themeChangedFinished.connect(self._update_style)

    def setColor(self, color: QColor):
        """ Set the background color of button

        Parameters
        ----------
        color: QColor
            background color
        """
        if not isinstance(color, QColor):
            color = QColor(color)

        self._background_color = color
        self._dark_background_color = self._generate_dark_color(color)
        self._update_style()

    def color(self) -> QColor:
        """ Get the background color of button """
        return self._background_color

    def setDarkColor(self, color: QColor):
        """ Set the background color for dark theme

        Parameters
        ----------
        color: QColor
            background color in dark theme
        """
        if not isinstance(color, QColor):
            color = QColor(color)

        self._dark_background_color = color
        self._update_style()

    def darkColor(self) -> QColor:
        """ Get the background color in dark theme """
        return self._dark_background_color or self._generate_dark_color(self._background_color)

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



    def _get_current_color(self) -> QColor:
        """ Get the current background color based on theme """
        if qconfig.theme == Theme.DARK:
            return self.darkColor()
        return self._background_color

    def _update_style(self):
        """ Update button style """
        bg_color = self._get_current_color()

        # Calculate text color based on background brightness
        r, g, b = bg_color.red(), bg_color.green(), bg_color.blue()
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        text_color = QColor(Qt.white) if luminance < 0.6 else QColor(Qt.black)

        # Generate style sheet
        style = f"""
            FilledPushButton {{
                background-color: {bg_color.name()};
                color: {text_color.name()};
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            
            FilledPushButton:hover {{
                background-color: {self._lighten_color(bg_color).name()};
            }}
            
            FilledPushButton:pressed {{
                background-color: {self._darken_color(bg_color).name()};
            }}
            
            FilledPushButton:disabled {{
                background-color: {self._disable_color(bg_color).name()};
                color: {self._disable_color(text_color).name()};
            }}
        """
        self.setStyleSheet(style)

    def _lighten_color(self, color: QColor, factor: float = 1.1) -> QColor:
        """ Lighten color for hover state """
        h, s, v, a = color.getHsvF()
        return QColor.fromHsvF(h, s, min(1.0, v * factor), a)

    def _darken_color(self, color: QColor, factor: float = 0.9) -> QColor:
        """ Darken color for pressed state """
        h, s, v, a = color.getHsvF()
        return QColor.fromHsvF(h, s, v * factor, a)

    def _disable_color(self, color: QColor) -> QColor:
        """ Create disabled state color """
        h, s, v, a = color.getHsvF()
        return QColor.fromHsvF(h, s * 0.5, v, a * 0.6)

    # Property for Qt Property System
    backgroundColor = Property(QColor, color, setColor)
    darkBackgroundColor = Property(QColor, darkColor, setDarkColor)