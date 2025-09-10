from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QScrollArea


class SmoothScrollArea2(QScrollArea):
    def __init__(self, parent=None):
        super(SmoothScrollArea2, self).__init__(parent)
        self._animation = QPropertyAnimation(self.verticalScrollBar(), b"value")
        self._animation.setDuration(300)  # 기본 애니메이션 지속 시간
        self._animation.setEasingCurve(QEasingCurve.OutCubic)  # 감속 효과

    def wheelEvent(self, event):
        scroll_bar = self.verticalScrollBar()

        # 현재 애니메이션이 진행 중인지 확인
        if self._animation.state() == QPropertyAnimation.Running:
            # 현재 애니메이션이 끝나는 위치에서 새로운 애니메이션 시작
            current_value = self._animation.endValue()
        else:
            # 애니메이션이 진행 중이 아니면 현재 스크롤 위치에서 시작
            current_value = scroll_bar.value()

        # 휠 이벤트에 따른 새로운 목표 위치 계산
        wheel_delta = event.angleDelta().y() * 1.5  # 스크롤 민감도 조정
        end_value = current_value - wheel_delta

        # 스크롤 바의 범위를 초과하지 않도록 제한
        end_value = max(scroll_bar.minimum(), min(scroll_bar.maximum(), end_value))

        # 새 목표 위치로의 애니메이션 설정
        self._animation.stop()
        self._animation.setStartValue(scroll_bar.value())  # 현재 스크롤 위치에서 시작
        self._animation.setEndValue(end_value)  # 가속된 목표 위치로 애니메이션
        self._animation.setDuration(300)  # 지속 시간을 초기화 또는 조정 가능
        self._animation.start()

        event.accept()