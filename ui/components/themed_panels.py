# ui/components/themed_panels.py
# Стеклянные панели и контейнеры с поддержкой тем

from typing import List
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect

from core.models import Rhinestone, PaletteColor, RhinestoneSize
from .themed_buttons import ThemedColorDisplayButton, ThemedModernButton, ThemedSizeDisplay, ThemedModernToggle


class ThemedGlassCard(QFrame):
    """Базовая стеклянная карточка."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glassCard")
        self._setup_glass_effect()

    def _setup_glass_effect(self):
        """Настраивает эффект стекла (тень)."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)


class ThemedInfoPanel(ThemedGlassCard):
    """Информационная панель для отображения выделенных страз."""

    colorChangeRequested = pyqtSignal()
    sizeChangeRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("infoPanel")
        self._setup_ui()

    def _setup_ui(self):
        """Настройка интерфейса панели."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        # Счетчик выделения
        self.selection_count = QLabel("Выбрано: 0 страз")
        self.selection_count.setObjectName("selectionCount")
        layout.addWidget(self.selection_count)

        # Цвет
        self.color_label = QLabel("Цвет")
        self.color_label.setObjectName("sectionLabel")
        layout.addWidget(self.color_label)

        self.color_display = ThemedColorDisplayButton()
        self.color_display.clicked.connect(self.colorChangeRequested.emit)
        layout.addWidget(self.color_display)

        # Размер
        self.size_label = QLabel("Размер")
        self.size_label.setObjectName("sectionLabel")
        layout.addWidget(self.size_label)

        self.size_display = ThemedSizeDisplay()
        self.size_display.sizeChangeRequested.connect(self.sizeChangeRequested.emit)
        layout.addWidget(self.size_display)

        # Координаты
        self.coordinates = QLabel("Позиция: —")
        self.coordinates.setObjectName("coordinatesLabel")
        layout.addWidget(self.coordinates)

    def update_selection(self, selected_rhinestones: List[Rhinestone]):
        """Обновляет информацию о выделенных стразах."""
        count = len(selected_rhinestones)

        if count == 0:
            self.selection_count.setText("Ничего не выбрано")
            self.color_display.reset_style()
            self.size_display.set_size("—", 0.0)
            self.coordinates.setText("Позиция: —")

        elif count == 1:
            rhinestone = selected_rhinestones[0]
            self.selection_count.setText("Выбран 1 страз")

            # Цвет
            color_rgb = (rhinestone.color.color.r, rhinestone.color.color.g, rhinestone.color.color.b)
            self.color_display.set_color(rhinestone.color.name, color_rgb)

            # Размер
            self.size_display.set_size(rhinestone.size.name, rhinestone.size.diameter_mm)

            # Координаты
            x, y = int(rhinestone.position.x), int(rhinestone.position.y)
            self.coordinates.setText(f"Позиция: ({x}, {y})")

        else:
            self.selection_count.setText(f"Выбрано {count} страз")

            # Проверка на одинаковый цвет
            first_color = selected_rhinestones[0].color
            same_color = all(r.color.name == first_color.name for r in selected_rhinestones)
            if same_color:
                color_rgb = (first_color.color.r, first_color.color.g, first_color.color.b)
                self.color_display.set_color(first_color.name, color_rgb)
            else:
                self.color_display.set_color("", (0, 0, 0), mixed=True)

            # Проверка на одинаковый размер
            first_size = selected_rhinestones[0].size
            same_size = all(r.size.name == first_size.name for r in selected_rhinestones)
            if same_size:
                self.size_display.set_size(first_size.name, first_size.diameter_mm)
            else:
                self.size_display.set_size("Смешанные", 0.0, mixed=True)

            # Средние координаты
            avg_x = sum(r.position.x for r in selected_rhinestones) / count
            avg_y = sum(r.position.y for r in selected_rhinestones) / count
            self.coordinates.setText(f"Центр: ({int(avg_x)}, {int(avg_y)})")


class ThemedSelectionTools(ThemedGlassCard):
    """Панель инструментов выделения."""

    selectAll = pyqtSignal()
    clearSelection = pyqtSignal()
    selectByColor = pyqtSignal()
    selectBySize = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("selectionTools")
        self._setup_ui()

    def _setup_ui(self):
        """Настройка интерфейса панели."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        # Заголовок
        self.title = QLabel("Выделение")
        self.title.setObjectName("panelTitle")
        layout.addWidget(self.title)

        # Основные действия
        basic_layout = QHBoxLayout()
        basic_layout.setSpacing(10)

        self.select_all_btn = ThemedModernButton("Все")
        self.select_all_btn.clicked.connect(self.selectAll.emit)
        basic_layout.addWidget(self.select_all_btn)

        self.clear_btn = ThemedModernButton("Снять")
        self.clear_btn.clicked.connect(self.clearSelection.emit)
        basic_layout.addWidget(self.clear_btn)

        layout.addLayout(basic_layout)

        # Умные действия
        smart_layout = QHBoxLayout()
        smart_layout.setSpacing(10)

        self.select_color_btn = ThemedModernButton("По цвету")
        self.select_color_btn.clicked.connect(self.selectByColor.emit)
        self.select_color_btn.setToolTip("Выделить все стразы такого же цвета")
        smart_layout.addWidget(self.select_color_btn)

        self.select_size_btn = ThemedModernButton("По размеру")
        self.select_size_btn.clicked.connect(self.selectBySize.emit)
        self.select_size_btn.setToolTip("Выделить все стразы такого же размера")
        smart_layout.addWidget(self.select_size_btn)

        layout.addLayout(smart_layout)

    def update_selection_state(self, has_selection: bool):
        """Обновляет состояние кнопок в зависимости от наличия выделения."""
        self.select_color_btn.setEnabled(has_selection)
        self.select_size_btn.setEnabled(has_selection)


