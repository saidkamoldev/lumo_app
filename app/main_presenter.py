# app/main_presenter.py
# Презентер - "мозг" приложения. Управляет логикой и состоянием.

import os
from typing import Optional, List

from PyQt5.QtCore import QObject, pyqtSignal, QPoint, QThread
from PyQt5.QtWidgets import QDialog, QPushButton, QApplication, QColorDialog
from PIL import Image

from app.update_manager import UpdateManager
from ui.dialogs.settings_dialog import SettingsDialog
from core.services.export_service import ExportService
from core.services.image_processor_service import ImageProcessorService
from core.services.palette_service import PaletteService
from core.services.text_service import TextImageService
from core.services.trace_processor import TraceProcessor
from core.services.image_state_manager import ImageStateManager
from ui.dialogs.export_dialog import ExportDialog
from ui.dialogs.text_dialog import TextCreatorDialog
from ui.dialogs.trace_popup import TraceDialog
from ui.interfaces import IMainView
from ui.dialogs.color_selector import ColorSelectorPopup
from ui.dialogs.size_selector import SizeSelectorPopup
from ui.theme.theme_manager import ThemeManager
from core.models import (
    Project, AppSettings,
    RhinestoneSize, OutputSettings, ExportSettings, TextLayoutSettings, TraceParameters, PaletteColor, Rhinestone
)


