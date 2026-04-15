# core/models.py
# Единый файл для всех моделей данных и структур приложения.

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum, auto

from PyQt5.QtGui import QColor

@dataclass
class UpdateInfoResponse:
    """Ответ от сервера с информацией об обновлении."""
    update_available: bool
    version: Optional[str] = None
    forced_update: bool = False
    notes: Optional[str] = None
    release_date: Optional[str] = None
    file_size: int = 0
    file_hash: Optional[str] = None

@dataclass
class AppSettings:
    """Общие настройки приложения."""
    current_version: str = "0.0.0"
    update_server_url: str = "https://lumoserver.ru/api"


# --- Базовые геометрические и цветовые модели ---

@dataclass(frozen=True)
class RGBColor:
    """Представляет цвет в формате RGB."""
    r: int
    g: int
    b: int

    def to_rgb_str(self) -> str:
        return f"rgb({self.r},{self.g},{self.b})"

    def to_qcolor(self) -> QColor:
        """Вспомогательный метод для конвертации в QColor."""
        return QColor(self.r, self.g, self.b)

    @classmethod
    def from_rgb_str(cls, rgb_str: str) -> 'RGBColor':
        """Создает объект из строки 'rgb(r,g,b)'."""
        try:
            r, g, b = map(int, rgb_str.replace('rgb(', '').replace(')', '').split(','))
            return cls(r, g, b)
        except (ValueError, IndexError):
            return cls(0, 0, 0)


@dataclass(frozen=True)
class Point:
    """Представляет точку (координаты X, Y)."""
    x: float
    y: float


# --- Модели, связанные со стразами (ПРАВИЛЬНЫЙ ПОРЯДОК) ---

@dataclass(frozen=True)
class RhinestoneSize:
    """Представляет размер страза. (Определен ДО Rhinestone)"""
    name: str
    diameter_mm: float


@dataclass(frozen=True)
class PaletteColor:
    """Представляет цвет из палитры. (Определен ДО Rhinestone)"""
    name: str
    color: RGBColor


@dataclass
class Rhinestone:
    """Представляет один страз на холсте."""
    position: Point
    color: PaletteColor  # Теперь этот класс известен
    size: RhinestoneSize  # И этот класс известен
    group_id: int = 0


# --- Модель проекта ---

@dataclass
class Project:
    """Главная модель, описывающая весь проект макета."""
    rhinestones: List[Rhinestone] = field(default_factory=list)
    report: Dict[Tuple[str, str], int] = field(default_factory=dict)
    total_count: int = 0


# --- Модели для настроек ---

@dataclass
class CanvasSettings:
    """Общие настройки для всех холстов."""
    zoom_factor: float = 1.0
    min_zoom: float = 0.05
    max_zoom: float = 50.0
    zoom_step: float = 1.15



@dataclass
class OutputSettings:
    """Настройки выходного изображения."""
    width_mm: int
    height_mm: int
    dpi: int

    @property
    def width_px(self) -> int:
        """Ширина в пикселях, рассчитанная из миллиметров и DPI."""
        # 25.4 мм = 1 дюйм
        # Используем math.floor для округления вниз
        import math
        return math.floor((self.width_mm / 25.4) * self.dpi)

    @property
    def height_px(self) -> int:
        """Высота в пикселях, рассчитанная из миллиметров и DPI."""
        import math
        return math.floor((self.height_mm / 25.4) * self.dpi)

    def get_actual_size_mm(self) -> tuple[float, float]:
        """
        Возвращает фактический размер в миллиметрах с учетом округления пикселей вниз.
        Полезно для проверки точности.
        """
        actual_width_mm = (self.width_px * 25.4) / self.dpi
        actual_height_mm = (self.height_px * 25.4) / self.dpi
        return actual_width_mm, actual_height_mm


@dataclass
class ProcessingSettings:
    """Настройки для процесса генерации макета."""
    output: OutputSettings
    spacing: float
    base_dot_size_mm: float
    contrast: float
    fill_inner_white: bool
    grid_mode: str  # "uniform" или "honeycomb"
    allowed_sizes: Optional[List[str]] = None
    allowed_colors: Optional[List[str]] = None


@dataclass
class TextLayoutSettings:
    """Настройки для генерации макета из текста."""
    text: str = "Lumo"
    font_family: str = "Arial"
    font_size: int = 100
    letter_spacing: int = 0
    text_color: RGBColor = RGBColor(0, 0, 0)
    canvas_width_mm: float = 200.0
    canvas_height_mm: float = 100.0
    dpi: int = 150
    horizontal_align: str = "center"
    vertical_align: str = "middle"


