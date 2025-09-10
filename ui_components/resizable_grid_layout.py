import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout,
    QSplitter, QFrame, QLabel, QSizePolicy, QPushButton,
    QVBoxLayout, QHBoxLayout, QGraphicsBlurEffect
)
from PySide6.QtCore import Qt, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QRect, QPoint, QSize


class ResizableGridLayout(QWidget):
    def __init__(self, rows=2, cols=2, mode="global", parent=None):
        """
        :param rows: 기본 행 개수
        :param cols: 기본 열 개수
        :param mode: "global", "vertical", "horizontal" 중 하나
                     - global: 높이와 너비 모두 글로벌 조절
                     - vertical: 높이(세로)는 개별 조절, 너비(가로)는 글로벌 조절
                     - horizontal: 너비(가로)는 개별 조절, 높이(세로)는 글로벌 조절
        """
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.mode = mode  # "global", "vertical", "horizontal"
        self.animation_enabled = True

        # 비율 및 고정 사이즈 관련 설정
        self.row_ratios = {}           # {row_index: ratio}
        self.col_ratios = {}           # {col_index: ratio}
        self.fixed_sizes = {}          # {(row, col): (width, height)}
        self.fixed_row_heights = {}    # {row_index: height}
        self.include_fixed_in_ratio = True  # 고정 크기 위젯 비율 계산에 포함 여부

        self.cells = []
        for r in range(rows):
            row_list = []
            for c in range(cols):
                w = QFrame()
                w.setFrameStyle(QFrame.Box | QFrame.Plain)
                w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                row_list.append(w)
            self.cells.append(row_list)

        self.main_layout = QGridLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.container = None          # 내부 구조를 담는 QSplitter
        self.horizontal_splitters = [] # global, horizontal 모드에서 사용
        self.vertical_splitters = []   # vertical 모드에서 사용
        self._pending_sizes = None     # 모드 전환 전 크기 저장
        self._rebuild_structure()

    def setFixedRowHeight(self, row, height):
        """특정 행의 높이를 고정값으로 설정"""
        if not (0 <= row < self.rows):
            return

        self.fixed_row_heights[row] = height

        if self.mode in ("global", "horizontal"):
            for col in range(self.cols):
                self.cells[row][col].setFixedHeight(height)
        elif self.mode == "vertical":
            for splitter in self.vertical_splitters:
                widget = splitter.widget(row)
                if widget:
                    widget.setFixedHeight(height)

    def _rebuild_structure(self):
        """현재 모드, 행/열 수, 셀 배열에 따라 내부 위젯 구조를 재구성"""
        if self.container is not None:
            self.main_layout.removeWidget(self.container)
            self.container.deleteLater()

        fixed_heights = self.fixed_row_heights.copy()

        if self.mode in ("global", "horizontal"):
            self.container = QSplitter(Qt.Vertical)
            self.horizontal_splitters = []
            self.vertical_splitters = []  # 사용하지 않으므로 비워둠
            for r in range(self.rows):
                hs = QSplitter(Qt.Horizontal)
                for c in range(self.cols):
                    widget = self.cells[r][c]
                    if r in fixed_heights:
                        widget.setFixedHeight(fixed_heights[r])
                    hs.addWidget(widget)
                if self.mode == "global":
                    hs.splitterMoved.connect(self._on_horizontal_splitter_moved)
                self.horizontal_splitters.append(hs)
                self.container.addWidget(hs)
        elif self.mode == "vertical":
            self.container = QSplitter(Qt.Horizontal)
            self.vertical_splitters = []
            self.horizontal_splitters = []  # 사용하지 않으므로 비워둠
            for c in range(self.cols):
                vs = QSplitter(Qt.Vertical)
                for r in range(self.rows):
                    widget = self.cells[r][c]
                    if r in fixed_heights:
                        widget.setFixedHeight(fixed_heights[r])
                    vs.addWidget(widget)
                self.vertical_splitters.append(vs)
                self.container.addWidget(vs)

        self.main_layout.addWidget(self.container, 0, 0)

    def _on_horizontal_splitter_moved(self, pos, index):
        """Global 모드에서 한 행의 수평 splitter 변경 시, 다른 행에도 동일한 비율 적용"""
        if self.mode != "global" or not self.horizontal_splitters:
            return
        sender = self.sender()
        sizes = sender.sizes()
        total_size = sum(sizes)
        if total_size > 0:
            self.col_ratios.clear()
            for i, size in enumerate(sizes):
                self.col_ratios[i] = (size / total_size) * 100
        # 다른 행에도 비율 적용
        for splitter in self.horizontal_splitters:
            if splitter is not sender:
                splitter.blockSignals(True)
                self._apply_column_ratios(splitter)
                splitter.blockSignals(False)

    def update_mode(self, new_mode):
        """
        런타임 중 모드를 전환합니다.
        new_mode: "global", "vertical", "horizontal"
        기존 셀 위젯은 그대로 유지하면서 내부 구조를 재구성합니다.
        """
        if new_mode not in ("global", "vertical", "horizontal"):
            raise ValueError("Mode must be 'global', 'vertical' or 'horizontal'")
        if new_mode == self.mode:
            return

        self.mode = new_mode
        self._rebuild_structure()

        if self._pending_sizes:
            old_row_sizes, old_col_sizes = self._pending_sizes
            if self.mode in ("global", "horizontal"):
                self.container.setSizes(old_row_sizes)
                if self.mode == "horizontal":
                    for hs in self.horizontal_splitters:
                        hs.setSizes(old_col_sizes)
                elif self.mode == "global" and self.horizontal_splitters:
                    self.horizontal_splitters[0].setSizes(old_col_sizes)
                    for hs in self.horizontal_splitters[1:]:
                        hs.setSizes(old_col_sizes)
            elif self.mode == "vertical":
                self.container.setSizes(old_col_sizes)
                for vs in self.vertical_splitters:
                    vs.setSizes(old_row_sizes)
            self._pending_sizes = None
        else:
            if self.mode == "global" and self.horizontal_splitters:
                sizes = self.horizontal_splitters[0].sizes()
                for splitter in self.horizontal_splitters[1:]:
                    splitter.setSizes(sizes)

    def setRowRatios(self, ratios, include_fixed=None):
        """
        행의 비율을 설정
        :param ratios: 리스트 또는 딕셔너리 형태의 비율 (예: [30, 20, 50] 또는 {0: 30, 1: 20, 2: 50})
        :param include_fixed: 고정 크기 위젯 포함 여부 (None이면 기존 설정 유지)
        """
        if include_fixed is not None:
            self.include_fixed_in_ratio = include_fixed
        self.row_ratios.clear()
        if isinstance(ratios, (list, tuple)):
            for i, ratio in enumerate(ratios):
                if i < self.rows:
                    self.row_ratios[i] = ratio
        elif isinstance(ratios, dict):
            self.row_ratios.update({k: v for k, v in ratios.items() if k < self.rows})
        self._apply_ratios()

    def setColumnRatios(self, ratios, include_fixed=None):
        """
        열의 비율을 설정
        :param ratios: 리스트 또는 딕셔너리 형태의 비율
        :param include_fixed: 고정 크기 위젯 포함 여부
        """
        if include_fixed is not None:
            self.include_fixed_in_ratio = include_fixed
        self.col_ratios.clear()
        if isinstance(ratios, (list, tuple)):
            for i, ratio in enumerate(ratios):
                if i < self.cols:
                    self.col_ratios[i] = ratio
        elif isinstance(ratios, dict):
            self.col_ratios.update({k: v for k, v in ratios.items() if k < self.cols})
        self._apply_ratios()

    def setFixedCellSize(self, row, col, width=None, height=None):
        """특정 셀의 크기를 고정값으로 설정"""
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return
        widget = self.cells[row][col]
        if width is not None:
            widget.setFixedWidth(width)
        if height is not None:
            widget.setFixedHeight(height)
        if width is not None or height is not None:
            self.fixed_sizes[(row, col)] = (width, height)
        elif (row, col) in self.fixed_sizes:
            del self.fixed_sizes[(row, col)]
        self._apply_ratios()

    def _apply_ratios(self):
        """현재 설정된 비율을 splitter들에 적용"""
        if not self.row_ratios and not self.col_ratios:
            return

        if self.mode in ("global", "horizontal"):
            if self.row_ratios:
                total_height = self.container.height()
                sizes = self._calculate_sizes(self.row_ratios, total_height, is_horizontal=False)
                self.container.setSizes(sizes)
            if self.col_ratios and self.horizontal_splitters:
                for splitter in self.horizontal_splitters:
                    self._apply_column_ratios(splitter)
        elif self.mode == "vertical":
            if self.col_ratios:
                total_width = self.container.width()
                sizes = self._calculate_sizes(self.col_ratios, total_width, is_horizontal=True)
                self.container.setSizes(sizes)
            if self.row_ratios and self.vertical_splitters:
                for splitter in self.vertical_splitters:
                    total_height = splitter.height()
                    sizes = self._calculate_sizes(self.row_ratios, total_height, is_horizontal=False)
                    splitter.setSizes(sizes)

    def _apply_column_ratios(self, splitter):
        """수평 splitter에 열 비율 적용"""
        if not self.col_ratios:
            return
        total_width = splitter.width()
        sizes = self._calculate_sizes(self.col_ratios, total_width, is_horizontal=True)
        splitter.setSizes(sizes)

    def _calculate_sizes(self, ratios, total_size, is_horizontal):
        """
        비율에 따른 실제 크기 계산
        :param ratios: 비율 딕셔너리
        :param total_size: 전체 크기
        :param is_horizontal: 가로 방향 여부
        :return: 계산된 크기 리스트
        """
        count = self.cols if is_horizontal else self.rows
        sizes = [0] * count
        remaining_size = total_size
        remaining_ratio = 100
        fixed_indices = set()

        for i in range(count):
            has_fixed = False
            fixed_size = 0
            if is_horizontal:
                for row in range(self.rows):
                    if (row, i) in self.fixed_sizes:
                        width, _ = self.fixed_sizes[(row, i)]
                        if width is not None:
                            has_fixed = True
                            fixed_size = max(fixed_size, width)
            else:
                for col in range(self.cols):
                    if (i, col) in self.fixed_sizes:
                        _, height = self.fixed_sizes[(i, col)]
                        if height is not None:
                            has_fixed = True
                            fixed_size = max(fixed_size, height)
            if has_fixed:
                sizes[i] = fixed_size
                remaining_size -= fixed_size
                if self.include_fixed_in_ratio and i in ratios:
                    remaining_ratio -= ratios[i]
                fixed_indices.add(i)
        if remaining_size > 0 and remaining_ratio > 0:
            for i in range(count):
                if i not in fixed_indices and i in ratios:
                    sizes[i] = int((ratios[i] / remaining_ratio) * remaining_size)
        return sizes

    def setRowStretch(self, row, stretch):
        """행의 스트레치(비율)를 설정합니다."""
        if not (0 <= row < self.rows):
            return
        if self.mode in ("global", "horizontal"):
            self.container.setStretchFactor(row, stretch)
        elif self.mode == "vertical":
            for vs in self.vertical_splitters:
                vs.setStretchFactor(row, stretch)

    def setColumnStretch(self, col, stretch):
        """열의 스트레치(비율)를 설정합니다."""
        if not (0 <= col < self.cols):
            return
        if self.mode in ("global", "horizontal"):
            for hs in self.horizontal_splitters:
                hs.setStretchFactor(col, stretch)
        elif self.mode == "vertical":
            self.container.setStretchFactor(col, stretch)

    def setCellWidget(self, row, col, widget):
        """지정한 (row, col) 셀에 위젯을 배치합니다. (기존 위젯은 제거)"""
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return
        if self.mode in ("global", "horizontal"):
            old = self.horizontal_splitters[row].widget(col)
            if old:
                old.setParent(None)
            self.horizontal_splitters[row].insertWidget(col, widget)
        elif self.mode == "vertical":
            old = self.vertical_splitters[col].widget(row)
            if old:
                old.setParent(None)
            self.vertical_splitters[col].insertWidget(row, widget)
        self.cells[row][col] = widget

    def getCellWidget(self, row, col):
        """지정한 (row, col) 셀의 위젯을 반환합니다."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.cells[row][col]
        return None

    def _extract_nested_widgets(self, layout):
        """레이아웃에서 모든 중첩된 위젯을 추출하고 레이아웃 구조 정보도 함께 반환"""
        result = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget():
                result.append({"type": "widget", "widget": item.widget()})
            elif item.layout():
                # 레이아웃 타입과 그 안의 아이템들을 함께 저장
                nested_layout = item.layout()
                margins = nested_layout.contentsMargins()
                layout_info = {
                    "type": "layout",
                    "layout_type": type(nested_layout),
                    "items": self._extract_nested_widgets(nested_layout),
                    "spacing": nested_layout.spacing(),
                    "margins": (margins.left(), margins.top(), margins.right(), margins.bottom())
                }
                result.append(layout_info)
        return result

    def _recreate_layout_structure(self, layout_info):
        """저장된 레이아웃 정보를 바탕으로 동일한 구조의 레이아웃을 재생성"""
        if layout_info["type"] == "widget":
            return layout_info["widget"]
        elif layout_info["type"] == "layout":
            container = QWidget()
            new_layout = layout_info["layout_type"]()
            container.setLayout(new_layout)
            new_layout.setSpacing(layout_info["spacing"])
            new_layout.setContentsMargins(*layout_info["margins"])  # now unpacks tuple of integers

            for item in layout_info["items"]:
                if item["type"] == "widget":
                    new_layout.addWidget(item["widget"])
                else:
                    nested_container = self._recreate_layout_structure(item)
                    new_layout.addWidget(nested_container)

            return container

    def convertFromGridLayout(self, grid_layout):
        """
        기존 QGridLayout에 배치된 위젯들을 이 레이아웃으로 옮깁니다.
        grid_layout 내 (row, col) 위치를 기준으로 셀을 구성하며,
        위젯이 없으면 기본 placeholder(QFrame)를 생성합니다.
        nested layout의 경우 원래 구조를 그대로 유지합니다.
        기존 grid_layout은 제거됩니다.
        """
        rows = 0
        cols = 0
        cell_widgets = {}  # (row, col) -> widget

        for i in range(grid_layout.count()):
            r, c, rs, cs = grid_layout.getItemPosition(i)
            rows = max(rows, r + rs)
            cols = max(cols, c + cs)
            item = grid_layout.itemAt(i)
            if item.widget():
                cell_widgets[(r, c)] = item.widget()
            elif item.layout():
                # 레이아웃 구조 정보를 포함하여 추출
                layout = item.layout()
                margins = layout.contentsMargins()
                layout_info = {
                    "type": "layout",
                    "layout_type": type(layout),
                    "items": self._extract_nested_widgets(layout),
                    "spacing": layout.spacing(),
                    "margins": (margins.left(), margins.top(), margins.right(), margins.bottom())
                }

                # 레이아웃 구조를 그대로 재생성
                container = self._recreate_layout_structure(layout_info)
                cell_widgets[(r, c)] = container

        self.rows = rows
        self.cols = cols
        self.cells = []
        for r in range(rows):
            row_list = []
            for c in range(cols):
                if (r, c) in cell_widgets:
                    w = cell_widgets[(r, c)]
                    w.setParent(None)  # 기존 부모에서 분리
                else:
                    w = QFrame()
                    w.setFrameStyle(QFrame.Box | QFrame.Plain)
                row_list.append(w)
            self.cells.append(row_list)

        # grid_layout 내 모든 아이템 제거
        while grid_layout.count():
            item = grid_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    nested_item = item.layout().takeAt(0)
                    if nested_item.widget():
                        nested_item.widget().setParent(None)
            elif item.widget():
                item.widget().setParent(None)

        grid_layout.deleteLater()
        self._rebuild_structure()

    def setAnimationEnabled(self, enabled: bool):
        self.animation_enabled = enabled

    def switchMode(self, new_mode):
        """
        애니메이션 on/off 상태에 따라 모드를 전환합니다.
        애니메이션이 활성화된 경우, 모드 전환 애니메이션을 수행합니다.
        """
        if self.animation_enabled:
            self.animateModeChange(new_mode)
        else:
            self.update_mode(new_mode)

    def _get_widget_geometry_in(self, widget):
        """
        주어진 위젯의 좌표를 현재 ResizableGridLayout(self) 기준으로 환산하여 반환합니다.
        """
        global_pos = widget.mapToGlobal(QPoint(0, 0))
        pos_in_self = self.mapFromGlobal(global_pos)
        return QRect(pos_in_self, widget.size())

    def animateModeChange(self, new_mode):
        """
        모드 전환 시, 각 셀의 현재 모습을 캡쳐하여 오버레이에 띄운 후
        이전 위치에서 새 위치로 애니메이션과 함께 이동하며 블러 효과를 서서히 제거합니다.
        """
        # (1) 현재 splitters의 크기를 캡처 (행, 열 비율)
        if self.mode in ("global", "horizontal"):
            old_row_sizes = self.container.sizes()  # 각 행의 높이
            col_totals = [0] * self.cols
            for hs in self.horizontal_splitters:
                sizes = hs.sizes()
                for i, s in enumerate(sizes):
                    col_totals[i] += s
            old_col_sizes = [int(total / len(self.horizontal_splitters)) for total in col_totals]
        elif self.mode == "vertical":
            old_col_sizes = self.container.sizes()  # 각 열의 너비
            row_totals = [0] * self.rows
            for vs in self.vertical_splitters:
                sizes = vs.sizes()
                for i, s in enumerate(sizes):
                    row_totals[i] += s
            old_row_sizes = [int(total / len(self.vertical_splitters)) for total in row_totals]
        self._pending_sizes = (old_row_sizes, old_col_sizes)

        # (2) 각 셀의 스냅샷 캡쳐 및 오버레이 위 배치
        overlay = QWidget(self)
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay.setStyleSheet("background: transparent;")
        overlay.setGeometry(self.rect())
        overlay.show()

        overlay_items = []  # (row, col, label, blur_effect, old_geom)
        for r in range(self.rows):
            for c in range(self.cols):
                cell_widget = self.getCellWidget(r, c)
                old_geom = self._get_widget_geometry_in(cell_widget)
                pixmap = cell_widget.grab()
                label = QLabel(overlay)
                label.setPixmap(pixmap)
                label.setGeometry(old_geom)
                label.setAttribute(Qt.WA_TranslucentBackground)
                label.setStyleSheet("background: transparent;")
                label.show()
                blur_effect = QGraphicsBlurEffect(label)
                blur_effect.setBlurRadius(15)
                label.setGraphicsEffect(blur_effect)
                overlay_items.append((r, c, label, blur_effect, old_geom))

        # (3) 내부 구조 재구성 및 크기 복원
        self.update_mode(new_mode)
        overlay.raise_()
        self.layout().activate()
        QApplication.processEvents()

        # (4) 애니메이션 설정 (geometry와 blur 효과)
        anim_group = QParallelAnimationGroup(self)
        duration = 400
        for r, c, label, blur_effect, old_geom in overlay_items:
            new_widget = self.getCellWidget(r, c)
            new_geom = self._get_widget_geometry_in(new_widget)
            geom_anim = QPropertyAnimation(label, b"geometry")
            geom_anim.setDuration(duration)
            geom_anim.setStartValue(old_geom)
            geom_anim.setEndValue(new_geom)
            geom_anim.setEasingCurve(QEasingCurve.InOutQuad)
            blur_anim = QPropertyAnimation(blur_effect, b"blurRadius")
            blur_anim.setDuration(duration+100)
            blur_anim.setStartValue(20)
            blur_anim.setEndValue(0)
            blur_anim.setEasingCurve(QEasingCurve.OutQuad)
            anim_group.addAnimation(geom_anim)
            anim_group.addAnimation(blur_anim)

        def cleanup():
            overlay.deleteLater()

        anim_group.finished.connect(cleanup)
        anim_group.start(QPropertyAnimation.DeleteWhenStopped)

    def minimumSizeHint(self):
        return QSize(0, 0)


# example
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Resizable Grid Layout")
        #self.setMinimumSize(800, 600)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        button_layout = QHBoxLayout()
        self.global_button = QPushButton("Global Mode")
        self.vertical_button = QPushButton("Vertical Mode\n(높이 개별)")
        self.horizontal_button = QPushButton("Horizontal Mode\n(너비 개별)")
        self.convert_button = QPushButton("Convert from QGridLayout")
        self.toggle_anim_button = QPushButton("Animation: ON")
        button_layout.addWidget(self.global_button)
        button_layout.addWidget(self.vertical_button)
        button_layout.addWidget(self.horizontal_button)
        button_layout.addWidget(self.convert_button)
        button_layout.addWidget(self.toggle_anim_button)
        main_layout.addLayout(button_layout)

        self.grid = ResizableGridLayout(2, 2, mode="global")
        main_layout.addWidget(self.grid)
        self.setCentralWidget(central_widget)

        for r in range(2):
            for c in range(2):
                label = QLabel(f"Cell ({r}, {c})")
                label.setAlignment(Qt.AlignCenter)
                label.setStyleSheet(f"background-color: rgb({80 + r*60}, {120 + c*60}, 200);")
                self.grid.setCellWidget(r, c, label)

        self.grid.setRowStretch(0, 60)
        self.grid.setRowStretch(1, 40)
        self.grid.setColumnStretch(0, 30)
        self.grid.setColumnStretch(1, 70)

        self.global_button.clicked.connect(lambda: self.grid.switchMode("global"))
        self.vertical_button.clicked.connect(lambda: self.grid.switchMode("vertical"))
        self.horizontal_button.clicked.connect(lambda: self.grid.switchMode("horizontal"))
        self.convert_button.clicked.connect(self.convert_from_grid)
        self.toggle_anim_button.clicked.connect(self.toggle_animation)

    def toggle_animation(self):
        current = self.grid.animation_enabled
        self.grid.setAnimationEnabled(not current)
        self.toggle_anim_button.setText("Animation: ON" if not current else "Animation: OFF")

    def convert_from_grid(self):
        """
        임시 QGridLayout을 생성하여 위젯을 배치한 후,
        이를 ResizableGridLayout으로 변환하는 예제.
        """
        temp_widget = QWidget()
        temp_layout = QGridLayout(temp_widget)
        temp_layout.setSpacing(5)
        temp_layout.setContentsMargins(5, 5, 5, 5)

        # 예제: 3행 3열 구성
        for r in range(3):
            for c in range(3):
                label = QLabel(f"New Cell ({r}, {c})")
                label.setAlignment(Qt.AlignCenter)
                label.setStyleSheet(f"background-color: rgb({150 + r*30}, {150 + c*30}, 220);")
                temp_layout.addWidget(label, r, c)

        self.grid.convertFromGridLayout(temp_layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())