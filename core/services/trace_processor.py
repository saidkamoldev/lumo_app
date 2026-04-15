# core/services/trace_processor.py
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from ..models import TraceParameters


class TraceProcessor:
    """Выполняет сложные операции над изображением для подготовки к трассировке."""

    def __init__(self):
        self._original_image: Image.Image = None

    def set_source_image(self, image: Image.Image):
        """Устанавливает исходное изображение для всех операций."""
        # Убедимся, что работаем с копией в формате RGB
        self._original_image = image.copy().convert("RGB")

    def process_with_parameters(self, params: TraceParameters, is_preview=False) -> Image.Image:
        """
        Применяет к изображению серию фильтров.
        Если is_preview=True, возвращает уменьшенную копию для отображения.
        Финальная обработка всегда идет в полном разрешении.
        """
        if not self._original_image:
            raise ValueError("Исходное изображение не установлено. Вызовите set_source_image() сначала.")

        img = self._original_image.copy()

        # 1. Коррекция яркости
        if params.brightness_enabled and params.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(params.brightness)

        # 2. Коррекция контраста
        if params.contrast_enabled and params.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(params.contrast)

        # 3. Коррекция насыщенности
        if params.saturation_enabled and params.saturation != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(params.saturation)

        # 4. Размытие
        if params.blur_enabled and params.blur_type != 'none' and params.blur_strength > 0:
            img = self._apply_blur(img, params.blur_type, params.blur_strength)

        # 5. Повышение резкости (если включено)
        if params.sharpen_enabled:
            img = self._apply_sharpening(img, params.sharpen_strength)

        # 6. Постеризация
        if params.colors_enabled and params.colors > 0:
            img = self._apply_posterization(img, params.colors)

        # 7. Инвертирование
        if params.invert_enabled:
            img = ImageOps.invert(img)

        # 8. Гамма-коррекция (если включена)
        if params.gamma_enabled and params.gamma != 1.0:
            img = self._apply_gamma_correction(img, params.gamma)

        # 9. Цветовая температура (если включена)
        if params.temperature_enabled and params.temperature != 0:
            img = self._apply_temperature_shift(img, params.temperature)

        return img


    def _apply_blur(self, img: Image.Image, blur_type: str, strength: float) -> Image.Image:
        """Применяет различные типы размытия."""
        if blur_type == 'gaussian':
            return img.filter(ImageFilter.GaussianBlur(radius=strength))


        elif blur_type == 'median':
            size = int(strength * 2) + 1
            if size % 2 == 0:
                size += 1
            if size <= 1:
                return img
            size = min(size, 15)
            return img.filter(ImageFilter.MedianFilter(size=size))

        elif blur_type == 'bilateral':
            # Билатеральный фильтр (аппроксимация)
            temp = img.filter(ImageFilter.GaussianBlur(radius=strength * 0.5))
            return Image.blend(img, temp, 0.7)

        elif blur_type == 'motion':
            # Имитация motion blur через комбинацию фильтров
            return img.filter(ImageFilter.BLUR).filter(ImageFilter.BLUR)

        elif blur_type == 'radial':
            # Радиальное размытие (упрощенная версия)
            temp = img.filter(ImageFilter.GaussianBlur(radius=strength))
            return Image.blend(img, temp, 0.6)

        return img

    def _apply_sharpening(self, img: Image.Image, strength: float) -> Image.Image:
        """Применяет повышение резкости с настраиваемой силой."""
        if strength <= 0:
            return img

        if strength <= 1.0:
            # Слабое повышение резкости
            return img.filter(ImageFilter.SHARPEN)
        else:
            # Сильное повышение резкости
            img = img.filter(ImageFilter.SHARPEN)
            if strength > 1.5:
                # Дополнительное повышение резкости для высоких значений
                img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=int(strength * 100)))

        return img

    def _apply_posterization(self, img: Image.Image, colors: int) -> Image.Image:
        """Применяет постеризацию (уменьшение количества цветов)."""
        if colors == 1:
            return img.convert('L').convert('RGB')

        # Adaptive quantization для лучшего результата
        quantized = img.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=0)
        return quantized.convert('RGB')

    def _apply_gamma_correction(self, img: Image.Image, gamma: float) -> Image.Image:
        """Применяет гамма-коррекцию."""
        import numpy as np

        # Конвертируем в numpy array для гамма-коррекции
        img_array = np.array(img, dtype=np.float32) / 255.0

        # Применяем гамма-коррекцию
        corrected = np.power(img_array, 1.0 / gamma)

        # Возвращаем в формат PIL
        corrected = (corrected * 255).astype(np.uint8)
        return Image.fromarray(corrected)

    def _apply_temperature_shift(self, img: Image.Image, temperature: float) -> Image.Image:
        """Применяет сдвиг цветовой температуры."""
        import numpy as np

        img_array = np.array(img, dtype=np.float32)

        if temperature > 0:
            # Теплые тона (больше красного/желтого)
            img_array[:, :, 0] *= (1.0 + temperature * 0.3)  # Красный
            img_array[:, :, 1] *= (1.0 + temperature * 0.1)  # Зеленый
            img_array[:, :, 2] *= (1.0 - temperature * 0.2)  # Синий
        else:
            # Холодные тона (больше синего)
            temp = abs(temperature)
            img_array[:, :, 0] *= (1.0 - temp * 0.2)  # Красный
            img_array[:, :, 1] *= (1.0 - temp * 0.1)  # Зеленый
            img_array[:, :, 2] *= (1.0 + temp * 0.3)  # Синий

        # Ограничиваем значения
        img_array = np.clip(img_array, 0, 255).astype(np.uint8)
        return Image.fromarray(img_array)

    def reset(self):
        """Сбрасывает процессор к исходному состоянию."""
        if self._original_image:
            self._source_image = self._original_image.copy()