@dataclass
class TraceParameters:
    """Параметры трассировки с возможностью включения/выключения каждого эффекта."""

    # Основные параметры с включением/выключением
    algorithm: str = "artistic"

    # Постеризация (количество цветов)
    colors_enabled: bool = True
    colors: int = 8  # 0 означает "не применять постеризацию"

    # Коррекция контраста
    contrast_enabled: bool = False
    contrast: float = 1.0

    # Коррекция насыщенности
    saturation_enabled: bool = False
    saturation: float = 1.0

    # Коррекция яркости
    brightness_enabled: bool = False
    brightness: float = 1.0

    # Гамма-коррекция (новое)
    gamma_enabled: bool = False
    gamma: float = 1.0

    # Цветовая температура (новое)
    temperature_enabled: bool = False
    temperature: float = 0.0  # -1.0 до 1.0 (холодный - теплый)

    # Размытие
    blur_enabled: bool = False
    blur_type: str = "gaussian"  # gaussian, median, bilateral, motion, radial
    blur_strength: float = 1.0

    # Повышение резкости
    sharpen_enabled: bool = False
    sharpen_strength: float = 1.0  # Теперь с настраиваемой силой

    # Инверсия
    invert_enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует параметры в словарь."""
        return {
            'algorithm': self.algorithm,
            'colors_enabled': self.colors_enabled,
            'colors': self.colors,
            'contrast_enabled': self.contrast_enabled,
            'contrast': self.contrast,
            'saturation_enabled': self.saturation_enabled,
            'saturation': self.saturation,
            'brightness_enabled': self.brightness_enabled,
            'brightness': self.brightness,
            'gamma_enabled': self.gamma_enabled,
            'gamma': self.gamma,
            'temperature_enabled': self.temperature_enabled,
            'temperature': self.temperature,
            'blur_enabled': self.blur_enabled,
            'blur_type': self.blur_type,
            'blur_strength': self.blur_strength,
            'sharpen_enabled': self.sharpen_enabled,
            'sharpen_strength': self.sharpen_strength,
            'invert_enabled': self.invert_enabled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TraceParameters':
        """Создает объект из словаря."""
        # Создаем объект с значениями по умолчанию
        params = cls()

        # Обновляем только те поля, которые есть в словаре
        for key, value in data.items():
            if hasattr(params, key):
                setattr(params, key, value)

        return params

    def get_enabled_effects(self) -> List[str]:
        """Возвращает список включенных эффектов."""
        enabled = []
        if self.colors_enabled and self.colors > 0:
            enabled.append(f"Постеризация ({self.colors} цветов)")
        if self.contrast_enabled and self.contrast != 1.0:
            enabled.append(f"Контраст ({self.contrast:.2f})")
        if self.saturation_enabled and self.saturation != 1.0:
            enabled.append(f"Насыщенность ({self.saturation:.2f})")
        if self.brightness_enabled and self.brightness != 1.0:
            enabled.append(f"Яркость ({self.brightness:.2f})")
        if self.gamma_enabled and self.gamma != 1.0:
            enabled.append(f"Гамма ({self.gamma:.2f})")
        if self.temperature_enabled and self.temperature != 0.0:
            temp_desc = "теплая" if self.temperature > 0 else "холодная"
            enabled.append(f"Температура ({temp_desc})")
        if self.blur_enabled and self.blur_strength > 0:
            enabled.append(f"Размытие ({self.blur_type})")
        if self.sharpen_enabled:
            enabled.append(f"Резкость ({self.sharpen_strength:.1f})")
        if self.invert_enabled:
            enabled.append("Инверсия")

        return enabled

# --- Перечисления (Enums) для состояний и опций ---

class EditMode(Enum):
    VIEW = auto()
    EDIT = auto()


class ExportFormat(Enum):
    PNG = auto()
    JPG = auto()
    SVG = auto()


class ExportVariant(Enum):
    CLEAN = auto()
    NUMBERED = auto()
    WITH_REPORT = auto()


@dataclass
class ExportSettings:
    """Все настройки для процесса экспорта."""
    format: ExportFormat = ExportFormat.PNG
    variant: ExportVariant = ExportVariant.NUMBERED
    output_path: str = ""
    filename: str = ""
    quality: int = 95
    add_stroke: bool = False
    save_table_separately: bool = True