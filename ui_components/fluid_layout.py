from PySide6.QtCore import (Qt, QSize, QRect, QPoint, QTimer, QObject, Signal,
                            QPropertyAnimation, QParallelAnimationGroup, QEasingCurve)
from PySide6.QtWidgets import QLayout, QApplication

'''
https://doc.qt.io/qt-5/qtwidgets-layouts-flowlayout-example.html
https://doc.qt.io/qt-5/layout.html#how-to-write-a-custom-layout-manager
'''

class LayoutChangeNotifier(QObject):
    layoutChanged = Signal()
    layoutSwitched = Signal(str)


class FlowLayout(QLayout):
    """
    개선된 FlowLayout - 위젯을 유동적으로 배치하는 레이아웃
    """
    def __init__(self, parent=None, LRmargin=0, TBmargin=0, h_spacing=10, v_spacing=10):
        super().__init__(parent)
        self.itemList = []
        self.setContentsMargins(LRmargin, TBmargin, LRmargin, TBmargin)
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._min_column_width = 154
        self.row_positions = []
        self._enabled = True  # 레이아웃 활성화 상태 추가
        self._cached_size_hint = QSize()
        self._layout_dirty = True  # 레이아웃이 갱신 필요한지 추적

    def __del__(self):
        self.clear()

    def clear(self):
        """모든 아이템을 제거하고 메모리 정리"""
        while self.count():
            item = self.takeAt(0)
            if item:
                del item
        self._layout_dirty = True

    def setEnabled(self, enabled):
        """레이아웃 활성화/비활성화"""
        self._enabled = enabled
        if enabled and self._layout_dirty:
            self.invalidate()

    def addItem(self, item):
        self.itemList.append(item)
        self._layout_dirty = True
        if self._enabled:
            self.invalidate()

    def addWidget(self, widget):
        """편의를 위한 위젯 추가 메소드"""
        super().addWidget(widget)
        self._layout_dirty = True
        if self._enabled:
            self.invalidate()

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            item = self.itemList.pop(index)
            self._layout_dirty = True
            if self._enabled:
                self.invalidate()
            return item
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        if width <= 0:
            return 0
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        if not self._enabled or rect.width() <= 0 or rect.height() <= 0:
            super().setGeometry(rect)
            return

        if rect.width() < self._min_column_width:
            # 최소 너비보다 작을 경우 처리
            super().setGeometry(rect)
            return

        super().setGeometry(rect)
        self.doLayout(rect, False)
        self._layout_dirty = False

    def sizeHint(self):
        if self._layout_dirty or not self._cached_size_hint.isValid():
            self._cached_size_hint = self._calculateSizeHint()
        return self._cached_size_hint

    def _calculateSizeHint(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.sizeHint())

        # 아이템이 있을 경우 spacing 고려
        if self.itemList:
            # 여러 행을 가정하여 대략적인 크기 계산
            count = len(self.itemList)
            avg_width = size.width() + self._h_spacing
            avg_height = size.height() + self._v_spacing

            # 대략적인 행과 열 계산
            cols = max(1, int(1000 / avg_width))  # 1000은 적당한 기본 너비
            rows = (count + cols - 1) // cols

            width = cols * avg_width
            height = rows * avg_height

            size = QSize(width, height)

        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        # 최소 너비 설정
        size.setWidth(max(size.width(), self._min_column_width))
        return size

    def doLayout(self, rect, testOnly):
        if not self._enabled and not testOnly:
            return 0

        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(+left, +top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        lineHeight = 0
        self.row_positions = [y]

        for item in self.itemList:
            widget_size = item.sizeHint()
            if not widget_size.isValid():
                continue

            nextX = x + widget_size.width() + self._h_spacing

            # 다음 줄로 넘어가야 하는지 확인
            if nextX - self._h_spacing > effective_rect.right() and lineHeight > 0:
                if effective_rect.width() >= self._min_column_width:
                    x = effective_rect.x()
                    y = y + lineHeight + self._v_spacing
                    self.row_positions.append(y)
                    nextX = x + widget_size.width() + self._h_spacing
                    lineHeight = 0
                else:
                    # 너무 좁아서 배치 중단
                    break

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), widget_size))

            x = nextX
            lineHeight = max(lineHeight, widget_size.height())

        # 마지막 행 높이 추가
        result = y + lineHeight - effective_rect.y()
        return result

    def getRowPositions(self):
        return self.row_positions

    def setMinColumnWidth(self, width):
        """최소 컬럼 너비 설정"""
        self._min_column_width = max(50, width)  # 너무 작은 값 방지
        self._layout_dirty = True
        if self._enabled:
            self.invalidate()

