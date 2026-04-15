# ui/components/size_display_button.py
# Компонент для отображения размера страза

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QPushButton


class SizeDisplayButton(QPushButton):
    """Кнопка отображения размера с поддержкой тем через QSS."""

    sizeChangeRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sizeDisplayButton")
        self.setFixedHeight(40)
        self.setMinimumWidth(120)
        self.clicked.connect(self.sizeChangeRequested.emit)

    def set_size(self, size_name: str, diameter_mm: float, mixed: bool = False):
        """Устанавливает размер для отображения."""
        if mixed:
            self.setText("Смешанные")
            self.setToolTip("Выбраны стразы разных размеров")
        else:
            self.setText(f"{size_name}")
            self.setToolTip(f"Размер: {size_name} ({diameter_mm} мм)")