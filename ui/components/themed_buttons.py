# ui/components/themed_buttons.py
# Базовые тематические компоненты кнопок

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QPushButton, QLabel, QVBoxLayout, QCheckBox


def get_text_color_for_background(bg_rgb: tuple) -> str:
    """Вычисляет контрастный цвет текста для фона."""
    r, g, b = bg_rgb
    luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    return "#1E1E1E" if luminance > 140 else "#FFFFFF"


class ThemedColorDisplayButton(QPushButton):
    """Кнопка для отображения цвета с поддержкой тем."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("colorDisplayButton")
        self.setMinimumHeight(70)
        self.setCursor(Qt.PointingHandCursor)

        # Создаем внутренний QLabel для корректного отображения HTML
        self._label = QLabel(self)
        self._label.setObjectName("colorDisplayLabel")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setAttribute(Qt.WA_TranslucentBackground)
        self._label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        # Layout для метки
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self._label)

        # Сохраняем данные для перерисовки
        self._current_color_name = ""
        self._current_color_rgb = (0, 0, 0)
        self._is_mixed = False

        self.reset_style()

    def reset_style(self):
        """Сбрасывает стиль кнопки к состоянию 'Не выбран'."""
        self._label.setText("Не выбран")
        self._current_color_name = ""
        self._is_mixed = False

        # Сбрасываем инлайновый стиль, чтобы снова применялся
        # стиль из основного QSS файла (light/dark_theme.qss).
        self.setStyleSheet("")
        self.setProperty("colorState", "default")

        # Принудительно заставляем Qt перерисовать виджет с учётом основного файла стилей
        self.style().unpolish(self)
        self.style().polish(self)

    def set_color(self, color_name: str, color_rgb: tuple, mixed: bool = False):
        """Устанавливает цвет кнопки и соответствующий текст."""
        self._current_color_name = color_name
        self._current_color_rgb = color_rgb
        self._is_mixed = mixed

        # Состояние "Смешанные цвета" по-прежнему управляется через основной QSS
        if mixed:
            self.reset_style()  # Сначала сбрасываем любой инлайновый стиль
            self._label.setText("Смешанные цвета")
            self.setProperty("colorState", "mixed")
            self.style().unpolish(self)
            self.style().polish(self)
            return

        # Убираем свойство, чтобы оно не конфликтовало со стилями
        self.setProperty("colorState", "colored")

        r, g, b = color_rgb
        hex_code = f"#{r:02X}{g:02X}{b:02X}"
        text_color = get_text_color_for_background(color_rgb)
        hex_text_color = "#555555" if text_color == "#1E1E1E" else "#A0A0A0"

        html_text = f"""
        <div style='line-height: 120%; text-align: center;'>
            <div style='font-size: 11pt; font-weight: bold; color: {text_color};'>{color_name}</div>
            <div style='font-size: 10pt; font-weight: 400; color: {hex_text_color}; margin-top: 4px;'>{hex_code}</div>
        </div>
        """
        self._label.setText(html_text)

        # ИЗМЕНЕНИЕ: Вместо QSS-свойства, применяем стиль напрямую.
        # Этот метод работает во всех версиях Qt и является самым надежным.
        # Стили рамки и скругления взяты из light_theme.qss для универсальности.
        self.setStyleSheet(f"""
            QPushButton#colorDisplayButton {{
                background-color: {hex_code};
                border: 1px solid rgba(0, 0, 0, 0.2);
                border-radius: 8px;
            }}
            QPushButton#colorDisplayButton:hover {{
                border: 1px solid rgba(0, 0, 0, 0.4);
            }}
        """)


class ThemedModernButton(QPushButton):
    """Современная кнопка-пилюля с поддержкой тем."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("modernButton")
        self.setFixedHeight(36)
        self.setMinimumWidth(80)
        self._is_active = False

    def set_active(self, active: bool):
        """Устанавливает активное состояние кнопки."""
        self._is_active = active
        self.setProperty("active", active)
        self.setStyleSheet("")  # Сброс для переприменения QSS


class ThemedSizeDisplay(QPushButton):
    """Отображение размера страза."""
    sizeChangeRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sizeDisplayButton")
        self.setFixedHeight(40)
        self.setMinimumWidth(120)
        self.clicked.connect(self.sizeChangeRequested.emit)

    def set_size(self, size_name: str, diameter_mm: float, mixed: bool = False):
        """Устанавливает отображаемый размер."""
        if mixed:
            self.setText("Смешанные")
            self.setToolTip("Выбраны стразы разных размеров")
            self.setProperty("sizeState", "mixed")
        else:
            self.setText(f"{size_name}")
            self.setToolTip(f"Размер: {size_name} ({diameter_mm} мм)")
            self.setProperty("sizeState", "normal")

        self.setStyleSheet("")  # Сброс для переприменения QSS


class ThemedModernToggle(QCheckBox):
    """Современный переключатель."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("modernToggle")
        self.setFixedHeight(32)