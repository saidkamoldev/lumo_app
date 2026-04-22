# ui/dialogs/tex_dialog.py
# Диалог для создания текстовых макетов с live preview.
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QPlainTextEdit, QDialogButtonBox,
    QColorDialog, QWidget, QStyledItemDelegate, QButtonGroup, QStyle,
    QDoubleSpinBox
)
from PyQt5.QtGui import QColor, QFontDatabase, QFont
from PyQt5.QtCore import pyqtSignal, QTimer, QSize, Qt

from core.models import TextLayoutSettings, RGBColor
from core.services.text_service import TextImageService
from ..components.collapsible_box import CollapsibleBox

# --- Вспомогательная кнопка для выбора цвета ---
class ColorPickerButton(QPushButton):
    colorChanged = pyqtSignal(RGBColor)

    def __init__(self, color: RGBColor, parent=None):
        super().__init__(parent)
        self.setColor(color)
        self.clicked.connect(self.on_click)

    def setColor(self, color: RGBColor):
        self._color = color
        self.setText(f"#{color.r:02x}{color.g:02x}{color.b:02x}".upper())
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color.to_rgb_str()};
                color: {'#FFF' if color.r + color.g + color.b < 384 else '#000'};
                border: 1px solid #888;
                border-radius: 4px;
                padding: 5px;
                font-weight: bold;
            }}
        """)

    def on_click(self):
        dialog = QColorDialog(QColor(self._color.r, self._color.g, self._color.b), self)
        if dialog.exec_():
            c = dialog.selectedColor()
            new_color = RGBColor(c.red(), c.green(), c.blue())
            self.setColor(new_color)
            self.colorChanged.emit(new_color)


# --- Делегат для отрисовки шрифтов в QComboBox ---
class FontDelegate(QStyledItemDelegate):
    def __init__(self, text_service, parent=None):
        super().__init__(parent)
        self.text_service = text_service
        self._font_cache = {}  # Kesh qo'shamiz

    def paint(self, painter, option, index):
        font_name = index.data()

        # Keshdan olish yoki yuklash
        if font_name not in self._font_cache:
            font_path = self.text_service.get_font_path(font_name)
            if font_path:
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        self._font_cache[font_name] = QFont(families[0], 12)
                    else:
                        self._font_cache[font_name] = QFont()
                else:
                    self._font_cache[font_name] = QFont()
            else:
                self._font_cache[font_name] = QFont(font_name, 12)

        qt_font = self._font_cache[font_name]

        painter.save()
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())

        painter.setFont(qt_font)
        painter.drawText(
            option.rect.adjusted(5, 0, 0, 0),
            Qt.AlignVCenter | Qt.AlignLeft,
            font_name
        )
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(200, 30)


# --- Основной диалог ---
class TextCreatorDialog(QDialog):
    settings_changed = pyqtSignal(TextLayoutSettings)
    creation_confirmed = pyqtSignal(TextLayoutSettings)
    cancelled = pyqtSignal()

    def __init__(self, text_service: TextImageService, parent=None):
        super().__init__(parent)
        self.text_service = text_service
        self.settings = TextLayoutSettings()

        self.setWindowTitle("Создание текста")
        self.setMinimumWidth(380)
        self.setObjectName("textCreatorDialog")

        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._emit_settings_changed)

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.text_edit = QPlainTextEdit("Lumo")
        self.text_edit.setObjectName("textInputArea")
        main_layout.addWidget(self.text_edit, 1)

        grid = QGridLayout()
        grid.addWidget(QLabel("Шрифт:"), 0, 0)
        self.font_combo = QComboBox()
        self.font_combo.addItems(self.text_service.get_available_fonts())
        self.font_delegate = FontDelegate(self.text_service, self)
        self.font_combo.setItemDelegate(self.font_delegate)
        grid.addWidget(self.font_combo, 0, 1)

        grid.addWidget(QLabel("Размер:"), 1, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 1000)
        self.font_size_spin.setValue(100)
        grid.addWidget(self.font_size_spin, 1, 1)

        grid.addWidget(QLabel("Цвет:"), 2, 0)
        self.color_picker_btn = ColorPickerButton(self.settings.text_color)
        grid.addWidget(self.color_picker_btn, 2, 1)
        main_layout.addLayout(grid)

        advanced_box = CollapsibleBox("Дополнительно")
        adv_content = QWidget()
        adv_layout = QGridLayout(adv_content)
        adv_layout.addWidget(QLabel("Выравнивание:"), 0, 0)
        align_layout = QHBoxLayout()
        self.align_group = QButtonGroup(self)
        self.btn_align_left = QPushButton("По левому")
        self.btn_align_center = QPushButton("По центру")
        self.btn_align_right = QPushButton("По правому")
        for i, btn in enumerate([self.btn_align_left, self.btn_align_center, self.btn_align_right]):
            btn.setCheckable(True)
            btn.setObjectName("alignButton")
            align_layout.addWidget(btn)
            self.align_group.addButton(btn, i)
        self.btn_align_center.setChecked(True)
        adv_layout.addLayout(align_layout, 0, 1)
        adv_layout.addWidget(QLabel("Межбукв. интервал:"), 1, 0)
        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(-20, 50)
        adv_layout.addWidget(self.spacing_spin, 1, 1)
        advanced_box.setContent(adv_content)
        main_layout.addWidget(advanced_box)

        # --- НАЧАЛО ИЗМЕНЕНИЙ В БЛОКЕ "РАЗМЕР ХОЛСТА" ---
        canvas_box = CollapsibleBox("Размер холста")
        canvas_content = QWidget()
        canvas_layout = QGridLayout(canvas_content)

        # 1. Меняем подписи с px на мм
        canvas_layout.addWidget(QLabel("Ширина (мм):"), 0, 0)
        # 2. Заменяем QSpinBox на QDoubleSpinBox для дробных значений
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(10.0, 2000.0)
        self.width_spin.setValue(self.settings.canvas_width_mm)  # Используем значение из модели
        canvas_layout.addWidget(self.width_spin, 0, 1)

        canvas_layout.addWidget(QLabel("Высота (мм):"), 1, 0)
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(10.0, 2000.0)
        self.height_spin.setValue(self.settings.canvas_height_mm)  # Используем значение из модели
        canvas_layout.addWidget(self.height_spin, 1, 1)

        # 3. Добавляем новое поле для DPI
        canvas_layout.addWidget(QLabel("DPI:"), 2, 0)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(self.settings.dpi)
        canvas_layout.addWidget(self.dpi_spin, 2, 1)

        canvas_box.setContent(canvas_content)
        main_layout.addWidget(canvas_box)
        # --- КОНЕЦ ИЗМЕНЕНИЙ ---

        main_layout.addStretch()
        self.button_box = QDialogButtonBox()
        self.add_btn = self.button_box.addButton("Добавить", QDialogButtonBox.AcceptRole)
        self.cancel_btn = self.button_box.addButton("Отмена", QDialogButtonBox.RejectRole)
        self.add_btn.setObjectName("acceptButton")
        self.cancel_btn.setObjectName("cancelButton")
        main_layout.addWidget(self.button_box)

    def _connect_signals(self):
        self.text_edit.textChanged.connect(self._schedule_update)
        self.font_combo.currentTextChanged.connect(self._schedule_update)
        self.font_size_spin.valueChanged.connect(self._schedule_update)
        self.color_picker_btn.colorChanged.connect(self._schedule_update)
        self.align_group.buttonClicked.connect(self._schedule_update)
        self.spacing_spin.valueChanged.connect(self._schedule_update)
        self.width_spin.valueChanged.connect(self._schedule_update)
        self.height_spin.valueChanged.connect(self._schedule_update)
        self.dpi_spin.valueChanged.connect(self._schedule_update)  # <-- НОВОЕ СОЕДИНЕНИЕ

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _schedule_update(self):
        self._update_timer.start(100)

    def _emit_settings_changed(self):
        self._update_model_from_ui()
        self.settings_changed.emit(self.settings)

    def _update_model_from_ui(self):
        self.settings.text = self.text_edit.toPlainText()
        self.settings.font_family = self.font_combo.currentText()
        self.settings.font_size = self.font_size_spin.value()
        self.settings.text_color = self.color_picker_btn._color

        checked_id = self.align_group.checkedId()
        if checked_id == 0:
            self.settings.horizontal_align = 'left'
        elif checked_id == 2:
            self.settings.horizontal_align = 'right'
        else:
            self.settings.horizontal_align = 'center'

        self.settings.letter_spacing = self.spacing_spin.value()

        self.settings.canvas_width_mm = self.width_spin.value()
        self.settings.canvas_height_mm = self.height_spin.value()
        self.settings.dpi = self.dpi_spin.value()

    def accept(self):
        self._update_model_from_ui()
        self.creation_confirmed.emit(self.settings)
        super().accept()

    def reject(self):
        self.cancelled.emit()
        super().reject()