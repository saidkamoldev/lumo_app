# ui/interfaces.py
# Абстрактные интерфейсы, определяющие "контракт" между слоями.

from abc import ABC, abstractmethod
from typing import List, Optional
from PIL.Image import Image
from PyQt5.QtGui import QColor

from core.models import (
    Project,
    OutputSettings,
    ProcessingSettings,
    Rhinestone
)


class IMainView(ABC):
    """
    Абстрактный интерфейс для главного окна (View).
    Определяет все действия, которые Презентер может попросить выполнить у UI.
    """

    @abstractmethod
    def display_image(self, image: Image, output_settings: Optional[OutputSettings] = None,
                      preserve_view: bool = False):
        """
        Отображает изображение. Если переданы output_settings,
        изображение будет отцентрировано относительно размеров холста.
        """
        pass

    @abstractmethod
    def update_project_preview(self, project: Project, output_settings: OutputSettings,
                               preserve_view: bool = False):
        """Обновляет предпросмотр, отображая сгенерированный макет стразов."""
        pass

    @abstractmethod
    def update_color_report(self, project: Project):
        """Обновляет панель с отчетом по цветам и размерам."""
        pass

    @abstractmethod
    def update_selection_info(self, selected_rhinestones: List[Rhinestone]):
        """Обновляет информацию в панели редактирования о выбранных стразах."""
        pass

    @abstractmethod
    def get_source_image_path(self) -> Optional[str]:
        """Открывает диалог выбора файла и возвращает путь."""
        pass

    @abstractmethod
    def get_save_folder_path(self) -> Optional[str]:
        """Открывает диалог выбора папки для сохранения и возвращает путь."""
        pass

    @abstractmethod
    def set_ui_mode(self, mode: str):
        """
        Переключает UI в определенный режим ('view' или 'edit').
        """
        pass

    @abstractmethod
    def show_progress(self, message: str):
        """Показывает индикатор выполнения задачи."""
        pass

    @abstractmethod
    def hide_progress(self):
        """Скрывает индикатор выполнения задачи."""
        pass

    @abstractmethod
    def set_edit_button_enabled(self, enabled: bool):
        """Включает/выключает кнопку 'Редактировать'."""
        pass

    @abstractmethod
    def set_export_button_enabled(self, enabled: bool):
        """Включает/выключает кнопку 'Экспорт'."""
        pass

    @abstractmethod
    def show_error(self, title: str, message: str):
        """Показать диалоговое окно с ошибкой."""
        pass

    @abstractmethod
    def show_info(self, title: str, message: str):
        """Показать информационное диалоговое окно."""
        pass

    @abstractmethod
    def get_processing_settings(self) -> Optional[ProcessingSettings]:
        """
        Собирает все настройки обработки с виджетов и возвращает в виде объекта.
        """
        pass

    @abstractmethod
    def set_output_dimensions(self, width_mm: int, height_mm: int):
        """Устанавливает значения в полях для ширины и высоты вывода."""
        pass

    @abstractmethod
    def set_canvas_background(self, color: QColor):
        """Устанавливает цвет фона для холстов."""
        pass