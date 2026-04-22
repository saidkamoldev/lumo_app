# core/services/text_service.py
# ИСПРАВЛЕННАЯ ВЕРСИЯ с работающим межбуквенным интервалом

from PIL import Image, ImageDraw, ImageFont
import os
from typing import List, Dict, Optional, Tuple

from core.models import TextLayoutSettings


class TextImageService:
    def __init__(self):
        self._font_cache: Dict[str, ImageFont.ImageFont] = {}
        self._font_files = self._scan_fonts_directory()

    def _scan_fonts_directory(self) -> Dict[str, str]:
        found_fonts = {}

        # 1. resources/fonts papkasini tekshir
        fonts_dir = "resources/fonts"
        if not os.path.exists(fonts_dir):
            os.makedirs(fonts_dir)

        for file in os.listdir(fonts_dir):
            if file.lower().endswith(('.ttf', '.otf')):
                font_name = os.path.splitext(file)[0]
                found_fonts[font_name] = os.path.join(fonts_dir, file)

        # 2. Tizim shriftlarini ham qo'sh (Linux/Windows/Mac)
        system_font_dirs = [
            "/usr/share/fonts",           # Linux
            "/usr/local/share/fonts",     # Linux
            os.path.expanduser("~/.fonts"),  # Linux user fonts
            "C:/Windows/Fonts",           # Windows
            "/System/Library/Fonts",      # macOS
            "/Library/Fonts",             # macOS
        ]

        for sys_dir in system_font_dirs:
            if os.path.exists(sys_dir):
                for root, dirs, files in os.walk(sys_dir):
                    for file in files:
                        if file.lower().endswith(('.ttf', '.otf')):
                            font_name = os.path.splitext(file)[0]
                            # resources/fonts dagi fontlar ustunlik qiladi
                            if font_name not in found_fonts:
                                found_fonts[font_name] = os.path.join(root, file)

        return found_fonts

    def get_available_fonts(self) -> List[str]:
        return sorted(list(self._font_files.keys())) if self._font_files else ["Arial"]

    def get_font_path(self, font_name: str) -> Optional[str]:
        return self._font_files.get(font_name)

    def _get_font_object(self, font_family: str, size: int) -> ImageFont.ImageFont:
        font_path = self.get_font_path(font_family)
        try:
            if font_path:
                return ImageFont.truetype(font_path, size)
            else:
                return ImageFont.truetype(f"{font_family.lower()}.ttf", size)
        except IOError:
            return ImageFont.load_default()

    # --- НОВЫЕ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ---
    def _get_text_dimensions(self, text: str, font: ImageFont.ImageFont, spacing: int) -> Tuple[int, int]:
        """Рассчитывает финальные ширину и высоту текста с учетом интервала."""
        max_width = 0
        total_height = 0

        # Получаем высоту строки из шрифта
        try:
            _, top, _, bottom = font.getbbox("A")
            line_height = bottom - top
        except AttributeError:  # Для старых версий PIL
            line_height = font.getsize("A")[1]

        lines = text.splitlines()
        for line in lines:
            # Ширина строки = сумма ширин символов + интервалы
            line_width = sum(font.getlength(char) for char in line)
            if len(line) > 1:
                line_width += (len(line) - 1) * spacing

            if line_width > max_width:
                max_width = line_width

            total_height += line_height

        return int(max_width), total_height

    def _draw_text_with_spacing(self, draw: ImageDraw.Draw, pos: Tuple[float, float], text: str,
                                font: ImageFont.ImageFont, fill: Tuple[int, int, int], spacing: int):
        """Отрисовывает текст посимвольно с заданным интервалом."""
        x_start, y_start = pos

        try:
            _, top, _, bottom = font.getbbox("A")
            line_height = bottom - top
        except AttributeError:
            line_height = font.getsize("A")[1]

        current_y = y_start
        for line in text.splitlines():
            current_x = x_start
            # Рисуем каждый символ
            for char in line:
                draw.text((current_x, current_y), char, font=font, fill=fill)
                current_x += font.getlength(char) + spacing
            current_y += line_height

    def generate_text_image(self, settings: TextLayoutSettings) -> Image.Image:
        """Генерирует изображение с текстом с корректным выравниванием для каждой строки."""
        # Рассчитываем размеры изображения в пикселях из миллиметров
        width_px = int(settings.canvas_width_mm * settings.dpi / 25.4)
        height_px = int(settings.canvas_height_mm * settings.dpi / 25.4)

        final_image = Image.new('RGB', (width_px, height_px), (255, 255, 255))
        draw = ImageDraw.Draw(final_image)
        font = self._get_font_object(settings.font_family, settings.font_size)
        fill = (settings.text_color.r, settings.text_color.g, settings.text_color.b)

        if not settings.text:
            return final_image

        lines = settings.text.splitlines()

        # 1. Сначала получаем размеры всего текстового блока
        line_heights, line_widths = self._calculate_line_dimensions(lines, font, settings.letter_spacing)
        total_height = sum(line_heights)
        max_width = max(line_widths) if line_widths else 0

        # 2. Определяем стартовую Y-координату для всего блока текста
        block_y = 0
        if settings.vertical_align == 'middle':
            block_y = (height_px - total_height) / 2
        elif settings.vertical_align == 'bottom':
            block_y = height_px - total_height

        # 3. Рисуем каждую строку отдельно с правильным смещением по X
        current_y = block_y
        for i, line in enumerate(lines):
            line_width = line_widths[i]

            # Рассчитываем стартовую X-координату для ТЕКУЩЕЙ строки
            line_x = 0
            if settings.horizontal_align == 'center':
                line_x = (width_px - line_width) / 2
            elif settings.horizontal_align == 'right':
                line_x = width_px - line_width - 10

            self._draw_line_with_spacing(draw, (line_x, current_y), line, font, fill, settings.letter_spacing)

            current_y += line_heights[i]

        final_image.info['is_text_image'] = True
        return final_image

    def _calculate_line_dimensions(self, lines, font, spacing):
        """Рассчитывает высоту и ширину для каждой строки текста."""
        line_heights = []
        line_widths = []

        for line in lines:
            if line.strip():
                # Har bir satr uchun haqiqiy balandlikni hisoblash
                try:
                    bbox = font.getbbox(line)
                    line_height = bbox[3] - bbox[1]
                except AttributeError:
                    line_height = font.getsize(line)[1]
            else:
                # Bo'sh satr uchun "A" harfi balandligini ishlatamiz
                try:
                    _, top, _, bottom = font.getbbox("A")
                    line_height = bottom - top
                except AttributeError:
                    line_height = font.getsize("A")[1]

            # Satr kengligi
            if line.strip():
                line_width = sum(font.getlength(char) for char in line)
                if len(line) > 1:
                    line_width += (len(line) - 1) * spacing
            else:
                line_width = 0

            line_widths.append(int(line_width))
            line_heights.append(int(line_height * 1.2))  # 1.2 — satrlar orasiga bo'sh joy

        return line_heights, line_widths

    def _draw_line_with_spacing(self, draw, pos, line, font, fill, spacing):
        """Рисует одну строку текста посимвольно."""
        x, y = pos
        for char in line:
            draw.text((x, y), char, font=font, fill=fill)
            x += font.getlength(char) + spacing