class ThemedAdditionMode(ThemedGlassCard):
    """Панель режима добавления страз."""

    additionModeToggled = pyqtSignal(bool)
    additionColorChangeRequested = pyqtSignal()
    additionSizeChangeRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("additionMode")
        self._setup_ui()

    def _setup_ui(self):
        """Настройка интерфейса панели."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        # Заголовок
        self.title = QLabel("Добавление")
        self.title.setObjectName("panelTitle")
        layout.addWidget(self.title)

        # Переключатель режима
        self.mode_toggle = ThemedModernToggle("Режим добавления")
        self.mode_toggle.stateChanged.connect(self._on_mode_toggled)
        layout.addWidget(self.mode_toggle)

        # Подсказка
        self.hint_label = QLabel("ЛКМ - добавить страз")
        self.hint_label.setObjectName("hintLabel")
        self.hint_label.setVisible(False)
        layout.addWidget(self.hint_label)

        # Цвет для новых страз
        self.color_label = QLabel("Цвет для новых страз")
        self.color_label.setObjectName("sectionLabel")
        layout.addWidget(self.color_label)

        self.addition_color_display = ThemedColorDisplayButton()
        self.addition_color_display.clicked.connect(self.additionColorChangeRequested.emit)
        layout.addWidget(self.addition_color_display)

        # Размер для новых страз
        self.size_label = QLabel("Размер для новых страз")
        self.size_label.setObjectName("sectionLabel")
        layout.addWidget(self.size_label)

        self.addition_size = ThemedSizeDisplay()
        self.addition_size.set_size("SS16", 4.0)
        self.addition_size.sizeChangeRequested.connect(self.additionSizeChangeRequested.emit)
        layout.addWidget(self.addition_size)

    def _on_mode_toggled(self, state):
        """Обработчик переключения режима добавления."""
        is_active = bool(state)
        self.hint_label.setVisible(is_active)

        # Устанавливаем свойство для QSS стилизации
        self.setProperty("additionActive", is_active)
        self.setStyleSheet("")  # Сброс для переприменения QSS

        self.additionModeToggled.emit(is_active)

    def is_addition_mode_active(self) -> bool:
        """Проверяет, активен ли режим добавления."""
        return self.mode_toggle.isChecked()

    def set_addition_color(self, color: PaletteColor):
        """Устанавливает цвет для добавляемых страз."""
        color_rgb = (color.color.r, color.color.g, color.color.b)
        self.addition_color_display.set_color(color.name, color_rgb)

    def set_addition_size(self, size: RhinestoneSize):
        """Устанавливает размер для добавляемых страз."""
        self.addition_size.set_size(size.name, size.diameter_mm)