class ExportWorker(QObject):
    """
    Выполняет задачу экспорта в отдельном потоке, чтобы не блокировать UI.
    """
    finished = pyqtSignal(bool, str)

    def __init__(self, export_service: ExportService, project: Project, output: OutputSettings, export: ExportSettings):
        super().__init__()
        self.export_service = export_service
        self.project = project
        self.output = output
        self.export = export

    def run(self):
        """Запускает процесс экспорта."""
        try:
            success = self.export_service.export_project(self.project, self.output, self.export)
            if success:
                full_path = os.path.join(self.export.output_path, self.export.filename)
                self.finished.emit(True, full_path)
            else:
                self.finished.emit(False, "Не удалось сохранить файл. Подробности в консоли.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(False, f"Критическая ошибка при экспорте:\n{e}")


class TraceWorker(QObject):
    """
    Выполняет обработку трассировки изображения в отдельном потоке.
    """
    finished = pyqtSignal(object)

    def __init__(self, trace_processor, params: TraceParameters, is_for_display: bool = False):
        super().__init__()
        self.trace_processor = trace_processor
        self.params = params
        self.is_for_display = is_for_display

    def run(self):
        """Выполняет трассировку."""
        try:
            result = self.trace_processor.process_with_parameters(self.params, is_preview=False)
            self.finished.emit(result)
        except Exception as e:
            print(f"Ошибка в TraceWorker: {e}")
            import traceback
            traceback.print_exc()
            self.finished.emit(None)


class MainPresenter(QObject):
    """
    Управляет логикой приложения, реагируя на действия пользователя
    и обновляя View через интерфейс IMainView.
    """

    def __init__(
        self,
        view: IMainView,
        app_settings: AppSettings,
        processor_service: ImageProcessorService,
        palette_service: PaletteService,
        trace_processor: TraceProcessor,
        text_service: TextImageService,
        export_service: ExportService,
        update_manager: UpdateManager,
        theme_manager: ThemeManager,
        available_sizes: List[RhinestoneSize]
    ):
        super().__init__()

        self.view = view
        self.app_settings = app_settings
        self.processor = processor_service
        self.palette_service = palette_service
        self.trace_processor = trace_processor
        self.text_service = text_service
        self.export_service = export_service
        self.update_manager = update_manager
        self.theme_manager = theme_manager
        self.available_sizes = available_sizes

        self._project: Optional[Project] = None
        self._image_state_manager = ImageStateManager()
        self._edit_mode = False

        self.color_popup: Optional[ColorSelectorPopup] = None
        self.size_popup: Optional[SizeSelectorPopup] = None
        self._settings_dialog: Optional[SettingsDialog] = None
        self.edit_color_popup: Optional[ColorSelectorPopup] = None
        self.add_color_popup: Optional[ColorSelectorPopup] = None

        self._allowed_colors: Optional[List[str]] = None
        self._allowed_sizes: Optional[List[str]] = None

        self._trace_dialog: Optional[TraceDialog] = None
        self._last_trace_params: Optional[TraceParameters] = None
        self._preview_thread: Optional[QThread] = None
        self._preview_worker: Optional[TraceWorker] = None
        self._final_trace_thread: Optional[QThread] = None
        self._final_trace_worker: Optional[TraceWorker] = None
        self._trace_cache = {}

        self._text_creator_dialog: Optional[TextCreatorDialog] = None
        self._image_before_text_creation = None

        self.export_thread: Optional[QThread] = None
        self.export_worker: Optional[ExportWorker] = None
        self._current_view_transform = None

        self._connect_edit_toolbar_signals()

    # --- Управление попапами тулбара ---

    def _on_edit_color_popup_closed(self):
        self.edit_color_popup = None

    def _on_add_color_popup_closed(self):
        self.add_color_popup = None

    # --- Настройки и Обновления ---

    def open_settings_dialog(self):
        if self._settings_dialog and self._settings_dialog.isVisible():
            self._settings_dialog.activateWindow()
            return
        self._settings_dialog = SettingsDialog(self.app_settings, parent=self.view)
        self._settings_dialog.check_for_updates_requested.connect(self._on_check_for_updates)
        self._settings_dialog.install_update_requested.connect(self._on_install_update)
        self.update_manager.update_check_finished.connect(self._settings_dialog.on_update_check_finished)
        self.update_manager.update_progress.connect(
            lambda p: self._settings_dialog.set_update_progress(p, f"Загрузка: {p}%"))
        self.update_manager.update_process_finished.connect(self._on_update_process_finished)
        self._settings_dialog.exec_()

    def _on_check_for_updates(self):
        if self._settings_dialog:
            self._settings_dialog.set_checking_for_updates(True)
        self.update_manager.check_for_updates()

    def _on_install_update(self, update_info):
        self.update_manager.start_update(update_info)
        if self._settings_dialog:
            self._settings_dialog.set_update_progress(0, "Подготовка к загрузке...")

    def _on_update_process_finished(self, success, message):
        if self._settings_dialog:
            self._settings_dialog.set_update_progress(100, message)
        if success and "Перезапуск" in message:
            QApplication.instance().quit()
        if not success:
            self.view.show_error("Ошибка обновления", message)

    # --- Операции с изображением ---

    def _on_change_canvas_background(self):
        initial_color = self.view.photo_viewer.scene().backgroundBrush().color()
        color = QColorDialog.getColor(initial_color, self.view, "Выберите цвет фона")
        if color.isValid():
            self.view.set_canvas_background(color)

    def mirror_image(self):
        if not self._image_state_manager.get_original_image():
            checkbox = self.view.settings_panel.check_mirror
            checkbox.setChecked(not checkbox.isChecked())
            return

        mirrored_image = self._image_state_manager.mirror_original_image()
        if not mirrored_image:
            return

        settings = self.view.get_processing_settings()
        if not settings:
            self.view.show_error("Ошибка", "Не удалось получить настройки для отзеркаливания.")
            return

        if self._project and self._project.rhinestones:
            canvas_width = settings.output.width_px
            from core.models import Point
            for r in self._project.rhinestones:
                r.position = Point(x=(canvas_width - r.position.x), y=r.position.y)
            if self._edit_mode:
                self.view.editable_canvas.load_project(self._project, settings.output)
            else:
                self.view.update_project_preview(self._project, settings.output, preserve_view=True)
        else:
            self.view.display_image(mirrored_image, settings.output, preserve_view=True)
            self._project = None
            self.view.set_edit_button_enabled(False)
            self.view.set_export_button_enabled(False)

        if self._edit_mode:
            self.view.editable_canvas.update_canvas_bounds(settings.output)
        else:
            self.view.photo_viewer.update_canvas_bounds(settings.output)

    def process_image(self):
        if not self._image_state_manager.can_trace():
            self.view.show_error("Ошибка", "Пожалуйста, сначала выберите изображение.")
            return

        settings = self.view.get_processing_settings()
        if not settings:
            self.view.show_error("Ошибка", "Не удалось получить настройки обработки.")
            return

        is_update = self._project is not None
        self.view.show_progress("Идет обработка...")

        try:
            current_image = self._image_state_manager.get_current_image()
            if not current_image:
                raise ValueError("Не удалось получить текущее изображение.")

            settings.allowed_colors = self._allowed_colors
            settings.allowed_sizes = self._allowed_sizes

            self._project = self.processor.process(current_image, settings)

            if not self._project or not self._project.rhinestones:
                self.view.show_info("Результат", "Не найдено точек для создания макета. Попробуйте изменить настройки.")
                return

            self.view.photo_viewer.update_canvas_bounds(settings.output)
            self.view.update_project_preview(self._project, settings.output, preserve_view=is_update)
            self.view.update_color_report(self._project)
            self.view.set_edit_button_enabled(True)
            self.view.set_export_button_enabled(True)
            self.view.left_toolbar.btn_trace.setEnabled(False)

        except Exception as e:
            self.view.show_error("Критическая ошибка", f"Произошла ошибка во время обработки:\n{e}")
            import traceback
            traceback.print_exc()
        finally:
            self.view.hide_progress()

    def load_image(self):
        path = self.view.get_source_image_path()
        if not path:
            return

        self.view.show_progress("Загрузка изображения...")
        try:
            if self._image_state_manager.load_original_image(path):
                self._project = None
                image = self._image_state_manager.get_current_image()
                processing_settings = self.view.get_processing_settings()
                if image and processing_settings:
                    self.view.display_image(image, processing_settings.output)
                    self.view.set_edit_button_enabled(False)
                    self.view.set_export_button_enabled(False)
                    self.view.settings_panel.check_mirror.setChecked(False)
                    self.view.left_toolbar.btn_trace.setEnabled(True)
                elif not processing_settings:
                    self.view.show_error("Ошибка", "Не удалось получить настройки холста.")
            else:
                self.view.show_error("Ошибка", f"Не удалось загрузить изображение по пути:\n{path}")
        finally:
            self.view.hide_progress()

    # --- Режим редактирования ---

    def toggle_edit_mode(self):
        if not self._project:
            self.view.show_error("Ошибка", "Нет проекта для редактирования.")
            return

        settings = self.view.get_processing_settings()
        if not settings:
            self.view.show_error("Ошибка", "Не удалось получить настройки для редактирования.")
            return

        self._edit_mode = not self._edit_mode

        if self._edit_mode:
            self.view.set_ui_mode('edit')
            self.view.editable_canvas.load_project(self._project, settings.output)
            self._setup_edit_toolbar_defaults()
        else:
            self._clear_edit_mode_state()
            self.view.set_ui_mode('view')
            self.view.update_project_preview(self._project, settings.output)

    def _clear_edit_mode_state(self):
        if hasattr(self.view, 'editable_canvas'):
            self.view.editable_canvas._scene.clearSelection()
            for item in self.view.editable_canvas._rhinestone_items:
                item.disable_interaction()
            self.view.editable_canvas._move_start_positions.clear()
            self.view.editable_canvas._any_item_moved = False
            if self.view.editable_canvas._move_timer.isActive():
                self.view.editable_canvas._move_timer.stop()
        if hasattr(self.view, 'edit_toolbar'):
            self.view.edit_toolbar.update_selection([])

    def _connect_edit_toolbar_signals(self):
        toolbar = self.view.edit_toolbar
        toolbar.changeSelectedColor.connect(self._on_change_selected_color)
        toolbar.changeSelectedSize.connect(self._on_change_selected_size)
        toolbar.selectAll.connect(self._on_select_all)
        toolbar.clearSelection.connect(self._on_clear_selection)
        toolbar.selectByColor.connect(self._on_select_by_color)
        toolbar.selectBySize.connect(self._on_select_by_size)
        toolbar.additionModeToggled.connect(self._on_addition_mode_toggled)
        toolbar.additionColorChangeRequested.connect(self._on_addition_color_change_requested)
        toolbar.additionSizeChangeRequested.connect(self._on_addition_size_change_requested)
        if hasattr(self.view, 'editable_canvas'):
            self.view.editable_canvas.selectionChanged.connect(self._on_canvas_selection_changed)

    def _on_canvas_selection_changed(self, selected_indices: List[int]):
        if not self._project:
            return
        selected_rhinestones = [
            self._project.rhinestones[i] for i in selected_indices if 0 <= i < len(self._project.rhinestones)
        ]
        self.view.edit_toolbar.update_selection(selected_rhinestones)
        color_button = self.view.edit_toolbar.color_change_button
        self._update_color_button_style(color_button, selected_rhinestones)

    def _update_color_button_style(self, button: QPushButton, rhinestones: List[Rhinestone]):
        button.setProperty("colorState", "none")
        button.setStyleSheet("")
        if rhinestones:
            unique_colors = {r.color for r in rhinestones}
            if len(unique_colors) > 1:
                button.setProperty("colorState", "mixed")
            elif len(unique_colors) == 1:
                selected_color = unique_colors.pop()
                rgb = selected_color.color
                hex_color = f"#{rgb.r:02x}{rgb.g:02x}{rgb.b:02x}"
                brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000
                text_color = "#000000" if brightness > 128 else "#FFFFFF"
                button.setStyleSheet(f"""
                    QPushButton#colorDisplayButton {{
                        background-color: {hex_color};
                        color: {text_color};
                        border: 1px solid rgba(255, 255, 255, 0.5);
                    }}
                    QPushButton#colorDisplayButton:hover {{
                        border: 1px solid #FFFFFF;
                    }}
                """)
                return
        button.style().unpolish(button)
        button.style().polish(button)

    def _on_change_selected_color(self):
        if self.edit_color_popup and self.edit_color_popup.isVisible():
            self.edit_color_popup.close()
            return
        if not hasattr(self.view, 'editable_canvas') or not self.view.editable_canvas.get_selected_rhinestones():
            self.view.show_info("Информация", "Сначала выберите стразы для изменения цвета.")
            return
        trigger_widget = self.view.edit_toolbar.color_change_button
        self.edit_color_popup = ColorSelectorPopup(
            palette=self.palette_service.get_palette(),
            palette_service=self.palette_service,
            single_selection_mode=True,
            parent=self.view
        )
        pos = trigger_widget.mapToGlobal(
            QPoint((trigger_widget.width() - self.edit_color_popup.width()) // 2 - 120, trigger_widget.height()))
        self.edit_color_popup.colorSelected.connect(lambda color: self._apply_color_to_selected(color))
        self.edit_color_popup.closed.connect(self._on_edit_color_popup_closed)
        self.edit_color_popup.show_at(pos)

    def _on_change_selected_size(self):
        if not hasattr(self.view, 'editable_canvas') or not self.view.editable_canvas.get_selected_rhinestones():
            self.view.show_info("Информация", "Сначала выберите стразы для изменения размера.")
            return
        trigger_widget = self.view.edit_toolbar.size_change_button
        size_popup = SizeSelectorPopup(
            available_sizes=self.available_sizes,
            theme_manager=self.theme_manager,
            single_selection_mode=True,
            parent=self.view
        )
        pos = trigger_widget.mapToGlobal(
            QPoint((trigger_widget.width() - size_popup.width()) // 2 - 120, trigger_widget.height()))
        size_popup.sizeSelected.connect(lambda size: self._apply_size_to_selected(size))
        size_popup.show_at(pos)

    def _apply_color_to_selected(self, new_color: 'PaletteColor'):
        if not hasattr(self.view, 'editable_canvas') or not self._project:
            return
        selected_indices = self.view.editable_canvas.get_selected_indices()
        if not selected_indices:
            return
        from core.commands import ChangeRhinestoneColorCommand
        command = ChangeRhinestoneColorCommand(self._project, selected_indices, new_color)
        self.view.editable_canvas.command_manager.execute_command(command)
        self.view.editable_canvas._smart_sync_after_command(selected_indices)
        self.view.editable_canvas._update_project_report()
        self.view.editable_canvas.projectModified.emit(self._project)
        self._on_canvas_selection_changed(selected_indices)

    def _apply_size_to_selected(self, new_size: 'RhinestoneSize'):
        if not hasattr(self.view, 'editable_canvas') or not self._project:
            return
        selected_indices = self.view.editable_canvas.get_selected_indices()
        if not selected_indices:
            return
        from core.commands import ChangeRhinestoneSizeCommand
        command = ChangeRhinestoneSizeCommand(self._project, selected_indices, new_size)
        self.view.editable_canvas.command_manager.execute_command(command)
        self.view.editable_canvas._smart_sync_after_command(selected_indices)
        self.view.editable_canvas._update_project_report()
        self.view.editable_canvas.projectModified.emit(self._project)

    def _on_select_all(self):
        if hasattr(self.view, 'editable_canvas'):
            scene = self.view.editable_canvas._scene
            scene.blockSignals(True)
            for item in self.view.editable_canvas._rhinestone_items:
                item.setSelected(True)
            scene.blockSignals(False)
            self.view.editable_canvas._on_selection_changed()

    def _on_clear_selection(self):
        if hasattr(self.view, 'editable_canvas'):
            self.view.editable_canvas._scene.clearSelection()

    def _on_select_by_color(self):
        if not hasattr(self.view, 'editable_canvas') or not self._project:
            return
        selected_rhinestones = self.view.editable_canvas.get_selected_rhinestones()
        if not selected_rhinestones:
            self.view.show_info("Информация", "Сначала выберите страз с нужным цветом.")
            return
        target_color_name = selected_rhinestones[0].color.name
        scene = self.view.editable_canvas._scene
        scene.blockSignals(True)
        scene.clearSelection()
        for item in self.view.editable_canvas._rhinestone_items:
            if item.rhinestone.color.name == target_color_name:
                item.setSelected(True)
        scene.blockSignals(False)
        self.view.editable_canvas._on_selection_changed()

    def _on_select_by_size(self):
        if not hasattr(self.view, 'editable_canvas') or not self._project:
            return
        selected_rhinestones = self.view.editable_canvas.get_selected_rhinestones()
        if not selected_rhinestones:
            self.view.show_info("Информация", "Сначала выберите страз с нужным размером.")
            return
        target_size_name = selected_rhinestones[0].size.name
        scene = self.view.editable_canvas._scene
        scene.blockSignals(True)
        scene.clearSelection()
        for item in self.view.editable_canvas._rhinestone_items:
            if item.rhinestone.size.name == target_size_name:
                item.setSelected(True)
        scene.blockSignals(False)
        self.view.editable_canvas._on_selection_changed()

    def _on_addition_mode_toggled(self, active: bool):
        if hasattr(self.view, 'editable_canvas'):
            self.view.editable_canvas.set_addition_mode(active)

    def _on_addition_color_change_requested(self):
        if self.add_color_popup and self.add_color_popup.isVisible():
            self.add_color_popup.close()
            return
        trigger_widget = self.view.edit_toolbar.addition_color_button
        self.add_color_popup = ColorSelectorPopup(
            palette=self.palette_service.get_palette(),
            palette_service=self.palette_service,
            single_selection_mode=True,
            parent=self.view
        )
        pos = trigger_widget.mapToGlobal(
            QPoint((trigger_widget.width() - self.add_color_popup.width()) // 2 - 120, trigger_widget.height()))
        self.add_color_popup.colorSelected.connect(self._set_addition_color)
        self.add_color_popup.closed.connect(self._on_add_color_popup_closed)
        self.add_color_popup.show_at(pos)

    def _on_addition_size_change_requested(self):
        trigger_widget = self.view.edit_toolbar.addition_size_button
        size_popup = SizeSelectorPopup(
            available_sizes=self.available_sizes,
            theme_manager=self.theme_manager,
            single_selection_mode=True,
            parent=self.view
        )
        pos = trigger_widget.mapToGlobal(
            QPoint((trigger_widget.width() - size_popup.width()) // 2 - 120, trigger_widget.height()))
        size_popup.sizeSelected.connect(self._set_addition_size)
        size_popup.show_at(pos)

    def _set_addition_color(self, color: 'PaletteColor'):
        self.view.edit_toolbar.set_addition_color(color)
        if hasattr(self.view, 'editable_canvas'):
            self.view.editable_canvas.set_addition_color(color)
        button = self.view.edit_toolbar.addition_color_button
        rgb = color.color
        hex_color = f"#{rgb.r:02x}{rgb.g:02x}{rgb.b:02x}"
        brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000
        text_color = "#000000" if brightness > 128 else "#FFFFFF"
        button.setStyleSheet(f"""
            QPushButton#colorDisplayButton {{
                background-color: {hex_color};
                color: {text_color};
                border: 1px solid rgba(255, 255, 255, 0.5);
            }}
            QPushButton#colorDisplayButton:hover {{
                border: 1px solid #FFFFFF;
            }}
        """)

    def _set_addition_size(self, size: 'RhinestoneSize'):
        self.view.edit_toolbar.set_addition_size(size)
        if hasattr(self.view, 'editable_canvas'):
            self.view.editable_canvas.set_addition_size(size)

    def _setup_edit_toolbar_defaults(self):
        if self.palette_service.get_palette():
            default_color = self.palette_service.get_palette()[0]
            self._set_addition_color(default_color)
        default_size = next((s for s in self.available_sizes if s.name == "SS16"),
                            self.available_sizes[0] if self.available_sizes else None)
        if default_size:
            self._set_addition_size(default_size)

    # --- Управление палитрой и размерами ---

    def open_palette_dialog(self):
        if self.color_popup and self.color_popup.isVisible():
            self.color_popup.close()
            return
        trigger_widget = self.view.left_toolbar.btn_palette
        palette = self.palette_service.get_palette()
        self.color_popup = ColorSelectorPopup(
            palette=palette,
            palette_service=self.palette_service,
            parent=self.view
        )
        self.color_popup.set_selected_colors(self._allowed_colors or [])
        self.color_popup.selectionChanged.connect(self._on_allowed_colors_changed)
        self.color_popup.paletteChanged.connect(self._on_palette_updated)
        pos = trigger_widget.mapToGlobal(QPoint(trigger_widget.width() + 5, 0))
        self.color_popup.show_at(pos)

    def _on_allowed_colors_changed(self, color_names: List[str]):
        self._allowed_colors = color_names if color_names else None

    def _on_palette_updated(self):
        if self._project and not self._edit_mode:
            self.view.update_color_report(self._project)

    def open_sizes_dialog(self):
        if self.size_popup and self.size_popup.isVisible():
            self.size_popup.close()
            return
        trigger_widget = self.view.left_toolbar.btn_sizes
        self.size_popup = SizeSelectorPopup(
            available_sizes=self.available_sizes,
            theme_manager=self.theme_manager,
            parent=self.view
        )
        self.size_popup.set_selected_sizes(self._allowed_sizes or [])
        self.size_popup.selectionChanged.connect(self._on_allowed_sizes_changed)
        pos = trigger_widget.mapToGlobal(QPoint(trigger_widget.width() + 5, 0))
        self.size_popup.show_at(pos)

    def _on_allowed_sizes_changed(self, size_names: List[str]):
        self._allowed_sizes = size_names if size_names else None

    # --- Экспорт ---

    def export_project(self):
        if not self._project:
            self.view.show_error("Ошибка", "Нет проекта для экспорта.")
            return
        processing_settings = self.view.get_processing_settings()
        if not processing_settings:
            return
        dialog = ExportDialog(self.export_service, self.view)
        if dialog.exec_() == QDialog.Accepted:
            export_settings = dialog.get_settings()
            format_name = export_settings.format.name
            file_count = len(self._project.rhinestones)
            self.view.show_progress(f"Экспорт {file_count} стразов в {format_name}...")
            self.export_thread = QThread()
            self.export_worker = ExportWorker(
                self.export_service,
                self._project,
                processing_settings.output,
                export_settings
            )
            self.export_worker.moveToThread(self.export_thread)
            self.export_thread.started.connect(self.export_worker.run)
            self.export_worker.finished.connect(self._on_export_finished)
            self.export_thread.setPriority(QThread.HighPriority)
            self.export_thread.start()

    def _on_export_finished(self, success: bool, message: str):
        self.view.hide_progress()
        if success:
            import os
            file_size = os.path.getsize(message) if os.path.exists(message) else 0
            size_mb = file_size / (1024 * 1024)
            self.view.show_info(
                "Экспорт завершен",
                f"Файл успешно сохранен:\n{message}\n\nРазмер: {size_mb:.2f} МБ"
            )
        else:
            self.view.show_error("Ошибка экспорта", message)
        if self.export_thread:
            self.export_thread.quit()
            self.export_thread.wait(500)
            self.export_thread = None
            self.export_worker = None

    # --- Создание текста ---

    def create_text_layout(self):
        if self._image_state_manager.get_original_image() or self._project:
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self.view,
                'Подтверждение',
                'Это действие очистит текущее изображение или проект. Продолжить?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        self._image_before_text_creation = self._image_state_manager.get_current_image()
        dialog = TextCreatorDialog(self.text_service, self.view)
        dialog.settings_changed.connect(self.on_text_preview_update)
        dialog.creation_confirmed.connect(self.on_text_settings_confirmed)
        dialog.cancelled.connect(self.on_text_creation_cancelled)
        dialog.exec_()

    def on_text_preview_update(self, settings: TextLayoutSettings):
        if not self.view:
            return
        preview_image = self.text_service.generate_text_image(settings)
        temp_output = OutputSettings(
            width_mm=settings.canvas_width_mm,
            height_mm=settings.canvas_height_mm,
            dpi=settings.dpi
        )
        self.view.display_image(preview_image, temp_output, preserve_view=True)

    def on_text_settings_confirmed(self, settings: TextLayoutSettings):
        self.view.show_progress("Создание текстового макета...")
        try:
            self.view.set_output_dimensions(int(settings.canvas_width_mm), int(settings.canvas_height_mm))
            if hasattr(self.view, 'settings_panel'):
                self.view.settings_panel.spin_dpi.setValue(settings.dpi)
            text_image = self.text_service.generate_text_image(settings)
            self._image_state_manager.load_original_image_from_pil(text_image)
            image_to_display = self._image_state_manager.get_current_image()
            if image_to_display:
                output_settings = OutputSettings(
                    width_mm=int(settings.canvas_width_mm),
                    height_mm=int(settings.canvas_height_mm),
                    dpi=settings.dpi
                )
                self.view.display_image(image_to_display, output_settings)
                self._project = None
                self.view.set_edit_button_enabled(False)
                self.view.set_export_button_enabled(False)
        except Exception as e:
            self.view.show_error("Ошибка", f"Не удалось создать макет из текста: {e}")
        finally:
            self.view.hide_progress()
            if self._text_creator_dialog:
                self._text_creator_dialog.close()

    def on_text_creation_cancelled(self):
        processing_settings = self.view.get_processing_settings()
        if self._image_before_text_creation:
            self.view.display_image(
                self._image_before_text_creation,
                processing_settings.output if processing_settings else None
            )
        else:
            self.view.photo_viewer.clear()

    # --- Трассировка ---

    def open_trace_dialog(self):
        if not self._image_state_manager.can_trace():
            self.view.show_error("Ошибка", "Сначала загрузите изображение.")
            return
        if self._trace_dialog and self._trace_dialog.isVisible():
            self._trace_dialog.activateWindow()
            return
        if self._trace_dialog:
            self._trace_dialog.close()
        self._stop_current_trace_processing()
        original_image = self._image_state_manager.get_original_image()
        if not original_image:
            self.view.show_error("Ошибка", "Не удалось получить оригинальное изображение.")
            return
        self.trace_processor.set_source_image(original_image)
        self._trace_cache.clear()
        self._trace_dialog = TraceDialog(self.view)
        if self._last_trace_params:
            self._trace_dialog.set_parameters(self._last_trace_params)
        else:
            self._trace_dialog.set_parameters(TraceParameters())
        self._trace_dialog.preview_requested.connect(self._on_trace_preview_requested)
        self._trace_dialog.trace_confirmed.connect(self._on_trace_confirmed)
        self._trace_dialog.trace_cancelled.connect(self._on_trace_cancelled)
        trigger_widget = self.view.left_toolbar.btn_trace
        pos = trigger_widget.mapToGlobal(QPoint(trigger_widget.width() + 5, 0))
        self._trace_dialog.show_at(pos)

    def _on_trace_preview_requested(self, params: TraceParameters):
        self._stop_current_trace_processing()
        self._current_view_transform = self.view.photo_viewer.transform()
        original_image = self._image_state_manager.get_original_image()
        if not original_image:
            return
        self.trace_processor.set_source_image(original_image)
        params_key = tuple(vars(params).values())
        if params_key in self._trace_cache:
            processing_settings = self.view.get_processing_settings()
            self.view.display_image(
                self._trace_cache[params_key],
                processing_settings.output if processing_settings else None,
                preserve_view=True
            )
            return
        self._preview_thread = QThread()
        self._preview_worker = TraceWorker(self.trace_processor, params, is_for_display=True)
        self._preview_worker.moveToThread(self._preview_thread)
        self._preview_thread.started.connect(self._preview_worker.run)
        self._preview_worker.finished.connect(lambda img: self._on_trace_preview_ready(img, params_key))
        self._preview_worker.finished.connect(self._preview_thread.quit)
        self._preview_thread.finished.connect(self._preview_thread.deleteLater)
        self._preview_thread.start()

    def _on_trace_preview_ready(self, preview_image, params_key):
        """Отображает готовое превью трассировки."""
        if preview_image:
            if len(self._trace_cache) >= 5:
                del self._trace_cache[next(iter(self._trace_cache))]
            self._trace_cache[params_key] = preview_image.copy()

            processing_settings = self.view.get_processing_settings()
            self.view.display_image(
                preview_image,
                processing_settings.output if processing_settings else None,
                preserve_view=True
            )
            if self._current_view_transform:
                self.view.photo_viewer.setTransform(self._current_view_transform)

        # ИСПРАВЛЕНИЕ: Не вызываем cleanup из тела сигнала потока!
        # Используем QTimer чтобы cleanup произошёл в главном потоке
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self._cleanup_preview_thread)

    def _on_trace_confirmed(self, params: TraceParameters):
        self._last_trace_params = params
        self._stop_current_trace_processing()
        self.view.show_progress("Применение трассировки...")
        self._final_trace_thread = QThread()
        self._final_trace_worker = TraceWorker(self.trace_processor, params, is_for_display=False)
        self._final_trace_worker.moveToThread(self._final_trace_thread)
        self._final_trace_thread.started.connect(self._final_trace_worker.run)
        # Thread tugagach worker va thread ni xavfsiz o'chirish
        self._final_trace_worker.finished.connect(self._on_final_trace_ready)
        self._final_trace_worker.finished.connect(self._final_trace_thread.quit)
        self._final_trace_thread.finished.connect(self._final_trace_thread.deleteLater)
        self._final_trace_thread.start()
        if self._trace_dialog:
            self._trace_dialog.close()
            self._trace_dialog = None

    def _on_final_trace_ready(self, final_image):
        """Обрабатывает готовое финальное изображение после трассировки."""
        self.view.hide_progress()
        if final_image:
            self._image_state_manager.apply_trace(final_image)
            processing_settings = self.view.get_processing_settings()
            self.view.display_image(
                final_image,
                processing_settings.output if processing_settings else None,
                preserve_view=True
            )
            self._project = None
            self.view.set_edit_button_enabled(False)
            self.view.set_export_button_enabled(False)
        else:
            self.view.show_error("Ошибка", "Не удалось применить трассировку.")

        # ИСПРАВЛЕНИЕ: cleanup главном потоке орқали
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self._cleanup_final_trace_thread)

    def _extract_dominant_colors_from_image(self, image, max_colors: int) -> list:
        """Трассировка rasmidan dominant ranglarni topib palitrada moslaydi."""
        try:
            quantized = image.quantize(colors=max_colors, method=0, dither=0)
            palette_raw = quantized.getpalette()
            matched_color_names = []
            for i in range(max_colors):
                r = palette_raw[i * 3]
                g = palette_raw[i * 3 + 1]
                b = palette_raw[i * 3 + 2]
                if r >= 250 and g >= 250 and b >= 250:
                    continue
                from core.models import RGBColor
                color = RGBColor(r, g, b)
                nearest = self.palette_service.find_nearest(color, None)
                if nearest and nearest.name not in matched_color_names:
                    matched_color_names.append(nearest.name)
            return matched_color_names if matched_color_names else None
        except Exception as e:
            print(f"Ошибка при извлечении цветов трассировки: {e}")
            return None

    def _on_trace_cancelled(self):
        self._stop_current_trace_processing()
        self._trace_cache.clear()
        original_image = self._image_state_manager.get_original_image()
        if original_image:
            self._image_state_manager.reset_trace()
            processing_settings = self.view.get_processing_settings()
            self.view.display_image(
                original_image,
                processing_settings.output if processing_settings else None,
                preserve_view=True
            )
        if hasattr(self.trace_processor, 'reset'):
            self.trace_processor.reset()
        if self._trace_dialog:
            self._trace_dialog.close()
            self._trace_dialog = None

    def _stop_current_trace_processing(self):
        self._cleanup_preview_thread()
        self._cleanup_final_trace_thread()

    def _cleanup_preview_thread(self):
        """Очищает поток обработки превью."""
        if hasattr(self, '_preview_thread') and self._preview_thread:
            if self._preview_thread.isRunning():
                self._preview_thread.quit()
                self._preview_thread.wait(3000)
            self._preview_thread = None
            self._preview_worker = None

    def _cleanup_final_trace_thread(self):
        """Очищает поток финальной трассировки."""
        if hasattr(self, '_final_trace_thread') and self._final_trace_thread:
            if self._final_trace_thread.isRunning():
                self._final_trace_thread.quit()
                self._final_trace_thread.wait(3000)
            self._final_trace_thread = None
            self._final_trace_worker = None

    def cleanup(self):
        """
        Главный метод очистки — вызывается при закрытии приложения.
        Останавливает все активные потоки чтобы избежать краша.
        """
        print("MainPresenter: начало очистки ресурсов...")

        # 1. Останавливаем все trace потоки
        self._stop_current_trace_processing()

        # 2. Останавливаем export поток
        if self.export_thread and self.export_thread.isRunning():
            self.export_thread.quit()
            self.export_thread.wait(2000)
            self.export_thread = None
            self.export_worker = None

        # 3. Закрываем открытые диалоги
        if self._trace_dialog:
            self._trace_dialog.close()
            self._trace_dialog = None

        if self._settings_dialog:
            self._settings_dialog.close()
            self._settings_dialog = None

        print("MainPresenter: очистка завершена.")

    def _cleanup_final_trace_thread(self):
        if hasattr(self, '_final_trace_thread') and self._final_trace_thread:
            if self._final_trace_thread.isRunning():
                self._final_trace_thread.quit()
                self._final_trace_thread.wait(3000)
            self._final_trace_thread.deleteLater()
            self._final_trace_thread = None
            self._final_trace_worker = None