class AnimatedFlowLayout(FlowLayout):
    """
    위젯 위치 변경 시 애니메이션을 적용하는 FlowLayout
    """
    def __init__(self, parent=None, LRmargin=30, TBmargin=0, h_spacing=30, v_spacing=20):
        super().__init__(parent, LRmargin, TBmargin, h_spacing, v_spacing)
        self.notifier = LayoutChangeNotifier()
        self.widget_positions = {}
        self.animation_group = QParallelAnimationGroup()
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.triggerAnimation)
        self.animation_duration = 270  # ms
        self.batch_add_mode = False  # 여러 위젯 일괄 추가 모드
        self.pending_widgets = []  # 일괄 추가 대기 중인 위젯
        self.animation_enabled = True  # 애니메이션 활성화 여부

    def setAnimationEnabled(self, enabled):
        """애니메이션 활성화/비활성화"""
        self.animation_enabled = enabled

    def setAnimationDuration(self, duration_ms):
        """애니메이션 지속 시간 설정"""
        self.animation_duration = max(0, min(2000, duration_ms))  # 0-2000ms 범위 제한

    def startBatchAdd(self):
        """여러 위젯 일괄 추가 모드 시작"""
        self.batch_add_mode = True
        self.pending_widgets = []
        self.setEnabled(False)  # 레이아웃 업데이트 비활성화

    def endBatchAdd(self):
        """일괄 추가 모드 종료 및 애니메이션 시작"""
        self.batch_add_mode = False
        self.setEnabled(True)  # 레이아웃 업데이트 활성화

        # 애니메이션 시작 (타이머 사용하여 모든 위젯이 배치된 후 애니메이션 시작)
        QTimer.singleShot(10, self.triggerAnimation)

    def setEnabled(self, enabled):
        """레이아웃 활성화/비활성화"""
        self._enabled = enabled
        if enabled and self._layout_dirty:
            self.invalidate()
            if hasattr(self, 'pending_widgets') and self.pending_widgets:
                # 활성화될 때 애니메이션 트리거
                QTimer.singleShot(10, self.triggerAnimation)

    def addWidget(self, widget):
        """위젯 추가 - 일괄 모드 지원"""
        if self.batch_add_mode:
            # 일괄 추가 모드일 때 모든 위젯을 (0,0)에 배치
            super(FlowLayout, self).addWidget(widget)
            self.pending_widgets.append(widget)
            widget.move(0, 0)  # 모든 위젯을 (0,0)에 배치
        else:
            # 일반 추가 모드
            super().addWidget(widget)

    def doLayout(self, rect, testOnly):
        # 활성화 되어있지 않거나 테스트 모드일 경우 기본 동작 수행
        if (not self._enabled and not testOnly) or rect.width() <= 0:
            return 0

        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(+left, +top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        lineHeight = 0
        self.row_positions = [y]
        new_positions = {}

        for item in self.itemList:
            widget = item.widget()
            if not widget:
                continue

            widget_size = item.sizeHint()
            if not widget_size.isValid():
                continue

            nextX = x + widget_size.width() + self._h_spacing
            if nextX - self._h_spacing > effective_rect.right() and lineHeight > 0:
                if effective_rect.width() >= self._min_column_width:
                    x = effective_rect.x()
                    y = y + lineHeight + self._v_spacing
                    self.row_positions.append(y)
                    nextX = x + widget_size.width() + self._h_spacing
                    lineHeight = 0
                else:
                    break

            new_pos = QPoint(x, y)
            if not testOnly:
                new_positions[widget] = new_pos

            x = nextX
            lineHeight = max(lineHeight, widget_size.height())

        if not testOnly and self.animation_enabled and new_positions and new_positions != self.widget_positions:
            # 레이아웃 변경이 있고 애니메이션이 활성화된 경우에만 애니메이션 실행
            self.resize_timer.start(50)  # 더 많은 변경사항을 기다리기 위한 짧은 딜레이
            self.new_positions = new_positions
            self.notifier.layoutChanged.emit()

        return y + lineHeight - effective_rect.y()

    def triggerAnimation(self):
        """애니메이션 시작 트리거"""
        if self.animation_enabled:
            self.animateWidgets(getattr(self, 'new_positions', {}))

    def animateWidgets(self, new_positions):
        """위젯 위치 변경 애니메이션"""
        if not self.animation_enabled or not new_positions:
            # 애니메이션이 비활성화되어 있거나 새 위치가 없으면 즉시 위치 설정
            for widget, pos in new_positions.items():
                widget.move(pos)
            self.widget_positions = new_positions.copy()
            return

        # 실행 중인 애니메이션 중지
        if self.animation_group and self.animation_group.state() == QParallelAnimationGroup.Running:
            self.animation_group.stop()

        # 새 애니메이션 그룹 생성
        self.animation_group = QParallelAnimationGroup()

        # 애니메이션 추가
        has_animations = False

        # 모든 위젯에 애니메이션 적용
        for widget, new_pos in new_positions.items():
            # 위젯의 현재 위치에서 새 위치로 애니메이션
            start_pos = widget.pos()

            # 새로 추가된 위젯이면서 배치 모드일 때는 이미 (0,0)에 있음
            if widget not in self.widget_positions and not self.batch_add_mode:
                widget.move(start_pos)  # 시작 위치 설정

            # 애니메이션 생성
            animation = QPropertyAnimation(widget, b"pos")
            animation.setDuration(self.animation_duration)
            animation.setStartValue(start_pos)
            animation.setEndValue(new_pos)
            animation.setEasingCurve(QEasingCurve.OutCubic)  # 부드러운 감속 효과
            self.animation_group.addAnimation(animation)
            has_animations = True

        # 애니메이션 실행
        if has_animations:
            self.animation_group.start()

        # 위젯 위치 캐시 업데이트
        self.widget_positions = new_positions.copy()

    def clear(self):
        """모든 아이템 제거 및 메모리 정리"""
        # 실행 중인 애니메이션 중지
        if self.animation_group and self.animation_group.state() == QParallelAnimationGroup.Running:
            self.animation_group.stop()

        # 위젯 위치 캐시 초기화
        self.widget_positions.clear()
        self.pending_widgets.clear()

        # 부모 클래스의 clear 호출
        super().clear()

class ListLayout(QLayout):
    """
    위젯을 수직으로 나열하는 간단한 레이아웃 (QVBoxLayout과 유사)
    """
    def __init__(self, parent=None, LRmargin=10, TBmargin=10, spacing=10):
        super().__init__(parent)
        self.itemList = []
        self.setContentsMargins(LRmargin, TBmargin, LRmargin, TBmargin)
        self._spacing = spacing

    def __del__(self):
        self.clear()

    def clear(self):
        while self.count():
            item = self.takeAt(0)
            if item:
                if item.widget():
                    item.widget().setParent(None)
                del item

    def addItem(self, item):
        self.itemList.append(item)
        self.invalidate()

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return False

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect)

    def sizeHint(self):
        """호출할 메서드 이름을 문자열로 전달"""
        return self.calculateSize("sizeHint")

    def minimumSize(self):
        """호출할 메서드 이름을 문자열로 전달"""
        return self.calculateSize("minimumSize")

    def calculateSize(self, method_name: str):
        """
        주어진 메서드 이름(sizeHint 또는 minimumSize)을 사용하여 전체 크기를 계산
        """
        total_size = QSize(0, 0)
        for item in self.itemList:
            # getattr를 사용해 문자열 이름으로 실제 메서드를 가져와 호출
            size_func = getattr(item, method_name)
            item_size = size_func()

            total_size.setHeight(total_size.height() + item_size.height())
            total_size.setWidth(max(total_size.width(), item_size.width()))

        if self.itemList:
            total_size.setHeight(total_size.height() + (len(self.itemList) - 1) * self._spacing)

        left, top, right, bottom = self.getContentsMargins()
        total_size += QSize(left + right, top + bottom)
        return total_size

    def doLayout(self, rect):
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(+left, +top, -right, -bottom)
        y = effective_rect.y()

        for item in self.itemList:
            widget_height = item.sizeHint().height()
            item.setGeometry(QRect(effective_rect.x(), y, effective_rect.width(), widget_height))
            y += widget_height + self._spacing

