# ui/dialogs/size_selector.py
from typing import List, Optional, Set
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLineEdit, QScrollArea, QWidget, QLabel, QGraphicsDropShadowEffect, QPushButton
)
from core.models import RhinestoneSize

class MiniButton(QPushButton):
    """Стилизованная мини-кнопка для быстрых действий."""
    def __init__(self, text: str, tooltip: str, parent=None):
        super().__init__(text, parent)
        self.setToolTip(tooltip)
        self.setObjectName("miniButton")
        self.setFixedSize(32, 32)

class SizeItem(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, size: RhinestoneSize, theme_manager=None, parent=None):
        super().__init__(parent)
        self.size = size
        self.theme_manager = theme_manager
        self.setObjectName("sizeItem")
        self.setFixedHeight(45)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(12)

        self.circle_preview = QLabel()
        self.circle_preview.setObjectName("sizeCirclePreview")

        # 1. Вычисляем динамический размер и радиус
        size_mm = self.size.diameter_mm
        circle_dia = int(12 + (max(0, min(size_mm - 1.5, 3.5)) / 3.5) * 16)
        radius = int(circle_dia / 2)

        # 2. Устанавливаем размер виджета
        self.circle_preview.setFixedSize(circle_dia, circle_dia)

        # 3. Определяем цвета в зависимости от темы
        # ИСПРАВЛЕНИЕ: Заменен вызов несуществующего метода is_dark_theme() на is_dark()
        is_dark = self.theme_manager.is_dark() if self.theme_manager else True
        bg_color = "#888" if is_dark else "#ccc"
        border_color = "#AAA" if is_dark else "#aaa"

        # 4. Применяем стили напрямую с динамическим радиусом
        self.circle_preview.setStyleSheet(f"""
            QLabel#sizeCirclePreview {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {radius}px;
            }}
        """)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        self.name_label = QLabel(self.size.name)
        self.name_label.setObjectName("sizeNameLabel")
        self.diameter_label = QLabel(f"{self.size.diameter_mm} мм")
        self.diameter_label.setObjectName("sizeDiameterLabel")
        text_layout.addWidget(self.name_label)
        text_layout.addWidget(self.diameter_label)

        layout.addWidget(self.circle_preview)
        layout.addLayout(text_layout, 1)

    def set_selected(self, selected: bool):
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.size.name)
        super().mousePressEvent(event)


class SizeSelectorPopup(QFrame):
    selectionChanged = pyqtSignal(list)
    closed = pyqtSignal()
    sizeSelected = pyqtSignal(RhinestoneSize)

    def __init__(self, available_sizes: List[RhinestoneSize], theme_manager=None, single_selection_mode: bool = False, parent=None):
        super().__init__(parent)
        self.available_sizes = sorted(available_sizes, key=lambda s: s.diameter_mm)
        self.theme_manager = theme_manager
        self.selected_sizes: Set[str] = set()
        self.single_selection_mode = single_selection_mode

        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("sizeSelectorPopup")

        shadow = QGraphicsDropShadowEffect(blurRadius=20, xOffset=0, yOffset=4, color=QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

        main_container = QFrame(self)
        main_container.setObjectName("mainContainer")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(main_container)

        self._setup_ui(main_container)

    def _setup_ui(self, container: QFrame):
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # --- Top Layout ---
        self.top_widget = QWidget()
        top_layout = QHBoxLayout(self.top_widget)
        top_layout.setContentsMargins(0,0,0,0)
        top_layout.setSpacing(4)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Поиск...")

        self.btn_select_all = MiniButton("➕", "Выбрать все")
        self.btn_clear_all = MiniButton("➖", "Снять выбор")

        top_layout.addWidget(self.search_input, 1)
        top_layout.addWidget(self.btn_select_all)
        top_layout.addWidget(self.btn_clear_all)
        layout.addWidget(self.top_widget)

        # --- Scroll Area ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        if self.single_selection_mode:
            scroll_area.setMaximumHeight(280)
        else:
            scroll_area.setMaximumHeight(400)

        scroll_area.setObjectName("sizeScrollArea")

        scroll_container = QWidget()
        self.sizes_layout = QVBoxLayout(scroll_container)
        self.sizes_layout.setContentsMargins(0, 5, 0, 5)
        self.sizes_layout.setSpacing(3)
        scroll_area.setWidget(scroll_container)
        layout.addWidget(scroll_area, 1)

        # --- Info Label ---
        self.info_label = QLabel("Выбрано: 0 размеров")
        self.info_label.setObjectName("infoLabel")
        layout.addWidget(self.info_label)

        self._populate_sizes()

        # --- Mode-specific setup ---
        if self.single_selection_mode:
            self.top_widget.hide()
            self.info_label.hide()
            container.layout().setSpacing(4)
        else: # Multi-selection mode
            self.search_input.textChanged.connect(self._filter_sizes)
            self.btn_select_all.clicked.connect(self._select_all)
            self.btn_clear_all.clicked.connect(self._clear_all)

    def _populate_sizes(self):
        self.size_items = []
        while self.sizes_layout.count():
            item_widget = self.sizes_layout.takeAt(0).widget()
            if item_widget:
                item_widget.deleteLater()

        for size in self.available_sizes:
            item = SizeItem(size, theme_manager=self.theme_manager)
            item.clicked.connect(self._on_size_clicked)
            item.set_selected(size.name in self.selected_sizes)
            self.sizes_layout.addWidget(item)
            self.size_items.append(item)
        self.sizes_layout.addStretch(1)

    def _select_all(self):
        self.selected_sizes = {item.size.name for item in self.size_items if item.isVisible()}
        self._update_selection_state()

    def _clear_all(self):
        self.selected_sizes.clear()
        self._update_selection_state()

    def _filter_sizes(self, text: str):
        text_lower = text.lower()
        for item in self.size_items:
            item.setVisible(text_lower in item.size.name.lower() or text_lower in str(item.size.diameter_mm))

    def _on_size_clicked(self, size_name: str):
        if self.single_selection_mode:
            for size in self.available_sizes:
                if size.name == size_name:
                    self.sizeSelected.emit(size)
                    self.close()
                    return
        else:
            if size_name in self.selected_sizes:
                self.selected_sizes.remove(size_name)
            else:
                self.selected_sizes.add(size_name)
            self._update_selection_state()

    def _update_selection_state(self):
        for item in self.size_items:
            item.set_selected(item.size.name in self.selected_sizes)
        count = len(self.selected_sizes)
        self.info_label.setText(f"Выбрано: {count} размеров")
        self.selectionChanged.emit(list(self.selected_sizes))

    def set_selected_sizes(self, size_names: List[str]):
        if self.single_selection_mode: return
        self.selected_sizes = set(size_names)
        self._update_selection_state()

    def show_at(self, pos: QPoint):
        self.move(pos)
        self.show()