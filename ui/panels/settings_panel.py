# ui/panels/settings_panel.py
# Исправленная версия панели настроек с real-time обновлением границ холста

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QFormLayout, QPushButton,
    QDoubleSpinBox, QSpinBox, QCheckBox, QGridLayout
)

from core.models import ProcessingSettings, OutputSettings, Project
from ..components.collapsible_box import CollapsibleBox
from .report_panel import ReportPanel


class SettingsPanel(QFrame):
    """
    Правая панель с настройками. Теперь она также содержит и управляет отчетом.
    ИСПРАВЛЕНИЕ: Добавлены сигналы для real-time обновления границ холста.
    """
    settingsChanged = pyqtSignal(ProcessingSettings)
    processClicked = pyqtSignal()
    mirrorClicked = pyqtSignal()

    # НОВЫЕ СИГНАЛЫ для real-time обновления границ холста
    canvasSizeChanged = pyqtSignal(OutputSettings)  # Новый сигнал

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rightInspector")
        self.setFixedWidth(380)

        self._create_widgets()
        self._setup_layout()
        self._connect_signals()

    def _create_widgets(self):
        """Создает все виджеты ввода."""
        self.spin_out_width = QSpinBox()
        self.spin_out_width.setRange(10, 2000)
        self.spin_out_width.setValue(300)
        self.spin_out_width.setSuffix(" мм")

        self.spin_out_height = QSpinBox()
        self.spin_out_height.setRange(10, 2000)
        self.spin_out_height.setValue(300)
        self.spin_out_height.setSuffix(" мм")

        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(72, 600)
        self.spin_dpi.setValue(150)
        self.spin_dpi.setSuffix(" DPI")

        self.spin_spacing = QDoubleSpinBox()
        self.spin_spacing.setRange(0.1, 50.0)
        self.spin_spacing.setValue(1.5)
        self.spin_spacing.setSingleStep(0.1)

        self.spin_base_dot_size = QDoubleSpinBox()
        self.spin_base_dot_size.setRange(0.1, 10.0)
        self.spin_base_dot_size.setValue(2.0)
        self.spin_base_dot_size.setSingleStep(0.1)

        self.spin_contrast = QDoubleSpinBox()
        self.spin_contrast.setRange(-5.0, 5.0)
        self.spin_contrast.setValue(1.0)
        self.spin_contrast.setSingleStep(0.1)

        self.check_mirror = QCheckBox("Отразить зеркально")
        self.check_fill_inner = QCheckBox("Заполнить внутренние области")
        self.check_honeycomb = QCheckBox("Сетка в виде Сот")

        self.report_panel = ReportPanel()

    def _setup_layout(self):
        """Собирает компоновку панели."""
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        output_box = CollapsibleBox("Параметры вывода")
        output_box.setContent(self._create_output_settings_page())

        processing_box = CollapsibleBox("Параметры обработки")
        processing_box.setContent(self._create_processing_settings_page())

        self.report_box = CollapsibleBox("Отчет по материалам")
        self.report_box.setContent(self.report_panel)
        self.report_box.hide()

        self.btn_process = QPushButton("Сгенерировать")
        self.btn_process.setObjectName("ProcessButton")

        # Добавляем виджеты по строкам
        main_layout.addWidget(output_box, 0, 0)
        main_layout.addWidget(processing_box, 1, 0)
        main_layout.addWidget(self.report_box, 2, 0)
        main_layout.addWidget(self.btn_process, 3, 0)

        main_layout.setRowStretch(2, 1)

    def _create_output_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        layout.addRow("Ширина:", self.spin_out_width)
        layout.addRow("Высота:", self.spin_out_height)
        layout.addRow("DPI:", self.spin_dpi)
        return page

    def _create_processing_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        layout.addRow("Шаг сетки:", self.spin_spacing)
        layout.addRow("Размер точки:", self.spin_base_dot_size)
        #layout.addRow("Контраст:", self.spin_contrast)
        layout.addRow(self.check_mirror)
        layout.addRow(self.check_fill_inner)
        layout.addRow(self.check_honeycomb)
        return page

    def _connect_signals(self):
        """
        ИСПРАВЛЕНИЕ: Соединяет сигналы для real-time обновления границ холста.
        """
        # Главная кнопка
        self.btn_process.clicked.connect(self.processClicked.emit)
        self.check_mirror.clicked.connect(self.mirrorClicked.emit)

        # НОВОЕ: Real-time обновление границ холста при изменении параметров вывода
        self.spin_out_width.valueChanged.connect(self._on_canvas_settings_changed)
        self.spin_out_height.valueChanged.connect(self._on_canvas_settings_changed)
        self.spin_dpi.valueChanged.connect(self._on_canvas_settings_changed)

        print("Подключены сигналы для real-time обновления границ холста")

    def _on_canvas_settings_changed(self):
        """
        НОВЫЙ МЕТОД: Обрабатывает изменения параметров холста и отправляет сигнал для обновления границ.
        """
        # Создаем новые настройки вывода
        output_settings = OutputSettings(
            width_mm=self.spin_out_width.value(),
            height_mm=self.spin_out_height.value(),
            dpi=self.spin_dpi.value()
        )

        print(
            f"Изменения настроек холста: {output_settings.width_mm}x{output_settings.height_mm} мм при {output_settings.dpi} DPI")
        print(f"Размер в пикселях: {output_settings.width_px}x{output_settings.height_px} px")

        # Отправляем сигнал для обновления границ
        self.canvasSizeChanged.emit(output_settings)

    def get_current_settings(self) -> ProcessingSettings:
        """
        Собирает и ВОЗВРАЩАЕТ текущие настройки из виджетов.
        """
        output_settings = OutputSettings(
            width_mm=self.spin_out_width.value(),
            height_mm=self.spin_out_height.value(),
            dpi=self.spin_dpi.value()
        )

        return ProcessingSettings(
            output=output_settings,
            spacing=self.spin_spacing.value(),
            base_dot_size_mm=self.spin_base_dot_size.value(),
            contrast=self.spin_contrast.value(),
            fill_inner_white=self.check_fill_inner.isChecked(),
            grid_mode="honeycomb" if self.check_honeycomb.isChecked() else "uniform"
        )

    def update_report(self, project: Project):
        """Обновляет данные в панели отчета и показывает ее."""
        self.report_panel.update_report(project)
        self.report_box.show()

    def set_output_dimensions(self, width_mm: int, height_mm: int):
        """
        Программно устанавливает значения для полей ширины и высоты вывода.
        ИСПРАВЛЕНИЕ: Блокирует сигналы при программном изменении, чтобы избежать лишних обновлений.
        """
        # Блокируем сигналы чтобы не вызывать лишние обновления
        self.spin_out_width.blockSignals(True)
        self.spin_out_height.blockSignals(True)

        self.spin_out_width.setValue(width_mm)
        self.spin_out_height.setValue(height_mm)

        # Разблокируем сигналы
        self.spin_out_width.blockSignals(False)
        self.spin_out_height.blockSignals(False)

        # Вручную вызываем обновление границ после программного изменения
        self._on_canvas_settings_changed()

    def get_current_output_settings(self) -> OutputSettings:
        """
        НОВЫЙ МЕТОД: Возвращает только текущие настройки вывода.
        """
        return OutputSettings(
            width_mm=self.spin_out_width.value(),
            height_mm=self.spin_out_height.value(),
            dpi=self.spin_dpi.value()
        )