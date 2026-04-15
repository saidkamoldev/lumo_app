# ui/dialogs/color_selector.py
# Всплывающий селектор цветов, стилизуемый через QSS. (ФИНАЛЬНАЯ ВЕРСИЯ)

from typing import List, Optional, Set
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QEvent, QRect
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QScrollArea,
    QFrame, QLabel, QPushButton, QDialog, QColorDialog, QMessageBox,
    QGraphicsDropShadowEffect, QDialogButtonBox, QFormLayout, QApplication
)
from PyQt5.QtGui import QColor, QCloseEvent

# Относительный импорт компонента кнопки из соседней папки
from ..components.themed_buttons import ThemedColorDisplayButton
from core.models import PaletteColor, RGBColor


class ColorEditorDialog(QDialog):
    """Диалог для добавления или редактирования цвета палитры."""

    def __init__(self, title: str, existing_names: List[str], color: Optional[PaletteColor] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setObjectName("colorEditorDialog")
        self.setMinimumWidth(380)

        self.existing_names = [name.lower() for name in existing_names]
        self.original_name = ""
        self.selected_color: Optional[QColor] = None

        # --- Виджеты ---
        self.name_input = QLineEdit()
        self.name_input.setObjectName("colorNameInput")
        self.name_input.setPlaceholderText("Например, Crystal AB")

        # Используем новую кнопку для отображения и выбора цвета
        self.color_display_button = ThemedColorDisplayButton()
        self.color_display_button.clicked.connect(self.pick_color)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("Сохранить")
        self.button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        self.button_box.accepted.connect(self.validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

        # --- Макет ---
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setSpacing(15)

        form_layout.addRow("Название:", self.name_input)
        form_layout.addRow("Цвет:", self.color_display_button)

        layout.addLayout(form_layout)
        layout.addWidget(self.button_box)

        # --- Начальное состояние и сигналы ---
        self.name_input.textChanged.connect(self.check_form_validity)
        self.name_input.textChanged.connect(self.update_color_display)

        if color:
            self.original_name = color.name
            self.name_input.setText(color.name)
            self.selected_color = color.color.to_qcolor()
            self.update_color_display()
        else:
            self.color_display_button.reset_style()

    def pick_color(self):
        """Открывает стандартный диалог выбора цвета."""
        initial_color = self.selected_color if self.selected_color else Qt.white
        new_color = QColorDialog.getColor(initial_color, self, "Выберите цвет")
        if new_color.isValid():
            self.selected_color = new_color
            self.update_color_display()

    def update_color_display(self):
        """Обновляет текст и цвет кнопки на основе текущих данных."""
        if not self.selected_color:
            self.color_display_button.reset_style()
            return

        current_name = self.name_input.text().strip()
        display_name = current_name if current_name else "Выбранный цвет"

        color_rgb = (self.selected_color.red(), self.selected_color.green(), self.selected_color.blue())
        self.color_display_button.set_color(display_name, color_rgb)
        self.check_form_validity()

    def check_form_validity(self):
        """Проверяет, заполнены ли все поля для активации кнопки сохранения."""
        name_valid = bool(self.name_input.text().strip())
        color_valid = self.selected_color is not None
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(name_valid and color_valid)

    def validate_and_accept(self):
        """Проверяет данные перед закрытием диалога."""
        name = self.name_input.text().strip()
        lower_name = name.lower()

        if lower_name in self.existing_names and lower_name != self.original_name.lower():
            QMessageBox.warning(self, "Ошибка", f"Цвет с именем '{name}' уже существует.")
            return
        self.accept()

    def get_color_data(self) -> Optional[PaletteColor]:
        """Возвращает данные о цвете, если диалог был подтвержден."""
        if self.result() == QDialog.Accepted:
            name = self.name_input.text().strip()
            color = RGBColor(r=self.selected_color.red(), g=self.selected_color.green(), b=self.selected_color.blue())
            return PaletteColor(name=name, color=color)
        return None


class MiniButton(QPushButton):
    def __init__(self, text: str, tooltip: str, parent=None):
        super().__init__(text, parent)
        self.setToolTip(tooltip)
        self.setObjectName("miniButton")
        self.setFixedSize(32, 32)


class ColorItem(QFrame):
    clicked = pyqtSignal(str)
    editClicked = pyqtSignal(str)

    def __init__(self, palette_color: PaletteColor, parent=None):
        super().__init__(parent)
        self.palette_color = palette_color
        self.setObjectName("colorItem")
        self.setMinimumHeight(38)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        self.color_circle = QLabel()
        self.color_circle.setObjectName("colorCircle")
        self.color_circle.setFixedSize(16, 16)
        self.color_circle.setStyleSheet(f"background-color: {palette_color.color.to_rgb_str()};")

        self.name_label = QLabel(self.palette_color.name)
        self.name_label.setObjectName("colorNameLabel")
        self.name_label.setWordWrap(True)

        self.edit_button = QPushButton("...")
        self.edit_button.setObjectName("miniEditButton")
        self.edit_button.setFixedSize(32, 32)
        self.edit_button.setToolTip("Редактировать цвет")
        self.edit_button.clicked.connect(lambda: self.editClicked.emit(self.palette_color.name))

        layout.addWidget(self.color_circle)
        layout.addWidget(self.name_label, 1)
        layout.addWidget(self.edit_button)

    def set_selected(self, selected: bool):
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.edit_button.geometry().contains(event.pos()):
                self.clicked.emit(self.palette_color.name)
        super().mousePressEvent(event)


class ColorSelectorPopup(QFrame):
    selectionChanged = pyqtSignal(list)
    paletteChanged = pyqtSignal()
    closed = pyqtSignal()
    colorSelected = pyqtSignal(PaletteColor)

    def __init__(self, palette: List[PaletteColor], palette_service, single_selection_mode: bool = False, parent=None):
        super().__init__(parent)
        self.palette = palette[:]
        self.palette_service = palette_service
        self.selected_colors: Set[str] = set()
        self.single_selection_mode = single_selection_mode

        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("colorSelectorPopup")

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

        # --- Top Layout (Search and selection) ---
        self.top_widget = QWidget()
        top_layout = QHBoxLayout(self.top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.textChanged.connect(self._filter_colors)

        self.btn_select_all = MiniButton("➕", "Выбрать все")
        self.btn_clear_all = MiniButton("➖", "Снять выбор")

        top_layout.addWidget(self.search_input, 1)
        top_layout.addWidget(self.btn_select_all)
        top_layout.addWidget(self.btn_clear_all)
        layout.addWidget(self.top_widget)

        # --- Scroll Area ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("colorScrollArea")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        scroll_container = QWidget()
        self.colors_layout = QVBoxLayout(scroll_container)
        self.colors_layout.setContentsMargins(0, 5, 0, 5)
        self.colors_layout.setSpacing(2)
        scroll_area.setWidget(scroll_container)
        layout.addWidget(scroll_area, 1)

        # --- Controls Layout (Add/Delete) ---
        self.controls_widget = QWidget()
        controls_layout = QHBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)
        self.btn_add_color = QPushButton("➕ Добавить")
        self.btn_add_color.setObjectName("addButton")
        self.btn_delete_color = QPushButton("🗑️ Удалить")
        self.btn_delete_color.setObjectName("deleteButton")
        self.btn_delete_color.setEnabled(False)
        controls_layout.addWidget(self.btn_add_color)
        controls_layout.addWidget(self.btn_delete_color)
        layout.addWidget(self.controls_widget)

        # --- Info Label ---
        self.info_label = QLabel("Выбрано: 0 цветов")
        self.info_label.setObjectName("infoLabel")
        layout.addWidget(self.info_label)

        self._populate_colors()

        # --- Mode-specific setup ---
        if self.single_selection_mode:
            self.btn_select_all.hide()
            self.btn_clear_all.hide()
            self.controls_widget.hide()
            self.info_label.hide()
            container.layout().setSpacing(4)
            scroll_area.setMaximumHeight(280)
        else:
            self.btn_select_all.clicked.connect(self._select_all)
            self.btn_clear_all.clicked.connect(self._clear_all)
            self.btn_add_color.clicked.connect(self._add_new_color)
            self.btn_delete_color.clicked.connect(self._delete_selected_colors)
            scroll_area.setMaximumHeight(400)

    def eventFilter(self, source, event):
        # Если виджет видим и произошел клик мыши
        if self.isVisible() and event.type() == QEvent.MouseButtonPress:
            # Получаем геометрию виджета в глобальных координатах
            popup_rect = QRect(self.mapToGlobal(QPoint(0, 0)), self.size())
            # Если клик был вне этой геометрии, закрываем виджет
            if not popup_rect.contains(event.globalPos()):
                self.close()
                return True # Сообщаем, что мы обработали событие

        # Передаем все остальные события для стандартной обработки
        return super().eventFilter(source, event)

    def closeEvent(self, a0: QCloseEvent) -> None:
        QApplication.instance().removeEventFilter(self)
        self.closed.emit()
        super().closeEvent(a0)

    def _populate_colors(self):
        self.color_items = []
        while self.colors_layout.count():
            item_widget = self.colors_layout.takeAt(0).widget()
            if item_widget: item_widget.deleteLater()

        for color in sorted(self.palette, key=lambda c: c.name):
            item = ColorItem(color)
            item.clicked.connect(self._on_color_clicked)
            item.editClicked.connect(self._edit_color)
            item.set_selected(color.name in self.selected_colors)

            if self.single_selection_mode:
                item.edit_button.hide()

            self.colors_layout.addWidget(item)
            self.color_items.append(item)
        self.colors_layout.addStretch(1)

    def _edit_color(self, color_name: str):
        if self.single_selection_mode: return

        target_color_obj = next((c for c in self.palette if c.name == color_name), None)
        if not target_color_obj: return

        existing_names = [c.name for c in self.palette]

        dialog = ColorEditorDialog(
            title=f"Изменить цвет '{color_name}'",
            existing_names=existing_names,
            color=target_color_obj,
            parent=self.window()
        )

        if dialog.exec_() == QDialog.Accepted:
            new_color_data = dialog.get_color_data()
            if new_color_data:
                target_index = next((i for i, c in enumerate(self.palette) if c.name == color_name), -1)
                self.palette[target_index] = new_color_data

                if color_name in self.selected_colors and color_name != new_color_data.name:
                    self.selected_colors.remove(color_name)
                    self.selected_colors.add(new_color_data.name)

                self.palette_service.save_palette(self.palette)
                self.paletteChanged.emit()
                self._populate_colors()
                self._update_selection_state()

    def _on_color_clicked(self, color_name: str):
        if self.single_selection_mode:
            for color in self.palette:
                if color.name == color_name:
                    self.colorSelected.emit(color)
                    self.close()
                    return
        else:
            if color_name in self.selected_colors:
                self.selected_colors.remove(color_name)
            else:
                self.selected_colors.add(color_name)
            self._update_selection_state()

    def _update_selection_state(self):
        for item in self.color_items:
            item.set_selected(item.palette_color.name in self.selected_colors)
        count = len(self.selected_colors)
        self.info_label.setText(f"Выбрано: {count} цветов")
        self.btn_delete_color.setEnabled(count > 0)
        self.selectionChanged.emit(list(self.selected_colors))

    def _select_all(self):
        self.selected_colors = {item.palette_color.name for item in self.color_items if item.isVisible()}
        self._update_selection_state()

    def _clear_all(self):
        self.selected_colors.clear()
        self._update_selection_state()

    def _filter_colors(self, text: str):
        for item in self.color_items:
            item.setVisible(text.lower() in item.palette_color.name.lower())

    def _add_new_color(self):
        existing_names = [c.name for c in self.palette]
        dialog = ColorEditorDialog(
            title="Добавить новый цвет",
            existing_names=existing_names,
            parent=self.window()
        )

        if dialog.exec_() == QDialog.Accepted:
            new_color_data = dialog.get_color_data()
            if new_color_data:
                self.palette.append(new_color_data)
                self.palette_service.save_palette(self.palette)
                self.paletteChanged.emit()
                self._populate_colors()
                self.selected_colors.add(new_color_data.name)
                self._update_selection_state()

    def _delete_selected_colors(self):
        if not self.selected_colors: return
        reply = QMessageBox.question(
            self,
            "Удаление",
            f"Вы уверены, что хотите удалить {len(self.selected_colors)} выбранных цветов из палитры?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.palette = [c for c in self.palette if c.name not in self.selected_colors]
            self.selected_colors.clear()
            self.palette_service.save_palette(self.palette)
            self.paletteChanged.emit()
            self._populate_colors()
            self._update_selection_state()

    def set_selected_colors(self, color_names: List[str]):
        if self.single_selection_mode: return
        self.selected_colors = set(color_names)
        self._update_selection_state()

    def show_at(self, pos: QPoint):
        self.move(pos)
        self.show()
        QApplication.instance().installEventFilter(self)