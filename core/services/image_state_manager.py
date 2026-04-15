# core/services/image_state_manager.py
# Управляет состоянием изображения: оригинал, трассировка, параметры.

import os
import tempfile
from typing import Optional
from PIL import Image, ImageOps

from ..models import TraceParameters

class ImageStateManager:
    """
    Управляет состоянием исходного изображения в приложении.
    """
    def __init__(self):
        self._original_image: Optional[Image.Image] = None
        self._traced_image: Optional[Image.Image] = None
        self._is_traced: bool = False

    def get_original_image(self) -> Optional[Image.Image]:
        """Возвращает оригинальное, нетронутое изображение."""
        return self._original_image

    def load_original_image(self, image_path: str) -> bool:
        """Загружает оригинальное изображение и сбрасывает состояние."""
        try:
            self.cleanup() # Очищаем предыдущее состояние
            self._original_image = Image.open(image_path).convert('RGB')
            return True
        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            self._original_image = None
            return False

    def mirror_original_image(self) -> Optional[Image.Image]:
        """
        Отзеркаливает оригинальное изображение, сбрасывает трассировку
        и возвращает новое изображение.
        """
        if not self._original_image:
            return None

        self._original_image = ImageOps.mirror(self._original_image)
        # Отзеркаливание исходника делает любую трассировку неактуальной
        self.reset_trace()

        return self.get_current_image()

    def load_original_image_from_pil(self, image: Image.Image):
        """Загружает изображение из объекта PIL, сбрасывая состояние."""
        self.cleanup()
        self._original_image = image.copy()
        return True

    def apply_trace(self, traced_image: Image.Image):
        """Применяет трассированное изображение как текущее."""
        self._traced_image = traced_image
        self._is_traced = True

    def reset_trace(self):
        """Сбрасывает трассированное изображение, возвращаясь к оригиналу."""
        self._traced_image = None
        self._is_traced = False

    def get_current_image(self) -> Optional[Image.Image]:
        """Возвращает текущее активное изображение (трассированное или оригинал)."""
        return self._traced_image if self._is_traced else self._original_image

    def can_trace(self) -> bool:
        """Проверяет, есть ли изображение для трассировки."""
        return self._original_image is not None

    def cleanup(self):
        """Сбрасывает состояние до начального."""
        self._original_image = None
        self._traced_image = None
        self._is_traced = False