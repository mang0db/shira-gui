import sys
from typing import Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import FluentStyleSheet, FluentWindow, NavigationInterface, FluentTitleBar, FluentIconBase, \
    NavigationItemPosition
from qfluentwidgets.window.fluent_window import FluentWindowBase
from qframelesswindow import TitleBar


class CustomFluentTitleBar(TitleBar):
    """ Fluent title bar with custom button order (buttons on the left) """
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(48)

        # 기존 버튼을 레이아웃에서 제거
        self.hBoxLayout.removeWidget(self.minBtn)
        self.hBoxLayout.removeWidget(self.maxBtn)
        self.hBoxLayout.removeWidget(self.closeBtn)

        # macOS에서만 커스텀 버튼 표시
        if sys.platform == "darwin":
            # 버튼 레이아웃을 맨 앞에 추가
            self.buttonLayout = QHBoxLayout()
            self.buttonLayout.setSpacing(0)
            self.buttonLayout.setContentsMargins(0, 0, 0, 0)
            self.buttonLayout.addWidget(self.closeBtn)
            self.buttonLayout.addWidget(self.minBtn)
            self.buttonLayout.addWidget(self.maxBtn)
            self.hBoxLayout.insertLayout(0, self.buttonLayout)

            # 시스템 버튼 숨기기 (이미 TitleBar에서 생성된 버튼 사용)
            self.window().setProperty("useCustomTitleBar", True)
        else:
            # 다른 OS에서는 기존 위치에 버튼 추가
            self.vBoxLayout = QVBoxLayout()
            self.buttonLayout = QHBoxLayout()
            self.buttonLayout.setSpacing(0)
            self.buttonLayout.setContentsMargins(0, 0, 0, 0)
            self.buttonLayout.setAlignment(Qt.AlignTop)
            self.buttonLayout.addWidget(self.minBtn)
            self.buttonLayout.addWidget(self.maxBtn)
            self.buttonLayout.addWidget(self.closeBtn)
            self.vBoxLayout.addLayout(self.buttonLayout)
            self.vBoxLayout.addStretch(1)
            self.hBoxLayout.addLayout(self.vBoxLayout, 0)

        # 약간의 간격을 추가
        self.hBoxLayout.insertSpacing(1, 10)

        # 창 아이콘 추가
        self.iconLabel = QLabel(self)
        self.iconLabel.setFixedSize(18, 18)
        self.hBoxLayout.insertWidget(2, self.iconLabel, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.window().windowIconChanged.connect(self.setIcon)

        # 타이틀 레이블 추가
        self.titleLabel = QLabel(self)
        self.hBoxLayout.insertWidget(3, self.titleLabel, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.titleLabel.setObjectName('titleLabel')
        self.window().windowTitleChanged.connect(self.setTitle)

        FluentStyleSheet.FLUENT_WINDOW.apply(self)

    def setTitle(self, title):
        self.titleLabel.setText(title)
        self.titleLabel.adjustSize()

    def setIcon(self, icon):
        self.iconLabel.setPixmap(QIcon(icon).pixmap(18, 18))


class MacFluentWindow(FluentWindow):  # FluentWindowBase 대신 FluentWindow를 상속
    def __init__(self, parent=None):
        # 먼저 부모 클래스의 __init__을 호출하지 않고 필요한 초기화만 수행
        FluentWindowBase.__init__(self, parent)  # 직접 FluentWindowBase 초기화

        # 네비게이션 인터페이스와 스택 위젯 설정
        self.navigationInterface = NavigationInterface(self, showReturnButton=True)
        self.widgetLayout = QHBoxLayout()

        # 레이아웃 초기화
        self.hBoxLayout.addWidget(self.navigationInterface)
        self.hBoxLayout.addLayout(self.widgetLayout)
        self.hBoxLayout.setStretchFactor(self.widgetLayout, 1)

        self.widgetLayout.addWidget(self.stackedWidget)
        self.widgetLayout.setContentsMargins(0, 48, 0, 0)

        # macOS에서는 시스템 타이틀바 버튼 비활성화
        if sys.platform == "darwin":
            self.setSystemTitleBarButtonVisible(False)

        # 커스텀 타이틀바 설정
        self.setTitleBar(CustomFluentTitleBar(self))
        self.titleBar.raise_()

        self.navigationInterface.displayModeChanged.connect(self.titleBar.raise_)

    def addSubInterface(self, interface: QWidget, icon: Union[FluentIconBase, QIcon, str], text: str,
                        position=NavigationItemPosition.TOP, parent=None, isTransparent=False):
        # FluentWindow의 addSubInterface 메서드 사용
        return super().addSubInterface(interface, icon, text, position, parent, isTransparent)

    def resizeEvent(self, e):
        if hasattr(self, 'titleBar'):
            self.titleBar.move(46, 0)
            self.titleBar.resize(self.width()-46, self.titleBar.height())
        super().resizeEvent(e)