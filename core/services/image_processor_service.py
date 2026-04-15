# core/services/image_processor_service.py
import math
from collections import deque
from typing import List, Optional

import numpy as np
from PIL import Image, ImageEnhance

from .palette_service import PaletteService
from ..models import RhinestoneSize, ProcessingSettings, Project, Rhinestone, Point, RGBColor, OutputSettings


class ImageProcessorService:
    def __init__(self, palette_service: PaletteService, available_sizes: List[RhinestoneSize]):
        self.palette_service = palette_service
        self.available_sizes = {s.name: s for s in available_sizes}

        # ИСПРАВЛЕНИЕ: Кэш для дорогих вычислений
        self._distance_map_cache = {}
        self._binary_mask_cache = {}
        self._cache_max_size = 3

    def process(self, image: Image.Image, settings: ProcessingSettings) -> Project:
        if self._is_text_image(image):
            return self._process_text_image(image, settings)
        else:
            return self._process_standard_image(image, settings)

    def _is_text_image(self, img: Image.Image) -> bool:
        """Определяет, является ли изображение текстовым, проверяя метаданные."""
        return img.info.get('is_text_image', False)

    def _prepare_image(self, img: Image.Image, settings: ProcessingSettings) -> Image.Image:
        if settings.contrast != 0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1 + settings.contrast)
        return img.convert("RGB")

    def _get_cache_key(self, img: Image.Image, contrast: float) -> str:
        """Создает ключ кэша на основе размера изображения и контраста."""
        return f"{img.size[0]}x{img.size[1]}_contrast_{contrast:.2f}"

    def _process_text_image(self, img: Image.Image, settings: ProcessingSettings) -> Project:
        """
        ИСПРАВЛЕННАЯ версия обработки текстового изображения с кэшированием дорогих операций.
        """
        print(f"Обработка текста (режим сетки: {settings.grid_mode})...")

        # 1. Подготовка изображения
        img_gray = img.convert('L')
        if settings.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img_gray)
            img_gray = enhancer.enhance(settings.contrast)

        # ИСПРАВЛЕНИЕ: Кэширование бинарной маски и карты расстояний
        cache_key = self._get_cache_key(img_gray, settings.contrast)

        if cache_key in self._binary_mask_cache:
            print("Используется кэшированная бинарная маска")
            binary_mask = self._binary_mask_cache[cache_key]
            distance_map = self._distance_map_cache[cache_key]
        else:
            print("Создание новой бинарной маски и карты расстояний...")

            # Очистка кэша если он переполнен
            if len(self._binary_mask_cache) >= self._cache_max_size:
                oldest_key = next(iter(self._binary_mask_cache))
                del self._binary_mask_cache[oldest_key]
                del self._distance_map_cache[oldest_key]

            img_array = np.array(img_gray)
            binary_mask = img_array < 250

            # ИСПРАВЛЕНИЕ: Оптимизированное вычисление карты расстояний
            from scipy import ndimage
            distance_map = ndimage.distance_transform_edt(binary_mask)

            # Сохраняем в кэш
            self._binary_mask_cache[cache_key] = binary_mask
            self._distance_map_cache[cache_key] = distance_map
            print("Бинарная маска и карта расстояний сохранены в кэш")

        max_distance = np.max(distance_map) if np.max(distance_map) > 0 else 1

        # 3. Определяем доступные размеры стразов
        available_size_names = settings.allowed_sizes if settings.allowed_sizes else list(self.available_sizes.keys())
        if not available_size_names:
            available_size_names = ["SS3", "SS5", "SS7"]

        available_size_objects = []
        for name in available_size_names:
            if name in self.available_sizes:
                available_size_objects.append(self.available_sizes[name])

        if not available_size_objects:
            available_size_objects = list(self.available_sizes.values())[:3]

        available_size_objects.sort(key=lambda s: s.diameter_mm, reverse=True)

        # 4. Определяем базовый размер страза
        largest_size = available_size_objects[0]
        smallest_size = available_size_objects[-1]

        # 5. ИСПРАВЛЕНИЕ: Оптимизированный расчет шага сетки
        diameter_px = (smallest_size.diameter_mm * settings.output.dpi / 25.4)
        base_step = diameter_px * settings.spacing
        if base_step < 1:
            base_step = 1

        # 6. ИСПРАВЛЕНИЕ: Более быстрое создание адаптивной сетки
        adaptive_grid_points = self._create_adaptive_text_grid_fast(
            binary_mask=binary_mask,
            distance_map=distance_map,
            base_step=base_step,
            mode=settings.grid_mode
        )

        if not adaptive_grid_points:
            print("Не найдено точек для создания макета из текста.")
            return Project()

        # 7. ИСПРАВЛЕНИЕ: Оптимизированное определение цвета текста
        text_color_obj = self._get_dominant_text_color_fast(img, binary_mask)

        nearest_palette_color = self.palette_service.find_nearest(
            text_color_obj, settings.allowed_colors
        )
        if not nearest_palette_color:
            print("Не удалось найти подходящий цвет в палитре для текста.")
            return Project()

        # 8. ИСПРАВЛЕНИЕ: Векторизованное создание стразов
        rhinestones = self._create_rhinestones_vectorized(
            adaptive_grid_points,
            distance_map,
            max_distance,
            available_size_objects,
            nearest_palette_color,
            binary_mask
        )

        # 9. Дополнительный проход для заполнения пропусков (если нужно)
        if len(available_size_objects) > 1 and len(rhinestones) < len(adaptive_grid_points) * 0.8:
            gap_rhinestones = self._fill_text_gaps_fast(
                binary_mask=binary_mask,
                existing_rhinestones=rhinestones,
                smallest_size=smallest_size,
                color=nearest_palette_color,
                step=base_step * 0.5
            )
            rhinestones.extend(gap_rhinestones)

        # 10. Масштабирование и центрирование
        scaled_rhinestones = self._scale_and_center_rhinestones(rhinestones, settings.output)

        # 11. Формирование отчета
        from collections import defaultdict
        report_data = defaultdict(int)
        for r in scaled_rhinestones:
            report_data[(r.color.name, r.size.name)] += 1

        project = Project(
            rhinestones=scaled_rhinestones,
            report=dict(report_data),
            total_count=len(scaled_rhinestones)
        )

        print(f"Создан текстовый проект с {len(scaled_rhinestones)} стразами разных размеров.")
        return project

    def _get_dominant_text_color_fast(self, img: Image.Image, binary_mask: np.ndarray) -> RGBColor:
        """ИСПРАВЛЕНИЕ: Быстрое определение доминирующего цвета текста."""
        # Берем только каждый 5-й пиксель для ускорения
        height, width = binary_mask.shape
        step = 5

        color_sum_r, color_sum_g, color_sum_b = 0, 0, 0
        pixel_count = 0

        for y in range(0, height, step):
            for x in range(0, width, step):
                if binary_mask[y, x]:
                    r, g, b = img.getpixel((x, y))[:3]  # Безопасное извлечение RGB
                    color_sum_r += r
                    color_sum_g += g
                    color_sum_b += b
                    pixel_count += 1

                    # Достаточно небольшой выборки для определения цвета
                    if pixel_count >= 100:
                        break
            if pixel_count >= 100:
                break

        if pixel_count == 0:
            return RGBColor(0, 0, 0)

        avg_r = color_sum_r // pixel_count
        avg_g = color_sum_g // pixel_count
        avg_b = color_sum_b // pixel_count

        return RGBColor(avg_r, avg_g, avg_b)

    def _create_adaptive_text_grid_fast(self, binary_mask, distance_map, base_step, mode):
        """ИСПРАВЛЕНИЕ: Оптимизированное создание адаптивной сетки."""
        points = []
        height, width = binary_mask.shape

        if mode == "honeycomb":
            y_step = base_step * math.sqrt(3) / 2
            if y_step == 0:
                return []

            y = 0
            row_index = 0
            while y < height:
                x_offset = (base_step / 2) if (row_index % 2 != 0) else 0
                x = x_offset
                while x < width:
                    ix, iy = int(x), int(y)
                    if 0 <= iy < height and 0 <= ix < width and binary_mask[iy, ix]:
                        # ИСПРАВЛЕНИЕ: Упрощенная логика плотности
                        distance = distance_map[iy, ix]
                        # Берем больше точек в узких местах, меньше в широких
                        if distance < 3 or (distance >= 3 and np.random.random() < 0.7):
                            points.append(Point(x, y))
                    x += base_step
                y += y_step
                row_index += 1
        else:  # uniform
            # ИСПРАВЛЕНИЕ: Векторизованная обработка для uniform режима
            y_coords = np.arange(0, height, base_step)
            x_coords = np.arange(0, width, base_step)

            for y in y_coords:
                for x in x_coords:
                    ix, iy = int(x), int(y)
                    if 0 <= iy < height and 0 <= ix < width and binary_mask[iy, ix]:
                        points.append(Point(x, y))

        print(f"Создано {len(points)} точек сетки")
        return points

    def _create_rhinestones_vectorized(self, points, distance_map, max_distance,
                                       available_sizes, color, binary_mask):
        """ИСПРАВЛЕНИЕ: Векторизованное создание стразов."""
        rhinestones = []

        # Предварительно вычисляем размеры для разных расстояний
        size_thresholds = [0.4, 0.7]  # Пороги для выбора размеров

        for point in points:
            ix, iy = int(point.x), int(point.y)

            if 0 <= iy < distance_map.shape[0] and 0 <= ix < distance_map.shape[1]:
                distance_from_edge = distance_map[iy, ix]
            else:
                distance_from_edge = 0

            # ИСПРАВЛЕНИЕ: Быстрый выбор размера
            if len(available_sizes) == 1:
                size = available_sizes[0]
            else:
                normalized_distance = distance_from_edge / max_distance if max_distance > 0 else 0

                if normalized_distance > size_thresholds[1]:
                    size = available_sizes[0]  # Большой
                elif normalized_distance > size_thresholds[0]:
                    size = available_sizes[len(available_sizes) // 2] if len(available_sizes) > 2 else available_sizes[
                        0]
                else:
                    size = available_sizes[-1]  # Маленький

            # ИСПРАВЛЕНИЕ: Упрощенная проверка столкновений
            if self._can_place_rhinestone_fast(point, size, rhinestones):
                rhinestones.append(Rhinestone(
                    position=point,
                    size=size,
                    color=color
                ))

        return rhinestones

    def _can_place_rhinestone_fast(self, point, size, existing_rhinestones):
        """ИСПРАВЛЕНИЕ: Быстрая проверка возможности размещения страза."""
        new_radius = size.diameter_mm / 2
        min_distance = new_radius * 0.6  # Уменьшенный коэффициент для скорости

        # Проверяем только последние N стразов для ускорения
        check_count = min(50, len(existing_rhinestones))
        recent_rhinestones = existing_rhinestones[-check_count:] if check_count > 0 else []

        for rhinestone in recent_rhinestones:
            existing_radius = rhinestone.size.diameter_mm / 2
            distance_sq = (point.x - rhinestone.position.x) ** 2 + (point.y - rhinestone.position.y) ** 2
            required_distance_sq = ((new_radius + existing_radius) * 0.7) ** 2

            if distance_sq < required_distance_sq:
                return False

        return True

    def _fill_text_gaps_fast(self, binary_mask, existing_rhinestones, smallest_size, color, step):
        """ИСПРАВЛЕНИЕ: Быстрое заполнение пропусков."""
        gap_rhinestones = []
        height, width = binary_mask.shape

        # Создаем упрощенную маску покрытия
        coverage_mask = np.zeros_like(binary_mask, dtype=bool)

        # ИСПРАВЛЕНИЕ: Векторизованное создание маски покрытия
        for rhinestone in existing_rhinestones:
            x, y = int(rhinestone.position.x), int(rhinestone.position.y)
            radius = int(rhinestone.size.diameter_mm * 1.0)  # Уменьшенный радиус покрытия

            # Простое квадратное покрытие вместо круглого для скорости
            y_min, y_max = max(0, y - radius), min(height, y + radius)
            x_min, x_max = max(0, x - radius), min(width, x + radius)
            coverage_mask[y_min:y_max, x_min:x_max] = True

        # Ищем непокрытые области с большим шагом
        large_step = max(step * 2, 3)
        uncovered = binary_mask & ~coverage_mask

        for y in range(0, height, int(large_step)):
            for x in range(0, width, int(large_step)):
                if 0 <= y < height and 0 <= x < width and uncovered[y, x]:
                    point = Point(x, y)
                    if self._can_place_rhinestone_fast(point, smallest_size, existing_rhinestones + gap_rhinestones):
                        gap_rhinestones.append(Rhinestone(
                            position=point,
                            size=smallest_size,
                            color=color
                        ))

        return gap_rhinestones

    def _process_standard_image(self, img: Image.Image, settings: ProcessingSettings) -> Project:
        """Стандартный алгоритм обработки изображений (существующий код)"""
        # Уменьшаем изображение для ускорения сэмплирования
        sample_step = 5
        sample_width = img.width // sample_step
        sample_height = img.height // sample_step

        # Используем LANCZOS для более качественного ресайза
        img_sampled = img.resize((sample_width, sample_height), Image.LANCZOS)
        pixels = img_sampled.load()

        # НОВОЕ: Определяем внутренние белые области если включена опция
        inner_white_mask = None
        if settings.fill_inner_white:
            inner_white_mask = self._find_inner_white_areas(img_sampled, pixels)
            print(f"Найдено внутренних белых областей для заполнения")

        # Создание сетки для сэмплирования
        grid_spacing = settings.spacing
        grid_points = self._create_grid(sample_width, sample_height, grid_spacing, settings.grid_mode)

        # Генерация стразов
        rhinestones: List[Rhinestone] = []

        for point in grid_points:
            # Округляем до ближайшего пикселя
            ix = min(max(int(round(point.x)), 0), sample_width - 1)
            iy = min(max(int(round(point.y)), 0), sample_height - 1)

            r, g, b = pixels[ix, iy]

            # ОБНОВЛЕННАЯ ЛОГИКА: Пропускаем белый фон, но заполняем внутренние белые области
            is_white = r >= 250 and g >= 250 and b >= 250

            if is_white:
                if settings.fill_inner_white and inner_white_mask and inner_white_mask[ix][iy]:
                    # Это внутренняя белая область - заполняем
                    print(f"Заполняем внутреннюю белую область в ({ix}, {iy})")
                else:
                    # Это фон или внешняя белая область - пропускаем
                    continue

            pixel_color = RGBColor(r, g, b)

            nearest_palette_color = self.palette_service.find_nearest(
                pixel_color, settings.allowed_colors
            )
            if not nearest_palette_color:
                print(f"Не найден подходящий цвет для пикселя rgb({r}, {g}, {b})")
                continue

            # Рассчитываем размер на основе яркости
            brightness = (r + g + b) / (255 * 3)
            raw_size = settings.base_dot_size_mm * (1 - brightness)

            nearest_size = self._find_nearest_size(raw_size, settings.allowed_sizes)
            if not nearest_size:
                print(f"Не найден подходящий размер для raw_size={raw_size}")
                continue

            # Создаем страз
            rhinestones.append(Rhinestone(
                position=point,
                size=nearest_size,
                color=nearest_palette_color
            ))

        if not rhinestones:
            print("Не создано ни одного страза!")
            return Project()

        # Масштабирование и центрирование стразов
        rhinestones = self._scale_and_center_rhinestones(rhinestones, settings.output)

        # Формирование отчета и создание объекта Project
        from collections import defaultdict
        report_data = defaultdict(int)
        for r in rhinestones:
            key = (r.color.name, r.size.name)
            report_data[key] += 1

        project = Project(
            rhinestones=rhinestones,
            report=dict(report_data),
            total_count=len(rhinestones)
        )

        return project

    def _find_nearest_size(
            self,
            raw_size_mm: float,
            allowed_names: Optional[List[str]] = None
    ) -> Optional[RhinestoneSize]:
        """Находит ближайший стандартный размер страза."""

        # Определяем, в каком наборе размеров искать
        sizes_to_check = list(self.available_sizes.values())
        if allowed_names:
            allowed_names_set = set(allowed_names)
            sizes_to_check = [s for s in sizes_to_check if s.name in allowed_names_set]

        if not sizes_to_check:
            return None

        return min(sizes_to_check, key=lambda s: abs(s.diameter_mm - raw_size_mm))

    def _get_pixel_color_safe(self, img: Image.Image, x: int, y: int) -> RGBColor:
        """Безопасно получает цвет пикселя с проверкой границ"""
        try:
            # Убеждаемся что координаты в пределах изображения
            x = max(0, min(x, img.width - 1))
            y = max(0, min(y, img.height - 1))

            if img.mode == 'RGB':
                r, g, b = img.getpixel((x, y))
            elif img.mode == 'RGBA':
                r, g, b, a = img.getpixel((x, y))
            else:
                # Для других режимов конвертируем в RGB
                rgb_img = img.convert('RGB')
                r, g, b = rgb_img.getpixel((x, y))

            return RGBColor(r, g, b)
        except Exception as e:
            print(f"Ошибка получения цвета пикселя ({x}, {y}): {e}")
            return RGBColor(0, 0, 0)  # Возвращаем черный как fallback

    def _mark_covered_pixels(self, covered_mask: np.ndarray, center_x: int, center_y: int,
                             radius: float, shape: tuple):
        """Помечает пиксели, покрытые стразом"""
        y_min, y_max = int(center_y - radius), int(center_y + radius) + 1
        x_min, x_max = int(center_x - radius), int(center_x + radius) + 1

        for sy in range(y_min, y_max):
            for sx in range(x_min, x_max):
                if 0 <= sy < shape[0] and 0 <= sx < shape[1]:
                    if (sx - center_x) ** 2 + (sy - center_y) ** 2 < radius ** 2:
                        covered_mask[sy, sx] = True

    def _find_inner_white_areas(self, img_sampled, pixels):
        """
        Находит внутренние белые области (окруженные объектом, не касающиеся краев)
        Возвращает маску True для пикселей, которые нужно заполнить
        """
        sample_width, sample_height = img_sampled.size
        white_threshold = 240

        print(f"Анализ белых областей на изображении {sample_width}x{sample_height}")

        # 1. Создаем маску белых пикселей
        white_mask = [[False for _ in range(sample_height)] for _ in range(sample_width)]
        white_count = 0

        for y in range(sample_height):
            for x in range(sample_width):
                r, g, b = pixels[x, y]
                is_white = (r >= white_threshold and g >= white_threshold and b >= white_threshold)
                white_mask[x][y] = is_white
                if is_white:
                    white_count += 1

        print(f"Найдено {white_count} белых пикселей")

        # 2. Помечаем все белые области, которые касаются краев (это фон)
        visited = [[False for _ in range(sample_height)] for _ in range(sample_width)]
        background_areas = set()  # Координаты областей, которые являются фоном

        def flood_fill_background(start_x, start_y):
            """Flood fill для пометки фоновых областей"""
            if not (0 <= start_x < sample_width and 0 <= start_y < sample_height):
                return
            if visited[start_x][start_y] or not white_mask[start_x][start_y]:
                return

            # BFS для пометки всей связанной белой области как фон
            queue = deque([(start_x, start_y)])
            area_pixels = []

            while queue:
                x, y = queue.popleft()
                if visited[x][y]:
                    continue

                visited[x][y] = True
                area_pixels.append((x, y))

                # Проверяем 4 соседа
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if (0 <= nx < sample_width and 0 <= ny < sample_height and
                            not visited[nx][ny] and white_mask[nx][ny]):
                        queue.append((nx, ny))

            # Помечаем всю область как фон
            for px, py in area_pixels:
                background_areas.add((px, py))

            print(f"Помечена фоновая область из ({start_x}, {start_y}): {len(area_pixels)} пикселей")

        # 3. Запускаем flood fill от всех краевых белых пикселей
        # Верхний и нижний край
        for x in range(sample_width):
            if white_mask[x][0] and not visited[x][0]:
                flood_fill_background(x, 0)
            if white_mask[x][sample_height - 1] and not visited[x][sample_height - 1]:
                flood_fill_background(x, sample_height - 1)

        # Левый и правый край
        for y in range(sample_height):
            if white_mask[0][y] and not visited[0][y]:
                flood_fill_background(0, y)
            if white_mask[sample_width - 1][y] and not visited[sample_width - 1][y]:
                flood_fill_background(sample_width - 1, y)

        # 4. Создаем финальную маску: белые области, которые НЕ являются фоном
        inner_white_mask = [[False for _ in range(sample_height)] for _ in range(sample_width)]
        inner_count = 0

        for x in range(sample_width):
            for y in range(sample_height):
                if white_mask[x][y] and (x, y) not in background_areas:
                    inner_white_mask[x][y] = True
                    inner_count += 1

        print(f"Найдено {inner_count} внутренних белых пикселей для заполнения")
        print(f"Исключено {len(background_areas)} фоновых белых пикселей")

        return inner_white_mask

    def _scale_and_center_rhinestones(
            self,
            rhinestones: List[Rhinestone],
            output_settings: OutputSettings
    ) -> List[Rhinestone]:
        """
        Масштабирует и центрирует стразы для вписывания в выходные размеры.
        Теперь использует точные размеры в пикселях, рассчитанные из миллиметров.
        """
        if not rhinestones:
            return rhinestones

        # Находим границы получившегося узора
        min_x = min(r.position.x for r in rhinestones)
        max_x = max(r.position.x for r in rhinestones)
        min_y = min(r.position.y for r in rhinestones)
        max_y = max(r.position.y for r in rhinestones)

        pattern_width = max_x - min_x
        pattern_height = max_y - min_y

        # ИСПРАВЛЕНИЕ: Используем точные размеры в пикселях, рассчитанные из миллиметров
        canvas_width_px = output_settings.width_px  # Уже точно рассчитано из мм и DPI
        canvas_height_px = output_settings.height_px  # Уже точно рассчитано из мм и DPI

        margin_x = canvas_width_px * 0.025
        margin_y = canvas_height_px * 0.025

        # Уменьшаем целевую область для масштабирования на величину отступов
        target_width = canvas_width_px - 2 * margin_x
        target_height = canvas_height_px - 2 * margin_y

        # Масштабируем узор, чтобы он вписался в эту УМЕНЬШЕННУЮ "безопасную область"
        scale_factor = 1.0  # Значение по умолчанию на случай, если pattern_width/height равны нулю
        if pattern_width > 0 and pattern_height > 0:
            scale_factor = min(
                target_width / pattern_width,
                target_height / pattern_height
            )

        # Вычисляем смещение для центрирования
        final_width = pattern_width * scale_factor
        final_height = pattern_height * scale_factor
        offset_x = (canvas_width_px - final_width) / 2
        offset_y = (canvas_height_px - final_height) / 2

        # Применяем масштабирование и смещение ко всем стразам
        for r in rhinestones:
            new_x = (r.position.x - min_x) * scale_factor + offset_x
            new_y = (r.position.y - min_y) * scale_factor + offset_y
            r.position = Point(new_x, new_y)

        # Отладочная информация
        actual_width_mm, actual_height_mm = output_settings.get_actual_size_mm()
        print(f"Целевые размеры: {output_settings.width_mm}x{output_settings.height_mm} мм")
        print(f"Размеры в пикселях: {canvas_width_px}x{canvas_height_px} px")
        print(f"Фактические размеры: {actual_width_mm:.2f}x{actual_height_mm:.2f} мм")

        return rhinestones

    def _fill_inner_white_areas(self, img_sampled, pixels):
        """
        Определяет внутренние белые области для заполнения
        """
        sample_width, sample_height = img_sampled.size
        white_threshold = 240

        # Создаем маску белых пикселей
        white_mask = [[False for _ in range(sample_height)] for _ in range(sample_width)]
        for y in range(sample_height):
            for x in range(sample_width):
                r, g, b = pixels[x, y]
                white_mask[x][y] = (r >= white_threshold and g >= white_threshold and b >= white_threshold)

        # Используем flood fill для определения внешних белых областей
        visited = [[False for _ in range(sample_height)] for _ in range(sample_width)]
        queue = deque()

        # Добавляем граничные белые пиксели в очередь
        for x in range(sample_width):
            if white_mask[x][0]:
                queue.append((x, 0))
                visited[x][0] = True
            if white_mask[x][sample_height - 1]:
                queue.append((x, sample_height - 1))
                visited[x][sample_height - 1] = True

        for y in range(sample_height):
            if white_mask[0][y]:
                queue.append((0, y))
                visited[0][y] = True
            if white_mask[sample_width - 1][y]:
                queue.append((sample_width - 1, y))
                visited[sample_width - 1][y] = True

        # Распространяем от границ
        while queue:
            cx, cy = queue.popleft()
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < sample_width and 0 <= ny < sample_height:
                    if white_mask[nx][ny] and not visited[nx][ny]:
                        visited[nx][ny] = True
                        queue.append((nx, ny))

        # Возвращаем маску внутренних белых областей
        return [[white_mask[x][y] and not visited[x][y] for y in range(sample_height)] for x in range(sample_width)]

    def _create_grid(self, width: int, height: int, spacing: float, mode: str) -> List[Point]:
        """Создает сетку точек для сэмплирования изображения."""
        points = []
        if mode == "honeycomb":
            y_step = spacing * math.sqrt(3) / 2
            if y_step == 0: return []
            row_index = 0
            y = 0
            while y < height:
                x_offset = (spacing / 2) if (row_index % 2 != 0) else 0
                x = x_offset
                while x < width:
                    points.append(Point(x, y))
                    x += spacing
                y += y_step
                row_index += 1
        else:  # "uniform" - режим по умолчанию
            for x in np.arange(0, width, spacing):
                for y in np.arange(0, height, spacing):
                    points.append(Point(x, y))
        return points