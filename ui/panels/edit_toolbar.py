# ui/panels/edit_toolbar.py
# Панель инструментов для режима редактирования.

from typing import List
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from core.models import Rhinestone, PaletteColor, RhinestoneSize
from ui.components.themed_panels import ThemedInfoPanel, ThemedSelectionTools, ThemedAdditionMode


class EditToolbar(QWidget):
    """
    Главная панель редактирования, объединяющая все компоненты:
    информацию о выделении, инструменты и режим добавления.
    """

    # Сигналы для изменения свойств выделенных стразов
    changeSelectedColor = pyqtSignal()
    changeSelectedSize = pyqtSignal()

    # Сигналы для инструментов выделения
    selectAll = pyqtSignal()
    clearSelection = pyqtSignal()
    selectByColor = pyqtSignal()
    selectBySize = pyqtSignal()

    # Сигналы для режима добавления
    additionModeToggled = pyqtSignal(bool)
    additionColorChangeRequested = pyqtSignal()
    additionSizeChangeRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("editToolbar")
        self.setFixedWidth(420)

        self._setup_ui()
        self._connect_signals()

        # Псевдонимы для удобного доступа из презентера
        self.color_change_button = self.info_panel.color_display
        self.size_change_button = self.info_panel.size_display
        self.addition_color_button = self.addition_mode.addition_color_display
        self.addition_size_button = self.addition_mode.addition_size

        self.update_selection([])

    def _setup_ui(self):
        """Настройка интерфейса панели."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 20, 16, 20)
        main_layout.setSpacing(20)

        self.info_panel = ThemedInfoPanel()
        self.addition_mode = ThemedAdditionMode()
        self.selection_tools = ThemedSelectionTools()

        main_layout.addWidget(self.info_panel)
        main_layout.addWidget(self.addition_mode)
        main_layout.addWidget(self.selection_tools)
        main_layout.addStretch()

    def _connect_signals(self):
        """Подключение сигналов от дочерних виджетов к сигналам этой панели."""
        self.info_panel.colorChangeRequested.connect(self.changeSelectedColor)
        self.info_panel.sizeChangeRequested.connect(self.changeSelectedSize)
        self.selection_tools.selectAll.connect(self.selectAll)
        self.selection_tools.clearSelection.connect(self.clearSelection)
        self.selection_tools.selectByColor.connect(self.selectByColor)
        self.selection_tools.selectBySize.connect(self.selectBySize)
        self.addition_mode.additionModeToggled.connect(self.additionModeToggled)
        self.addition_mode.additionColorChangeRequested.connect(self.additionColorChangeRequested)
        self.addition_mode.additionSizeChangeRequested.connect(self.additionSizeChangeRequested)

    def update_selection(self, selected_rhinestones: List[Rhinestone]):
        """Обновляет информацию о выделенных стразах."""
        has_selection = bool(selected_rhinestones)
        self.info_panel.update_selection(selected_rhinestones)
        self.selection_tools.update_selection_state(has_selection)

    def set_addition_color(self, color: PaletteColor):
        """Устанавливает цвет для добавляемых страз."""
        self.addition_mode.set_addition_color(color)

    def set_addition_size(self, size: RhinestoneSize):
        """Устанавливает размер для добавляемых страз."""
        self.addition_mode.set_addition_size(size)

    def is_addition_mode_active(self) -> bool:
        """Проверяет, активен ли режим добавления."""
        return self.addition_mode.is_addition_mode_active()