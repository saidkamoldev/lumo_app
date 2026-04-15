# # core/services/palette_service.py
# # Сервис для работы с палитрой цветов. (Исправленная версия)

# import json
# from typing import List, Dict, Any, Optional

# from ..models import PaletteColor, RGBColor


# class PaletteService:
#     """Управляет загрузкой и сохранением палитры цветов."""

#     def __init__(self, colors_filepath: str = "resources/colors.json"):
#         self.filepath = colors_filepath
#         self._palette: List[PaletteColor] = []
#         # --- ИЗМЕНЕНИЕ: Формат по умолчанию теперь тоже список объектов ---
#         self._default_palette_data = [
#             {"name": "Crystal", "color": {"r": 255, "g": 255, "b": 255}},
#             {"name": "Jet", "color": {"r": 0, "g": 0, "b": 0}},
#             {"name": "Siam", "color": {"r": 227, "g": 22, "b": 45}}
#         ]

#     def load_palette(self) -> List[PaletteColor]:
#         """Загружает палитру из JSON-файла (формат: список объектов)."""
#         palette_data = []
#         try:
#             with open(self.filepath, 'r', encoding='utf-8') as f:
#                 palette_data = json.load(f)
#         except (FileNotFoundError, json.JSONDecodeError):
#             print(f"Файл {self.filepath} не найден или поврежден. Создаю новый.")
#             palette_data = self._default_palette_data
#             self.save_palette_data(palette_data)

#         self._palette = []
#         # --- ИСПРАВЛЕНИЕ: Итерируемся по списку словарей ---
#         for item in palette_data:
#             color_dict = item.get('color', {})
#             color = RGBColor(r=color_dict.get('r', 0), g=color_dict.get('g', 0), b=color_dict.get('b', 0))
#             self._palette.append(PaletteColor(name=item.get('name', 'Unknown'), color=color))

#         return self._palette

#     def save_palette(self, palette: List[PaletteColor]):
#         """Сохраняет палитру в JSON (формат: список объектов)."""
#         self._palette = palette
#         # --- ИСПРАВЛЕНИЕ: Сохраняем как список словарей ---
#         palette_data: List[Dict[str, Any]] = []
#         for p_color in self._palette:
#             palette_data.append({
#                 'name': p_color.name,
#                 'color': {'r': p_color.color.r, 'g': p_color.color.g, 'b': p_color.color.b}
#             })
#         self.save_palette_data(palette_data)

#     def save_palette_data(self, palette_data: List[Dict[str, Any]]):
#         """Вспомогательный метод для записи данных в файл."""
#         try:
#             with open(self.filepath, 'w', encoding='utf-8') as f:
#                 json.dump(palette_data, f, indent=4, ensure_ascii=False)
#         except IOError as e:
#             print(f"Ошибка сохранения палитры: {e}")

#     def get_palette(self) -> List[PaletteColor]:
#         """Возвращает загруженную палитру."""
#         if not self._palette:
#             self.load_palette()
#         return self._palette

#     def find_nearest(self, target_color: RGBColor, allowed_names: Optional[List[str]] = None) -> Optional[PaletteColor]:
#         """Находит ближайший цвет из палитры с учетом ограничений."""
#         search_palette = self.get_palette()
#         if allowed_names:
#             search_palette = [p for p in search_palette if p.name in allowed_names]
#         if not search_palette: return None

#         return min(search_palette, key=lambda p: (
#                 (target_color.r - p.color.r) ** 2 +
#                 (target_color.g - p.color.g) ** 2 +
#                 (target_color.b - p.color.b) ** 2
#         ))

#     @staticmethod
#     def get_contrasting_color(background: RGBColor) -> RGBColor:
#         luminance = 0.299 * background.r + 0.587 * background.g + 0.114 * background.b
#         return RGBColor(255, 255, 255) if luminance < 128 else RGBColor(0, 0, 0)
import json
import os
import sys
from typing import List, Dict, Any, Optional
from ..models import PaletteColor, RGBColor

def resource_path(relative_path):
    """ PyInstaller uchun resurs yo'lini aniqlash """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class PaletteService:
    def __init__(self, colors_filepath: str = "resources/colors.json"):
        # resource_path qo'shildi
        self.filepath = resource_path(colors_filepath)
        self._palette: List[PaletteColor] = []
        self._default_palette_data = [
            {"name": "Crystal", "color": {"r": 255, "g": 255, "b": 255}},
            {"name": "Jet", "color": {"r": 0, "g": 0, "b": 0}},
            {"name": "Siam", "color": {"r": 227, "g": 22, "b": 45}}
        ]

    def load_palette(self) -> List[PaletteColor]:
        palette_data = []
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                palette_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            palette_data = self._default_palette_data
        
        self._palette = []
        for item in palette_data:
            color_dict = item.get('color', {})
            color = RGBColor(r=color_dict.get('r', 0), g=color_dict.get('g', 0), b=color_dict.get('b', 0))
            self._palette.append(PaletteColor(name=item.get('name', 'Unknown'), color=color))
        return self._palette

    def save_palette_data(self, palette_data: List[Dict[str, Any]]):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(palette_data, f, indent=4, ensure_ascii=False)
        except IOError:
            pass

    def get_palette(self) -> List[PaletteColor]:
        if not self._palette:
            self.load_palette()
        return self._palette

    def find_nearest(self, target_color: RGBColor, allowed_names: Optional[List[str]] = None) -> Optional[PaletteColor]:
        search_palette = self.get_palette()
        if allowed_names:
            search_palette = [p for p in search_palette if p.name in allowed_names]
        if not search_palette: return None
        return min(search_palette, key=lambda p: ((target_color.r - p.color.r)**2 + (target_color.g - p.color.g)**2 + (target_color.b - p.color.b)**2))

    @staticmethod
    def get_contrasting_color(background: RGBColor) -> RGBColor:
        luminance = 0.299 * background.r + 0.587 * background.g + 0.114 * background.b
        return RGBColor(255, 255, 255) if luminance < 128 else RGBColor(0, 0, 0)