# ui/main_window.py
# Главное окно приложения. Собирает все компоненты UI.

from typing import List, Optional
from PIL.Image import Image

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame,
    QFileDialog, QMessageBox, QApplication
)

from .interfaces import IMainView
from core.models import Project, OutputSettings, Rhinestone, ProcessingSettings
from .panels.edit_toolbar import EditToolbar

from .panels.left_toolbar import LeftToolbar
from .panels.settings_panel import SettingsPanel
from .components.hybrid_viewer import HybridViewer
from .components.editable_canvas import EditableCanvas
from .utils import pil_to_qpixmap
from abc import ABCMeta


class QtABCMeta(type(QMainWindow), ABCMeta):
    pass


class MainWindow(QMainWindow, IMainView, metaclass=QtABCMeta):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lumo")
        self.resize(1440, 810)

        # Создание компонентов UI
        self.left_toolbar = LeftToolbar(self)
        self.settings_panel = SettingsPanel(self)
        self.photo_viewer = HybridViewer(parent=self)
        self.editable_canvas = EditableCanvas(None, self)
        self.editable_canvas.hide()
        self.edit_toolbar = EditToolbar()
        self.edit_toolbar.hide()

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        root_layout = QHBoxLayout(main_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(1)

        center_frame = QFrame()
        center_layout = QVBoxLayout(center_frame)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(self.photo_viewer)
        center_layout.addWidget(self.editable_canvas)

        root_layout.addWidget(self.left_toolbar)
        root_layout.addWidget(center_frame, 1)
        root_layout.addWidget(self.settings_panel)
        root_layout.addWidget(self.edit_toolbar)

    def _connect_signals(self):
        """
        Подключает сигналы для real-time обновления границ холста
        при изменении размеров в панели настроек.
        """
        self.settings_panel.canvasSizeChanged.connect(self.photo_viewer.update_canvas_bounds)
        self.settings_panel.canvasSizeChanged.connect(self.editable_canvas.update_canvas_bounds)

        # Установка начальных границ холста при запуске
        current_settings = self.settings_panel.get_current_output_settings()
        self.photo_viewer.update_canvas_bounds(current_settings)
        self.editable_canvas.update_canvas_bounds(current_settings)

    def set_output_dimensions(self, width_mm: int, height_mm: int):
        self.settings_panel.set_output_dimensions(width_mm, height_mm)

    def display_image(self, image: Image, output_settings: Optional[OutputSettings] = None,
                      preserve_view: bool = False):
        pixmap = pil_to_qpixmap(image)
        self.photo_viewer.setPixmap(pixmap, output_settings, True)
        self.set_ui_mode('view')

    def update_project_preview(self, project: Project, settings: OutputSettings, preserve_view: bool = False):
        self.photo_viewer.load_project(project, settings, preserve_view)
        self.update_color_report(project)

    def update_color_report(self, project: Project):
        self.settings_panel.update_report(project)

    def get_source_image_path(self) -> Optional[str]:
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Выберите изображение", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        return filepath if filepath else None

    def set_canvas_background(self, color: QColor):
        """Устанавливает цвет фона для обоих холстов (просмотра и редактирования)."""
        self.photo_viewer.setBackgroundColor(color)
        self.editable_canvas.setBackgroundColor(color)

    def get_save_folder_path(self) -> Optional[str]:
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        return folder if folder else None

    def set_ui_mode(self, mode: str):
        is_edit_mode = (mode == 'edit')
        self.editable_canvas.setVisible(is_edit_mode)
        self.edit_toolbar.setVisible(is_edit_mode)
        self.photo_viewer.setVisible(not is_edit_mode)
        self.settings_panel.setVisible(not is_edit_mode)

    def show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    def show_info(self, title: str, message: str):
        QMessageBox.information(self, title, message)

    def show_progress(self, message: str):
        self.statusBar().showMessage(message, 0)
        QApplication.setOverrideCursor(Qt.WaitCursor)

    def hide_progress(self):
        self.statusBar().clearMessage()
        QApplication.restoreOverrideCursor()

    def set_edit_button_enabled(self, enabled: bool):
        self.left_toolbar.set_edit_button_enabled(enabled)

    def set_export_button_enabled(self, enabled: bool):
        self.left_toolbar.set_export_button_enabled(enabled)

    def update_selection_info(self, selected_rhinestones: List[Rhinestone]):
        self.edit_toolbar.update_selection(selected_rhinestones)

    def get_processing_settings(self) -> Optional[ProcessingSettings]:
        return self.settings_panel.get_current_settings()