class FluidLayout(QLayout):
    """
    AnimatedFlowLayout과 ListLayout 간의 전환을 애니메이션으로 처리하는 컨테이너 레이아웃
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._flowLayout = AnimatedFlowLayout(h_spacing=10, v_spacing=10)
        self._listLayout = ListLayout(spacing=5, LRmargin=5, TBmargin=5)
        self._layouts = {
            "flow": self._flowLayout,
            "list": self._listLayout
        }
        self._active_layout_name = "flow"
        self._animation_group = QParallelAnimationGroup()
        self.animation_duration = 350

    @property
    def active_layout(self):
        return self._layouts[self._active_layout_name]

    def hasHeightForWidth(self):
        """활성 레이아웃이 너비에 따른 높이를 지원하는지 여부를 반환합니다."""
        return self.active_layout.hasHeightForWidth()

    def heightForWidth(self, width):
        """활성 레이아웃에 너비에 따른 높이 계산을 위임합니다."""
        return self.active_layout.heightForWidth(width)

    def setLayoutMode(self, mode_name: str):
        if mode_name not in self._layouts or mode_name == self._active_layout_name:
            return
        if self._animation_group.state() == QParallelAnimationGroup.Running:
            self._animation_group.stop()

        target_layout = self._layouts[mode_name]
        parent_widget = self.parentWidget()
        if not parent_widget:
            return

        target_geometries = self._calculate_target_geometries(target_layout, parent_widget.rect())
        self._animation_group = QParallelAnimationGroup()
        for i in range(self.count()):
            widget = self.itemAt(i).widget()
            if widget in target_geometries:
                anim = QPropertyAnimation(widget, b"geometry")
                anim.setDuration(self.animation_duration)
                anim.setStartValue(widget.geometry())
                anim.setEndValue(target_geometries[widget])
                anim.setEasingCurve(QEasingCurve.OutCubic)
                self._animation_group.addAnimation(anim)

        self._active_layout_name = mode_name

        # 애니메이션이 끝나면 레이아웃을 완전히 다시 계산하도록 강제합니다.
        self._animation_group.finished.connect(self.invalidate)
        self._animation_group.start()

        # 즉시 레이아웃 무효화 신호를 보내서 QScrollArea가 변경을 인지하게 합니다.
        self.invalidate()

    def _calculate_target_geometries(self, layout, rect):
        geometries = {}
        if isinstance(layout, ListLayout):
            left, top, right, bottom = layout.getContentsMargins()
            effective_rect = rect.adjusted(+left, +top, -right, -bottom)
            y = effective_rect.y()
            for item in layout.itemList:
                widget_height = item.sizeHint().height()
                geometries[item.widget()] = QRect(effective_rect.x(), y, effective_rect.width(), widget_height)
                y += widget_height + layout._spacing
        elif isinstance(layout, FlowLayout):
            left, top, right, bottom = layout.getContentsMargins()
            effective_rect = rect.adjusted(+left, +top, -right, -bottom)
            x = effective_rect.x()
            y = effective_rect.y()
            lineHeight = 0
            for item in layout.itemList:
                widget_size = item.sizeHint()
                nextX = x + widget_size.width() + layout._h_spacing
                if nextX - layout._h_spacing > effective_rect.right() and lineHeight > 0:
                    x = effective_rect.x()
                    y = y + lineHeight + layout._v_spacing
                    lineHeight = 0
                geometries[item.widget()] = QRect(QPoint(x, y), widget_size)
                x = x + widget_size.width() + layout._h_spacing
                lineHeight = max(lineHeight, widget_size.height())
        return geometries

    def addItem(self, item):
        self._flowLayout.addItem(item)
        self._listLayout.addItem(item)

    def addWidget(self, widget):
        super().addWidget(widget)

    def count(self):
        return self._flowLayout.count()

    def itemAt(self, index):
        return self._flowLayout.itemAt(index)

    def takeAt(self, index):
        list_item = self._listLayout.takeAt(index)
        flow_item = self._flowLayout.takeAt(index)
        return flow_item or list_item

    def setGeometry(self, rect):
        super().setGeometry(rect)
        if self._animation_group.state() != QParallelAnimationGroup.Running:
            self.active_layout.setGeometry(rect)

    def sizeHint(self):
        return self.active_layout.sizeHint()

    def minimumSize(self):
        return self.active_layout.minimumSize()

    def expandingDirections(self):
        return self.active_layout.expandingDirections()

    def invalidate(self):
        self.active_layout.invalidate()
        super().invalidate()

    def clear(self):
        self._flowLayout.clear()
        self._listLayout.clear()
        self.invalidate()