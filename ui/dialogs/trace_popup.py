# ui/dialogs/trace_popup.py
from PyQt5.QtCore import pyqtSignal, QTimer, Qt, QPoint
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QGridLayout, QLabel, QSlider,
    QPushButton, QComboBox, QCheckBox, QDialogButtonBox,
    QHBoxLayout, QGroupBox, QScrollArea, QWidget
)
from core.models import TraceParameters


class TraceDialog(QFrame):
    """
    Улучшенный диалог настройки трассировки с независимыми переключателями для каждого эффекта.
    """

    # Сигналы
    preview_requested = pyqtSignal(TraceParameters)
    trace_confirmed = pyqtSignal(TraceParameters)
    trace_cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_params = None
        self._apply_clicked = False
        self._setup_window()
        self._init_ui()
        self._connect_signals()

        if parent:
            parent.installEventFilter(self)

        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._emit_preview_request)

        self._initialized = False

    def eventFilter(self, obj, event):
        """Фильтр событий для закрытия при клике вне диалога."""
        from PyQt5.QtCore import QEvent

        if event.type() == QEvent.MouseButtonPress and self.isVisible():
            global_pos = event.globalPos()
            if not self.geometry().contains(global_pos):
                self._on_click_outside()
                return True

        return super().eventFilter(obj, event)

    def _on_click_outside(self):
        """Обработка клика вне диалога."""
        self._apply_clicked = False
        self.trace_cancelled.emit()
        self.close()

    def _setup_window(self):
        """Настройка окна диалога."""
        self.setWindowTitle("Настройка трассировки")
        self.setFixedSize(480, 720)
        self.setObjectName("lumoTraceDialog")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)

    def _init_ui(self):
        """Создание интерфейса."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок
        header = QFrame()
        header.setObjectName("lumoTraceDialogHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15)

        title_label = QLabel("Настройка трассировки")
        title_label.setObjectName("lumoTraceDialogTitle")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Кнопка сброса в заголовке
        self.reset_btn = QPushButton("Сброс")
        self.reset_btn.setObjectName("lumoTraceResetButton")
        header_layout.addWidget(self.reset_btn)

        main_layout.addWidget(header)

        # Прокручиваемая область
        scroll_area = QScrollArea()
        scroll_area.setObjectName("lumoTraceScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_widget.setObjectName("lumoTraceScrollContent")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(20, 20, 20, 20)

        # Группа постеризации
        self.colors_group = self._create_effect_group(
            "lumoTraceColorsGroup",
            "Постеризация (количество цветов)",
            "lumoTraceColorsCheck"
        )

        self.colors_frame = self._create_slider_group(
            "Количество цветов", 1, 64, 8, is_int=True,
            object_name="lumoTraceColorsSlider"
        )
        self.colors_group.layout().addWidget(self.colors_frame)
        content_layout.addWidget(self.colors_group)

        # Группа яркости
        self.brightness_group = self._create_effect_group(
            "lumoTraceBrightnessGroup",
            "Коррекция яркости",
            "lumoTraceBrightnessCheck"
        )

        self.brightness_frame = self._create_slider_group(
            "Яркость", 0.3, 2.5, 1.0, is_int=False,
            object_name="lumoTraceBrightnessSlider"
        )
        self.brightness_group.layout().addWidget(self.brightness_frame)
        content_layout.addWidget(self.brightness_group)

        # Группа контрастности
        self.contrast_group = self._create_effect_group(
            "lumoTraceContrastGroup",
            "Коррекция контрастности",
            "lumoTraceContrastCheck"
        )

        self.contrast_frame = self._create_slider_group(
            "Контрастность", 0.1, 3.0, 1.0, is_int=False,
            object_name="lumoTraceContrastSlider"
        )
        self.contrast_group.layout().addWidget(self.contrast_frame)
        content_layout.addWidget(self.contrast_group)

        # Группа насыщенности
        self.saturation_group = self._create_effect_group(
            "lumoTraceSaturationGroup",
            "Коррекция насыщенности",
            "lumoTraceSaturationCheck"
        )

        self.saturation_frame = self._create_slider_group(
            "Насыщенность", 0.0, 2.5, 1.0, is_int=False,
            object_name="lumoTraceSaturationSlider"
        )
        self.saturation_group.layout().addWidget(self.saturation_frame)
        content_layout.addWidget(self.saturation_group)

        # Группа гамма-коррекции
        self.gamma_group = self._create_effect_group(
            "lumoTraceGammaGroup",
            "Гамма-коррекция",
            "lumoTraceGammaCheck"
        )

        self.gamma_frame = self._create_slider_group(
            "Гамма", 0.3, 3.0, 1.0, is_int=False,
            object_name="lumoTraceGammaSlider"
        )
        self.gamma_group.layout().addWidget(self.gamma_frame)
        content_layout.addWidget(self.gamma_group)

        # Группа цветовой температуры
        self.temperature_group = self._create_effect_group(
            "lumoTraceTemperatureGroup",
            "Цветовая температура",
            "lumoTraceTemperatureCheck"
        )

        self.temperature_frame = self._create_slider_group(
            "Температура", -1.0, 1.0, 0.0, is_int=False,
            object_name="lumoTraceTemperatureSlider"
        )
        self.temperature_group.layout().addWidget(self.temperature_frame)
        content_layout.addWidget(self.temperature_group)

        # Группа размытия
        self.blur_group = self._create_effect_group(
            "lumoTraceBlurGroup",
            "Размытие",
            "lumoTraceBlurCheck"
        )

        # Тип размытия
        blur_type_layout = QHBoxLayout()
        blur_type_label = QLabel("Тип:")
        blur_type_label.setObjectName("lumoTraceBlurTypeLabel")

        self.blur_combo = QComboBox()
        self.blur_combo.setObjectName("lumoTraceBlurTypeCombo")
        self.blur_combo.addItems(["Гауссово", "Медианное", "Билатеральное", "Движение", "Радиальное"])

        blur_type_layout.addWidget(blur_type_label)
        blur_type_layout.addWidget(self.blur_combo)
        blur_type_layout.addStretch()

        self.blur_group.layout().addLayout(blur_type_layout)

        self.blur_strength_frame = self._create_slider_group(
            "Сила размытия", 0.1, 5.0, 1.0, is_int=False,
            object_name="lumoTraceBlurStrengthSlider"
        )
        self.blur_group.layout().addWidget(self.blur_strength_frame)
        content_layout.addWidget(self.blur_group)

        # Группа повышения резкости
        self.sharpen_group = self._create_effect_group(
            "lumoTraceSharpenGroup",
            "Повышение резкости",
            "lumoTraceSharpenCheck"
        )

        self.sharpen_frame = self._create_slider_group(
            "Сила резкости", 0.1, 3.0, 1.0, is_int=False,
            object_name="lumoTraceSharpenStrengthSlider"
        )
        self.sharpen_group.layout().addWidget(self.sharpen_frame)
        content_layout.addWidget(self.sharpen_group)

        # Группа инверсии
        self.invert_group = self._create_effect_group(
            "lumoTraceInvertGroup",
            "Инвертирование цветов",
            "lumoTraceInvertCheck"
        )
        content_layout.addWidget(self.invert_group)

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # Панель кнопок
        buttons_frame = QFrame()
        buttons_frame.setObjectName("lumoTraceDialogButtons")
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(20, 15, 20, 15)
        buttons_layout.setSpacing(10)

        # Информация о включенных эффектах
        self.effects_info = QLabel("Включенные эффекты: Нет")
        self.effects_info.setObjectName("lumoTraceEffectsInfo")
        buttons_layout.addWidget(self.effects_info)

        buttons_layout.addStretch()

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("lumoTraceCancelButton")
        buttons_layout.addWidget(self.cancel_btn)

        self.apply_btn = QPushButton("Применить")
        self.apply_btn.setObjectName("lumoTraceApplyButton")
        self.apply_btn.setDefault(True)
        buttons_layout.addWidget(self.apply_btn)

        main_layout.addWidget(buttons_frame)

    def _create_effect_group(self, group_name: str, title: str, check_name: str) -> QGroupBox:
        """Создает группу с переключателем для эффекта."""
        group = QGroupBox()
        group.setObjectName(group_name)

        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Заголовок с чекбоксом
        header_layout = QHBoxLayout()

        checkbox = QCheckBox(title)
        checkbox.setObjectName(check_name)
        header_layout.addWidget(checkbox)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Сохраняем ссылку на чекбокс
        group.checkbox = checkbox

        return group

    def _create_slider_group(self, title: str, min_val: float, max_val: float,
                             default: float, is_int: bool = False,
                             object_name: str = None) -> QFrame:
        """Создает группу со слайдером и подписями."""
        frame = QFrame()
        frame.setObjectName(object_name or "lumoTraceSliderGroup")

        layout = QVBoxLayout(frame)
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)

        # Верхняя строка с названием и значением
        top_layout = QHBoxLayout()

        title_label = QLabel(title)
        title_label.setObjectName("lumoTraceSliderTitle")
        top_layout.addWidget(title_label)

        top_layout.addStretch()

        value_label = QLabel()
        value_label.setObjectName("lumoTraceSliderValue")
        top_layout.addWidget(value_label)

        layout.addLayout(top_layout)

        # Слайдер
        slider = QSlider(Qt.Horizontal)
        slider.setObjectName(f"{object_name}_control" if object_name else "lumoTraceSlider")
        slider.setRange(0, 1000)  # Высокая точность

        slider.setProperty("min_val", min_val)
        slider.setProperty("max_val", max_val)
        slider.setProperty("is_int", is_int)
        slider.setProperty("value_label", value_label)
        slider.setProperty("default_val", default)

        # Устанавливаем начальное значение
        normalized = (default - min_val) / (max_val - min_val)
        slider.setValue(int(normalized * 1000))

        self._update_slider_label(slider)

        layout.addWidget(slider)

        return frame

    def _connect_signals(self):
        """Подключение сигналов."""
        # Чекбоксы групп
        for group in [self.colors_group, self.brightness_group, self.contrast_group,
                      self.saturation_group, self.gamma_group, self.temperature_group,
                      self.blur_group, self.sharpen_group, self.invert_group]:
            if hasattr(group, 'checkbox'):
                group.checkbox.stateChanged.connect(self._on_effect_toggled)

        # Слайдеры
        for frame in [self.colors_frame, self.brightness_frame, self.contrast_frame,
                      self.saturation_frame, self.gamma_frame, self.temperature_frame,
                      self.blur_strength_frame, self.sharpen_frame]:
            slider = frame.findChild(QSlider)
            if slider:
                slider.valueChanged.connect(lambda value, s=slider: self._on_slider_changed(s))

        # Комбобокс типа размытия
        self.blur_combo.currentIndexChanged.connect(self._schedule_preview)

        # Кнопки
        self.reset_btn.clicked.connect(self._reset_to_defaults)
        self.apply_btn.clicked.connect(self._on_apply)
        self.cancel_btn.clicked.connect(self._on_cancel)

    def _on_effect_toggled(self):
        """Обработчик переключения эффекта."""
        self._update_effects_info()
        self._schedule_preview()

    def _on_slider_changed(self, slider: QSlider):
        """Обработчик изменения слайдера."""
        self._update_slider_label(slider)
        self._update_effects_info()
        self._schedule_preview()

    def _update_slider_label(self, slider: QSlider):
        """Обновляет подпись значения слайдера."""
        min_val = slider.property("min_val")
        max_val = slider.property("max_val")
        is_int = slider.property("is_int")
        value_label = slider.property("value_label")

        normalized = slider.value() / 1000.0
        real_value = min_val + normalized * (max_val - min_val)

        if is_int:
            value_label.setText(str(int(real_value)))
        else:
            if abs(real_value) < 0.01:
                value_label.setText("0.00")
            else:
                value_label.setText(f"{real_value:.2f}")

    def _update_effects_info(self):
        """Обновляет информацию о включенных эффектах."""
        params = self.get_current_parameters()
        enabled_effects = params.get_enabled_effects()

        if enabled_effects:
            info_text = f"Включено эффектов: {len(enabled_effects)}"
        else:
            info_text = "Включенные эффекты: Нет"

        self.effects_info.setText(info_text)
        self.effects_info.setToolTip("\n".join(enabled_effects) if enabled_effects else "Нет активных эффектов")

    def _schedule_preview(self):
        """Планирует запрос превью."""
        if self._initialized:
            self._preview_timer.start(150)  # Немного задержки для плавности

    def _emit_preview_request(self):
        """Отправляет запрос на обновление превью."""
        params = self.get_current_parameters()
        self.preview_requested.emit(params)

    def get_current_parameters(self) -> TraceParameters:
        """Получает текущие параметры из UI."""
        params = TraceParameters()

        # Постеризация
        params.colors_enabled = self.colors_group.checkbox.isChecked()
        if params.colors_enabled:
            params.colors = int(self._get_slider_value(self.colors_frame.findChild(QSlider)))
        else:
            params.colors = 0

        # Яркость
        params.brightness_enabled = self.brightness_group.checkbox.isChecked()
        if params.brightness_enabled:
            params.brightness = self._get_slider_value(self.brightness_frame.findChild(QSlider))

        # Контрастность
        params.contrast_enabled = self.contrast_group.checkbox.isChecked()
        if params.contrast_enabled:
            params.contrast = self._get_slider_value(self.contrast_frame.findChild(QSlider))

        # Насыщенность
        params.saturation_enabled = self.saturation_group.checkbox.isChecked()
        if params.saturation_enabled:
            params.saturation = self._get_slider_value(self.saturation_frame.findChild(QSlider))

        # Гамма-коррекция
        params.gamma_enabled = self.gamma_group.checkbox.isChecked()
        if params.gamma_enabled:
            params.gamma = self._get_slider_value(self.gamma_frame.findChild(QSlider))

        # Цветовая температура
        params.temperature_enabled = self.temperature_group.checkbox.isChecked()
        if params.temperature_enabled:
            params.temperature = self._get_slider_value(self.temperature_frame.findChild(QSlider))

        # Размытие
        params.blur_enabled = self.blur_group.checkbox.isChecked()
        if params.blur_enabled:
            blur_types = ["gaussian", "median", "bilateral", "motion", "radial"]
            params.blur_type = blur_types[self.blur_combo.currentIndex()]
            params.blur_strength = self._get_slider_value(self.blur_strength_frame.findChild(QSlider))
        else:
            params.blur_type = "none"
            params.blur_strength = 0

        # Повышение резкости
        params.sharpen_enabled = self.sharpen_group.checkbox.isChecked()
        if params.sharpen_enabled:
            params.sharpen_strength = self._get_slider_value(self.sharpen_frame.findChild(QSlider))

        # Инверсия
        params.invert_enabled = self.invert_group.checkbox.isChecked()

        return params

    def _get_slider_value(self, slider: QSlider) -> float:
        """Получает реальное значение слайдера."""
        min_val = slider.property("min_val")
        max_val = slider.property("max_val")
        is_int = slider.property("is_int")

        normalized = slider.value() / 1000.0
        value = min_val + normalized * (max_val - min_val)

        return int(value) if is_int else value

    def _reset_to_defaults(self):
        """Сбрасывает все настройки к значениям по умолчанию."""
        # Включаем только постеризацию по умолчанию
        self.colors_group.checkbox.setChecked(True)
        self.brightness_group.checkbox.setChecked(False)
        self.contrast_group.checkbox.setChecked(False)
        self.saturation_group.checkbox.setChecked(False)
        self.gamma_group.checkbox.setChecked(False)
        self.temperature_group.checkbox.setChecked(False)
        self.blur_group.checkbox.setChecked(False)
        self.sharpen_group.checkbox.setChecked(False)
        self.invert_group.checkbox.setChecked(False)

        # Сбрасываем слайдеры к значениям по умолчанию
        for frame in [self.colors_frame, self.brightness_frame, self.contrast_frame,
                      self.saturation_frame, self.gamma_frame, self.temperature_frame,
                      self.blur_strength_frame, self.sharpen_frame]:
            slider = frame.findChild(QSlider)
            if slider:
                default = slider.property("default_val")
                self._set_slider_value(slider, default)

        # Сбрасываем комбобокс
        self.blur_combo.setCurrentIndex(0)

        self._update_effects_info()
        self._schedule_preview()

    def set_parameters(self, params: TraceParameters):
        """Устанавливает параметры в UI."""
        if not params:
            return

        self._initialized = False
        self._original_params = params

        # Устанавливаем состояние чекбоксов
        self.colors_group.checkbox.setChecked(getattr(params, 'colors_enabled', True))
        self.brightness_group.checkbox.setChecked(getattr(params, 'brightness_enabled', False))
        self.contrast_group.checkbox.setChecked(getattr(params, 'contrast_enabled', False))
        self.saturation_group.checkbox.setChecked(getattr(params, 'saturation_enabled', False))
        self.gamma_group.checkbox.setChecked(getattr(params, 'gamma_enabled', False))
        self.temperature_group.checkbox.setChecked(getattr(params, 'temperature_enabled', False))
        self.blur_group.checkbox.setChecked(getattr(params, 'blur_enabled', False))
        self.sharpen_group.checkbox.setChecked(getattr(params, 'sharpen_enabled', False))
        self.invert_group.checkbox.setChecked(getattr(params, 'invert_enabled', False))

        # Устанавливаем значения слайдеров
        if hasattr(params, 'colors'):
            self._set_slider_value(self.colors_frame.findChild(QSlider), params.colors)
        if hasattr(params, 'brightness'):
            self._set_slider_value(self.brightness_frame.findChild(QSlider), params.brightness)
        if hasattr(params, 'contrast'):
            self._set_slider_value(self.contrast_frame.findChild(QSlider), params.contrast)
        if hasattr(params, 'saturation'):
            self._set_slider_value(self.saturation_frame.findChild(QSlider), params.saturation)
        if hasattr(params, 'gamma'):
            self._set_slider_value(self.gamma_frame.findChild(QSlider), params.gamma)
        if hasattr(params, 'temperature'):
            self._set_slider_value(self.temperature_frame.findChild(QSlider), params.temperature)
        if hasattr(params, 'blur_strength'):
            self._set_slider_value(self.blur_strength_frame.findChild(QSlider), params.blur_strength)
        if hasattr(params, 'sharpen_strength'):
            self._set_slider_value(self.sharpen_frame.findChild(QSlider), params.sharpen_strength)

        # Устанавливаем тип размытия
        if hasattr(params, 'blur_type'):
            blur_map = {"gaussian": 0, "median": 1, "bilateral": 2, "motion": 3, "radial": 4}
            self.blur_combo.setCurrentIndex(blur_map.get(params.blur_type, 0))

        self._update_effects_info()
        self._initialized = True

    def _set_slider_value(self, slider: QSlider, value: float):
        """Устанавливает значение слайдера."""
        min_val = slider.property("min_val")
        max_val = slider.property("max_val")

        normalized = (value - min_val) / (max_val - min_val)
        slider_pos = max(0, min(1000, int(normalized * 1000)))
        slider.setValue(slider_pos)

        self._update_slider_label(slider)

    def show_at(self, pos: QPoint):
        """Показывает диалог в указанной позиции."""
        self.move(pos)
        self.show()
        self.raise_()
        self.activateWindow()

        self._initialized = True
        self._apply_clicked = False
        self._update_effects_info()
        self._emit_preview_request()

    def _on_apply(self):
        """Обработчик кнопки Применить."""
        self._apply_clicked = True
        params = self.get_current_parameters()
        self.trace_confirmed.emit(params)
        self.close()

    def _on_cancel(self):
        """Обработчик кнопки Отмена."""
        self._apply_clicked = False
        self.trace_cancelled.emit()
        self.close()

    def closeEvent(self, event):
        """При закрытии окна проверяем, как оно было закрыто."""
        if not self._apply_clicked:
            self.trace_cancelled.emit()

        if self.parent():
            self.parent().removeEventFilter(self)

        self._initialized = False
        self._preview_timer.stop()
        self._apply_clicked = False
        super().closeEvent(event)