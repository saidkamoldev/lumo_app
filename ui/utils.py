# ui/utils.py
# Вспомогательные функции для UI

from PIL import Image
from PyQt5.QtGui import QImage, QPixmap


def pil_to_qpixmap(pil_image: Image.Image) -> QPixmap:
    """
    Корректно и надежно конвертирует изображение из Pillow (PIL) в QPixmap.
    """
    # 1. Конвертируем изображение в RGBA.
    #    Это стандартный формат, который QImage отлично понимает,
    #    и это решает проблемы с разными режимами (RGB, P, LA и т.д.).
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")

    # 2. Получаем сырые байты изображения.
    width, height = pil_image.size
    data = pil_image.tobytes("raw", "RGBA")

    # 3. Создаем QImage из этих байтов.
    #    QImage.Format_RGBA8888 - это точный формат данных, которые мы передаем.
    qimage = QImage(data, width, height, QImage.Format_RGBA8888)

    # 4. Создаем QPixmap из QImage.
    return QPixmap.fromImage(qimage)