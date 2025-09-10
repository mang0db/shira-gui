import math
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QFrame, QWidget, QLabel, QVBoxLayout, QSizePolicy, QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect, QSpacerItem, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QMenu, QProgressBar,
    QTextEdit)
from PySide6.QtGui import QPainter, QPen, QColor, QAction, QIcon, QActionGroup, QTextOption, QBrush, QCursor
from PySide6.QtGui import QMouseEvent, QFont
from PySide6.QtCore import Qt, Signal, QTimer, QRectF


def ptToPx(pt_size: float) -> int:
    screen_dpi = QApplication.primaryScreen().logicalDotsPerInch()
    illustrator_ppi = 100  # Adobe Illustrator's PPI
    return int(pt_size * (screen_dpi / illustrator_ppi))


class CustomProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 100)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.base_speed = 3  # base speed
        self.step = 0
        self.direction = 1
        self.infinite_mode = True
        self.timer.start(16)  #update every 1/60 sec.
        self.infinite_chunk_color = QColor(255, 112, 51)
        self.infinite_background_color = QColor(255, 187, 153)
        self.chunk_width_ratio = 0.3

    def gaussian(self, x, mean, sigma):
        return math.exp(-0.5 * ((x - mean) / sigma) ** 2)

    def update_animation(self):
        if self.infinite_mode:
            bar_width = self.width()
            chunk_width = bar_width * self.chunk_width_ratio
            max_position = bar_width - chunk_width

            # apply gaussian
            mean = max_position / 2
            sigma = max_position / 3  # high sigma val. = gradual spd change.
            speed_multiplier = self.gaussian(self.step, mean, sigma)

            # calc. speed
            speed = self.base_speed * speed_multiplier

            # update pos
            self.step += self.direction * speed

            # check boundary
            if self.step >= max_position:
                self.step = max_position
                self.direction = -1
            elif self.step <= 0:
                self.step = 0
                self.direction = 1

            self.update()

    def paintEvent(self, event):
        if self.infinite_mode:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # background
            painter.setBrush(QBrush(self.infinite_background_color))
            painter.setPen(Qt.NoPen)
            painter.drawRect(self.rect())

            # chunck
            bar_width = self.width()
            bar_height = self.height()
            chunk_width = bar_width * self.chunk_width_ratio

            rect = QRectF(self.step, 0, chunk_width, bar_height)
            painter.setBrush(QBrush(self.infinite_chunk_color))
            painter.drawRect(rect)
        else:
            super().paintEvent(event)

    def stopInfinite(self):
        self.infinite_mode = False
        self.setRange(0, 100)
        self.timer.stop()
        self.update()

    def startInfinite(self):
        self.infinite_mode = True
        self.setRange(0, 0)
        self.step = 0  # 시작 위치 init
        self.direction = 1  # 이동 방향 init
        self.timer.start(16)
        self.update()

    def set_progress_value(self, value):
        if not self.infinite_mode:
            self.setValue(value)

# focus out 감지하는 커스텀 TextEdit
class CustomTextEdit(QTextEdit):
    editingFinished = Signal()  # 커스텀 시그널 정의

    def __init__(self, parent=None):
        super().__init__(parent)

    def setEditMode(self, enable):
        self.editMode = enable
        self.updateEditMode()

    def updateEditMode(self):
        if self.editMode:
            self.setReadOnly(False)
            self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
            self.setTextInteractionFlags(self.textInteractionFlags() | Qt.TextInteractionFlag.TextEditorInteraction)
            self.viewport().setCursor(QCursor(Qt.CursorShape.IBeamCursor))
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        else:
            self.setReadOnly(True)
            self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            self.viewport().setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self.editMode:
            self.editingFinished.emit()


