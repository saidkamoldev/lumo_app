# app/canvas_manager.py

from typing import List
from PyQt5.QtCore import QObject
from PyQt5.QtGui import QColor

# Импорты из нового проекта
from ui.components.base_canvas import BaseCanvas
from ui.theme.theme_manager import ThemeManager


class CanvasManager(QObject):
    """
    Управляет холстами и синхронизирует их состояние (например, цвет фона)
    с глобальным менеджером тем.
    """

    def __init__(self, theme_manager: ThemeManager):
        """
        Конструктор принимает ThemeManager для подписки на его события.
        """
        super().__init__()
        self.theme_manager = theme_manager
        self._canvases: List[BaseCanvas] = []

        self.theme_manager.themeChanged.connect(self._on_theme_changed)

    def register_canvas(self, canvas: BaseCanvas):
        """
        Регистрирует холст и немедленно применяет к нему цвет текущей темы.
        """
        if canvas not in self._canvases:
            self._canvases.append(canvas)
            # Получаем текущий цвет холста из ThemeManager
            current_bg_color = self.theme_manager.get_canvas_color()
            # Применяем его к новому холсту
            self._apply_background_color(canvas, current_bg_color)
            print(f"Холст {type(canvas).__name__} зарегистрирован, тема применена.")

    def unregister_canvas(self, canvas: BaseCanvas):
        """
        Отменяет регистрацию холста.
        """
        if canvas in self._canvases:
            self._canvases.remove(canvas)
            print(f"Холст {type(canvas).__name__} отключен.")

    def _on_theme_changed(self, theme_name: str):
        """
        Слот, который вызывается при смене темы в ThemeManager.
        Обновляет фон для всех зарегистрированных холстов.
        """
        print(f"CanvasManager: получена смена темы на '{theme_name}'.")
        new_bg_color = self.theme_manager.get_canvas_color()
        for canvas in self._canvases:
            self._apply_background_color(canvas, new_bg_color)

    def _apply_background_color(self, canvas: BaseCanvas, color: QColor):
        """
        Применяет цвет фона к холсту через его собственный метод.
        Это более надежный способ, чем setStyleSheet.
        """
        canvas.setBackgroundColor(color)