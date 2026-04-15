# ui/panels/left_toolbar.py
# Панель инструментов, расположенная слева.

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QPushButton

class LeftToolbar(QFrame):
    """
    Левая панель инструментов.
    Отвечает за создание кнопок и отправку сигналов при нажатии на них.
    """
    # Сигналы, которые панель отправляет "наружу". Presenter будет их слушать.
    loadImageClicked = pyqtSignal()
    addTextClicked = pyqtSignal()
    traceClicked = pyqtSignal()
    paletteClicked = pyqtSignal()
    sizesClicked = pyqtSignal()
    exportClicked = pyqtSignal()
    editModeClicked = pyqtSignal()
    settingsClicked = pyqtSignal()
    toggleThemeClicked = pyqtSignal()
    canvasBackgroundClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("leftToolbar")
        self.setFixedWidth(80)

        # --- Создание виджетов ---
        self.btn_load_image = QPushButton("🖼️")
        self.btn_load_image.setToolTip("Загрузить изображение")

        self.btn_add_text = QPushButton("🅰️")
        self.btn_add_text.setToolTip("Создать макет из текста")

        self.btn_trace = QPushButton("✨")
        self.btn_trace.setToolTip("Трассировка и обработка изображения")

        self.btn_sizes = QPushButton("💎")
        self.btn_sizes.setToolTip("Выбор размеров стразов")

        self.btn_palette = QPushButton("🎨")
        self.btn_palette.setToolTip("Редактор палитры цветов")

        self.btn_edit_mode = QPushButton("✏️")
        self.btn_edit_mode.setToolTip("Редактировать точки вручную")
        self.btn_edit_mode.setEnabled(False)

        self.btn_export = QPushButton("💾")
        self.btn_export.setToolTip("Экспорт макета")
        self.btn_export.setEnabled(False)

        self.btn_canvas_bg = QPushButton("🖌️")
        self.btn_canvas_bg.setToolTip("Изменить цвет фона холста")

        self.btn_toggle_theme = QPushButton("🌙")
        self.btn_toggle_theme.setToolTip("Сменить тему (светлая/темная)")

        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setToolTip("Проверить обновления")

        # --- Компоновка ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(self.btn_load_image)
        layout.addWidget(self.btn_add_text)
        layout.addWidget(self.btn_trace)
        layout.addWidget(self.btn_palette)
        layout.addWidget(self.btn_sizes)
        layout.addWidget(self.btn_export)
        layout.addWidget(self.btn_edit_mode)
        layout.addStretch()
        layout.addWidget(self.btn_canvas_bg)
        layout.addWidget(self.btn_toggle_theme)
        layout.addWidget(self.btn_settings)

        # --- Внутренние соединения сигналов ---
        self.btn_load_image.clicked.connect(self.loadImageClicked.emit)
        self.btn_add_text.clicked.connect(self.addTextClicked.emit)
        self.btn_trace.clicked.connect(self.traceClicked.emit)
        self.btn_palette.clicked.connect(self.paletteClicked.emit)
        self.btn_sizes.clicked.connect(self.sizesClicked.emit)
        self.btn_export.clicked.connect(self.exportClicked.emit)
        self.btn_edit_mode.clicked.connect(self.editModeClicked.emit)
        self.btn_settings.clicked.connect(self.settingsClicked.emit)
        self.btn_toggle_theme.clicked.connect(self.toggleThemeClicked.emit)
        self.btn_canvas_bg.clicked.connect(self.canvasBackgroundClicked.emit)

    def set_edit_button_enabled(self, enabled: bool):
        self.btn_edit_mode.setEnabled(enabled)

    def set_export_button_enabled(self, enabled: bool):
        self.btn_export.setEnabled(enabled)