from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QSizePolicy, QPushButton, QHBoxLayout, )


class CollapsibleSection(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.is_expanded = True
        self.content_height = 0

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.title_container = QWidget()
        self.title_layout = QHBoxLayout(self.title_container)  # 수정: self.title_container에 레이아웃 설정
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        self.title_layout.setSpacing(2)
        self.layout.addWidget(self.title_container)

        self.title_button = QPushButton(title)
        self.title_button.setStyleSheet("QPushButton { text-align: left; border: none; }")
        self.title_button.clicked.connect(self.toggle)
        self.title_button.setFont(QFont("Noto Sans KR", 10, QFont.DemiBold))
        self.title_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.update_button_icon()
        self.title_layout.addWidget(self.title_button)

        self.title_line = QFrame()
        self.title_line.setFrameShape(QFrame.HLine)
        self.title_line.setFrameShadow(QFrame.Sunken)
        self.title_line.setStyleSheet("background-color: #c0c0c0;")
        self.title_line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.title_line.setFixedHeight(1)
        self.title_layout.mousePressEvent = self.toggle
        self.title_layout.addWidget(self.title_line)


        self.content_widget = QWidget()
        self.content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 0, 0, 0)
        self.content_layout.setSpacing(5)
        self.layout.addWidget(self.content_widget)

        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        self.separator.setFixedHeight(2)
        self.separator.setStyleSheet("background-color: #c0c0c0;")
        self.layout.addWidget(self.separator)

        self.animation = QPropertyAnimation(self.content_widget, b"maximumHeight")
        self.animation.setDuration(350)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        self.update_content_height()

    def add_widget(self, widget):
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.content_layout.addWidget(widget)
        self.update_content_height()

    def update_content_height(self):
        self.content_height = self.content_layout.sizeHint().height()
        if self.is_expanded:
            self.content_widget.setMaximumHeight(self.content_height)
        else:
            self.content_widget.setMaximumHeight(0)

    def toggle(self):
        self.is_expanded = not self.is_expanded
        self.update_button_icon()
        self.start_animation()

    def start_animation(self):
        self.animation.stop()
        if self.is_expanded:
            self.animation.setStartValue(0)
            self.animation.setEndValue(self.content_height)
        else:
            self.animation.setStartValue(self.content_height)
            self.animation.setEndValue(0)
        self.animation.start()

    def update_button_icon(self):
        title = self.title_button.text().split(" ", 1)[-1]  # Remove existing icon
        if self.is_expanded:
            self.title_button.setText("\u25bc " + title)
        else:
            self.title_button.setText("\u25b6 " + title)