class ThumbnailView(QGraphicsView):
    def __init__(self, pixmap):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(pixmap.height() + 30)
        self.setStyleSheet("background: transparent; border: none;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.set_pixmap(pixmap)

    def set_pixmap(self, pixmap):
        self.scene.clear()
        pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(pixmap_item)
        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(19)
        shadow_effect.setOffset(0, 8)
        shadow_effect.setColor(QColor(0, 0, 0, 60))
        pixmap_item.setGraphicsEffect(shadow_effect)
        self.scene.setSceneRect(pixmap.rect())
        self.setAlignment(Qt.AlignmentFlag.AlignTop)


class ThumbnailContainer(QWidget):
    FONT_SIZE_LARGE = 40
    FONT_SIZE_MEDIUM = 17
    FONT_SIZE_SMALL = 15
    COLOR_WHITE = "#ffffff"
    COLOR_ORANGE = "#FF7033"
    COLOR_BLACK = "#262626"
    COLOR_LIGHT_ORANGE = "#FFBB99"

    def __init__(self, thumbnail, i2pdf_mode: Optional[bool] = False):
        super().__init__()
        self.setFixedSize(thumbnail.width() + 8, thumbnail.height() + 8)
        self.setStyleSheet("background: transparent;")

        self.thumbnail_view = ThumbnailView(thumbnail)
        self.thumbnail_view.setParent(self)

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.i2pdf_mode = i2pdf_mode
        if self.i2pdf_mode:
            self._initialize_labels()
            self._initialize_progress_bar()
        debug_placeholder = False
        if debug_placeholder:
            self.eta_label.setText("90 sec")
            self.speed_label.setText("4 files/s")
            self.page_count.setText("4/63")
            self.percent_count.setText("63%")

    def _initialize_labels(self):
        self.percent_count = self._create_label(self.FONT_SIZE_LARGE, self.COLOR_WHITE, 10, 120, demibold=True)
        self.page_count = self._create_label(self.FONT_SIZE_MEDIUM, self.COLOR_ORANGE, 6, 110, demibold=True)
        self.speed_label = self._create_label(self.FONT_SIZE_SMALL, self.COLOR_BLACK, 6, 100)
        self.eta_label = self._create_label(self.FONT_SIZE_SMALL, self.COLOR_BLACK, 6, 100)

    def _create_label(self, font_size: int, color: str, blur_radius: int, min_width: int, demibold: bool = False):
        label_font = QFont("Noto Sans KR")
        label_font.setWeight(QFont.Weight.DemiBold if demibold else QFont.Weight.Medium)
        label_font.setPixelSize(ptToPx(font_size))
        label = QLabel(self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"background: transparent; color: {color};")
        shadow_effect = QGraphicsDropShadowEffect(label)
        shadow_effect.setBlurRadius(blur_radius)
        shadow_effect.setOffset(4, 4)
        shadow_effect.setColor(QColor(0, 0, 0, 180))
        label.setGraphicsEffect(shadow_effect)
        label.setFont(label_font)
        label.setMinimumWidth(min_width)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        label.update()
        label.repaint()
        label.raise_()
        return label

    def _initialize_progress_bar(self):
        self.progress_bar = CustomProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.COLOR_LIGHT_ORANGE};
                
            }}
            QProgressBar::chunk {{
                background-color: {self.COLOR_ORANGE};
            }}
        """)
        self.progress_bar.setFixedSize(100, 6)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()

    def resizeEvent(self, event):
        self.thumbnail_view.setGeometry(self.rect())
        if self.i2pdf_mode:
            self._position_widgets()

    def _position_widgets(self):
        self._position_widget(self.percent_count, -30, self.percent_count.height())
        self._position_widget(self.progress_bar, 15, self.progress_bar.height())
        self._position_widget(self.page_count, 30, self.page_count.height())
        self._position_widget(self.speed_label, 53, self.speed_label.height())
        self._position_widget(self.eta_label, 75, self.eta_label.height())

    def _position_widget(self, widget, vertical_offset, widget_height):
        x = (self.width() - widget.width()) // 2
        y = (self.height() - widget_height) // 2 + vertical_offset
        widget.move(x, y)


class BookWidget(QWidget):
    clicked = Signal(str)  # Signal to pass book ID on click
    by_modified_time_signal = Signal(Path, bool)
    edit_title_signal = Signal(Path, str)

    def __init__(self, book_id, book_info, thumbnail, i2pdf_mode: Optional[bool] = False):
        super().__init__()
        self.setMaximumSize(154, 300)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.book_id = book_id
        self.is_selected = False
        self.is_processed = False
        self.is_processing = False
        self.is_complete = False
        self.i2pdfMode = i2pdf_mode
        self.by_modified_time = False
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(0.3)
        self.setup_ui(book_info, thumbnail)

    def setup_ui(self, book_info, thumbnail):
        # 외곽 스타일을 적용할 프레임 생성
        self.outer_frame = QFrame(self)
        self.outer_frame.setObjectName("outerFrame")  # 특정 스타일 적용을 위한 객체 이름 설정
        layout = QVBoxLayout(self.outer_frame)
        layout.setContentsMargins(0, 0, 0, 0)  # 레이아웃의 우측을 제외한 부분 마진 제거 (l,t,r,b)
        layout.setSpacing(0)  # 레이아웃의 간격 제거

        # 전체 레이아웃 적용
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.outer_frame)
        self.setLayout(main_layout)
        self.outer_frame.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self._setup_book_id(book_info, layout)
        self._setup_thumbnail(thumbnail, layout)
        self._setup_title(book_info, layout)
        self._setup_author(book_info, layout)

        self.setCursor(Qt.PointingHandCursor)  # 마우스 오버 시 커서 변경
        self.update_style()

    # 책 ID
    def _setup_book_id(self, book_info, layout):
        if 'file_info' in book_info:
            id_font = QFont("Noto Sans KR")
            id_font.setPixelSize(ptToPx(10.5))
            id_font.setWeight(QFont.Weight.Light)
            book_type = book_info['file_info']['format']
            book_id_label = QLabel(f"{self.book_id}({book_type})")
            book_id_label.setFont(id_font)
            book_id_label.setStyleSheet("background-color: transparent")
            book_id_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            book_id_label.setFixedHeight(17)
            layout.addWidget(book_id_label)
    # 썸네일
    def _setup_thumbnail(self, thumbnail, layout):
        self.thumbnail_container = ThumbnailContainer(thumbnail)
        layout.addWidget(self.thumbnail_container)
        layout.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Fixed))

    # 책 제목
    def _setup_title(self, book_info, layout):
        title_font = QFont("Noto Sans KR")
        title_font.setPixelSize(ptToPx(15))
        title_font.setWeight(QFont.Weight.ExtraBold)
        self.title_label = QLabel(book_info['title'])
        self.title_label.setWordWrap(True)
        self._apply_title_styles(title_font)
        layout.addWidget(self.title_label)

    # 기본 타이틀 스타일
    def _apply_title_styles(self, font):
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("background-color: transparent; padding-top: 2px; border: 0px;")
        self.title_label.setMaximumWidth(154)
        self.title_label.setMaximumHeight(60)
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.title_label.setMinimumHeight(10)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

    # 저자 정보
    def _setup_author(self, book_info, layout):
        if 'authors' in book_info and book_info['authors'] is not None:
            author_font = QFont("Noto Sans KR")
            author_font.setPixelSize(ptToPx(14.5))
            author_font.setWeight(QFont.Weight.Medium)
            authors = ", ".join([author['name'] for author in book_info['authors']])
            self.author_label = QLabel(f"{authors}")
            self.author_label.setFont(author_font)
            self.author_label.setStyleSheet("color: #707070; background-color: transparent; padding-left: 1px; padding-top: 0px;")
            self.author_label.setWordWrap(True)
            self.author_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.author_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            layout.addWidget(self.author_label)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.toggle_selection()
            self.clicked.emit(self.book_id)

    def toggle_selection(self):
        self.is_selected = not self.is_selected
        self.update_style()

    def set_processing(self, is_processing):
        if is_processing == 'Standby':
            self.thumbnail_container.progress_bar.show()
        elif is_processing:
            self.is_processing = is_processing
            self.thumbnail_container.progress_bar.stopInfinite()
        else:
            self.thumbnail_container.progress_bar.hide()

    # 프로그레스 바
    def set_progress(self, value):
        if 0 <= value <= 100:
            self.thumbnail_container.progress_bar.setValue(value)
            self.thumbnail_container.progress_bar.setRange(0, 100)
        else:
            self.thumbnail_container.progress_bar.startInfinite()  # 무한 로딩

    # 퍼센트 표시, 페이지 카운트
    def update_progress(self, current, total):
        self.totalPage = total
        self.thumbnail_container.percent_count.setText(f"{int(current / total * 100)}%")
        self.thumbnail_container.page_count.setText(f"{current}/{total}")

    def set_pagecount_complete(self):
        self.thumbnail_container.percent_count.setText(f"✓")
        self.thumbnail_container.percent_count.setStyleSheet("color: #FF5833; font-size: 50px;")
        self.thumbnail_container.page_count.setText(f"{self.totalPage}/{self.totalPage}")

    def update_style(self):
        opacity_effect_processing = QGraphicsOpacityEffect(self.thumbnail_container.thumbnail_view)
        opacity_effect_processing.setOpacity(0.6)
        # 디버그용 외곽선 표시
        debugFlag = False
        if debugFlag:
            self.setStyleSheet("""
                    background-color: white;
                    border: 1px solid #d0d0d0;
                    border-radius: 5px;
                """)
            #self.thumbnail_container.thumbnail_view.setGraphicsEffect(opacity_effect_processing)
        # 처리된 책 스타일 적용
        if self.is_processed:
            self.outer_frame.setStyleSheet("""
                    QFrame#outerFrame {
                        background-color: lightgray;
                        border-radius: 5px;
                    }
                """)
            self.title_label.setStyleSheet("color: #5E5E5E;")
            self.thumbnail_container.thumbnail_view.setGraphicsEffect(self.opacity_effect)
            if self.is_selected:
                self.outer_frame.setStyleSheet("""
                        QFrame#outerFrame {
                            background-color: #e0e0e0;
                            border: 2px solid #2196F3;
                            border-radius: 5px;
                        }
                    """)
        # 처리중
        elif self.is_processing:
            self.outer_frame.setStyleSheet("""
                    QFrame#outerFrame {
                        background-color: lightgray;
                        border-radius: 5px;
                        border: solid 1px #FF7033
                    }
                """)
            self.thumbnail_container.thumbnail_view.setGraphicsEffect(opacity_effect_processing)
        # 선택시 외곽 프레임에 스타일 적용
        elif self.is_selected:
            self.outer_frame.setStyleSheet("""
                    QFrame#outerFrame {
                        background-color: #e0e0e0;
                        border: 2px solid #2196F3;
                        border-radius: 5px;
                    }
                """)
        else:
            self.outer_frame.setStyleSheet("""
                    QFrame#outerFrame {
                        background-color: transparent;
                        border-radius: 5px;
                    }
                    QFrame#outerFrame:hover {
                        background-color: lightgray;
                        border: 1px solid gray;
                    }
                """)
            self.thumbnail_container.setGraphicsEffect(None)


class I2pdfBookWidget(BookWidget):
    def __int__(self, book_id, book_info, thumbnail, is_processed=False):
        super().__init__(book_id, book_info, thumbnail, is_processed)
        self.is_processing = False
        self.is_complete = False
        self.by_modified_time = False
        self.totalPage = 0

    def _setup_title(self, book_info, layout):
        title_font = QFont("Noto Sans KR")
        title_font.setPixelSize(ptToPx(15))
        title_font.setWeight(QFont.Weight.ExtraBold)
        self.title_label = CustomTextEdit(book_info['title'])
        self.title_label.setReadOnly(True)
        self.title_label.setEditMode(False)
        self.title_label.setWordWrapMode(QTextOption.WordWrap)
        super()._apply_title_styles(title_font)
        layout.addWidget(self.title_label)
        self.title_label.editingFinished.connect(self.finish_title_editing)

    def _setup_thumbnail(self, thumbnail, layout):
        self.thumbnail_container = ThumbnailContainer(thumbnail, i2pdf_mode=True)
        layout.addWidget(self.thumbnail_container)
        layout.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Fixed))

    def contextMenuEvent(self, event):
        if self.i2pdfMode:
            context_menu = QMenu(self)

            # 일반 항목
            actions = [
                ("Rename", "icons/character.cursor.ibeam.svg", self.start_title_editing),
                #("Edit Author", "icons/copy.svg", self.start_author_editing),
                #("Delete", "icons/delete.svg", self.on_delete)
            ]

            for text, icon_path, callback in actions:
                action = QAction(text, self)
                action.setIcon(QIcon(icon_path))
                action.triggered.connect(callback)
                context_menu.addAction(action)

            context_menu.addSeparator()

            # 정렬 옵션 그룹
            sort_group = QActionGroup(self)
            sort_group.setExclusive(True)

            # 정렬 옵션 생성
            sort_actions = [
                ("Sort by image name", "icons/textformat.svg", False),
                ("Sort by modified time", "icons/clock.svg", True)
            ]

            # 정렬 서브메뉴 생성
            #sort_submenu = QMenu("Sort", self)
            for text, icon_path, is_time_sort in sort_actions:
                action = QAction(text, self)
                action.setCheckable(True)
                action.setIcon(QIcon(icon_path))
                action.setChecked(self.by_modified_time == is_time_sort)
                sort_group.addAction(action)
                context_menu.addAction(action)

            # 메인 컨텍스트 메뉴에 정렬 서브메뉴 추가
            #context_menu.addMenu(context_menu)


            context_menu.setStyleSheet("""
                QMenu {
                    background-color: #EFE8E4;
                    color: black;
                    border: 1px solid #555555;
                    border-radius: 5px;
                }
                QMenu::icon {
                    padding-left: 10px;
                    padding-right: 0px;
                }
                QMenu::item {
                    padding: 8px 10px 8px 26px; /* top right bottom left */
                    background-color: transparent;
                }
                QMenu::item:selected {
                    background-color: #FFBB99;
                    color: black;
                }
                QMenu::item:checked {
                    background-color: #FF9966;
                    font-weight: bold;
                }
            """)

            def on_sort_action_triggered(action):
                self.by_modified_time = (action.text() == "Sort by modified time")
                self.by_modified_time_signal.emit(self.book_id, self.by_modified_time)
                '''                
                if action.text() == "Sort by modified time":
                    print("clicked")
                    clock_svg = "icons/clock.svg"
                    from PySide6.QtSvg import QSvgRenderer
                    svg_renderer = QSvgRenderer(clock_svg)
                    pixmap_size = svg_renderer.defaultSize()
                    pixmap = QPixmap(pixmap_size)
                    pixmap.fill(Qt.transparent)  # 배경을 투명하게 설정
                    painter = QPainter(pixmap)
                    svg_renderer.render(painter)
                    painter.end()
                    clock_label = QLabel(self)
                    clock_label.setPixmap(pixmap)
                    clock_label.setGeometry(10, 10, 100, 100)
                    clock_label.raise_()
                else:
                    clock_label = None
                '''

            sort_group.triggered.connect(on_sort_action_triggered)
            context_menu.exec(event.globalPos())

    def start_title_editing(self):
        self.title_label.setEditMode(True)
        self.title_label.setFocus(Qt.MouseFocusReason)
        self.title_label.selectAll()

    def finish_title_editing(self):
        self.title_label.setEditMode(False)
        new_title = self.title_label.toPlainText()
        self.edit_title_signal.emit(self.book_id, new_title)
        print(new_title)

    def update_thumbnail(self, new_thumbnail):
        self.thumbnail_container.thumbnail_view.set_pixmap(new_thumbnail)


class RowSeparationLineWidget(QWidget):
    def __init__(self, flow_layout, parent=None, margin_left=20, margin_right=20):
        super().__init__(parent)
        self.flow_layout = flow_layout
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.flow_layout.notifier.layoutChanged.connect(self.update)
        self.margin_left = margin_left
        self.margin_right = margin_right

    def paintEvent(self, event):
        painter = QPainter(self)
        pen = QPen(QColor("#9B9B9B"), 1, Qt.SolidLine)
        painter.setPen(pen)
        for y in self.flow_layout.getRowPositions()[1:]:  # 첫 번째 행 위의 선은 그리지 않음
            painter.drawLine(
                self.margin_left,
                y - self.flow_layout._v_spacing // 2,
                self.width() - self.margin_right,
                y - self.flow_layout._v_spacing // 2
            )
