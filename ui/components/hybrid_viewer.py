# ui/components/hybrid_viewer.py
# Гибридный просмотрщик для растровых изображений и векторных макетов стразов.
# Обновленная версия с пояснениями о масштабировании для соответствия экспорту.

from typing import Optional, List
from PyQt5.QtCore import Qt, pyqtSignal, QRectF
from PyQt5.QtGui import QPixmap, QColor, QBrush, QPen
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsRectItem

from core.models import Project, OutputSettings, Rhinestone, CanvasSettings
from ui.components.base_canvas import BaseCanvas


class CanvasBorderItem(QGraphicsRectItem):
    """Элемент для отображения границ холста оранжевой прерывистой линией."""

    def __init__(self, rect: QRectF):
        super().__init__(rect)

        pen = QPen(QColor(255, 140, 0))  # Оранжевый цвет
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        pen.setCosmetic(True)  # Толщина линии не зависит от масштаба

        self.setPen(pen)
        self.setBrush(QBrush(Qt.NoBrush))
        self.setFlags(self.flags() & ~self.ItemIsSelectable & ~self.ItemIsMovable)
        self.setZValue(1000)


class VectorRhinestoneItem(QGraphicsEllipseItem):
    """Векторный элемент страза для режима предпросмотра."""

    def __init__(self, rhinestone: Rhinestone, dpi: float):
        radius_px = ( (rhinestone.size.diameter_mm * dpi) / 25.4) / 2
        super().__init__(-radius_px, -radius_px, radius_px * 2, radius_px * 2)

        self.setPos(rhinestone.position.x, rhinestone.position.y)

        color = QColor(rhinestone.color.color.r, rhinestone.color.color.g, rhinestone.color.color.b)
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.NoPen))
        self.setFlags(self.flags() & ~self.ItemIsSelectable & ~self.ItemIsMovable)


class HybridViewer(BaseCanvas):
    """
    Гибридный просмотрщик, способный отображать как растровые изображения,
    так и векторные проекты стразов, а также границы холста.
    """
    imageChanged = pyqtSignal()
    projectChanged = pyqtSignal()
    modeChanged = pyqtSignal(str)

    def __init__(self, settings: Optional[CanvasSettings] = None, parent=None):
        super().__init__(settings, parent)
        self.setDragMode(self.NoDrag)

        self._current_mode = "raster"
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._current_pixmap: Optional[QPixmap] = None

        self._project: Optional[Project] = None
        self._output_settings: Optional[OutputSettings] = None
        self._rhinestone_items: List[VectorRhinestoneItem] = []

        self._canvas_border_item: Optional[CanvasBorderItem] = None
        self._canvas_bounds_visible = True

    def get_current_mode(self) -> str:
        return self._current_mode

    def set_canvas_bounds_visible(self, visible: bool):
        self._canvas_bounds_visible = visible
        if self._canvas_border_item:
            self._canvas_border_item.setVisible(visible)

    def update_canvas_bounds(self, output_settings: OutputSettings):
        """Обновляет границы холста на основе настроек вывода."""
        if not output_settings:
            if self._canvas_border_item:
                self._scene.removeItem(self._canvas_border_item)
                self._canvas_border_item = None
            return

        canvas_width_px = output_settings.width_px
        canvas_height_px = output_settings.height_px
        border_rect = QRectF(0, 0, canvas_width_px, canvas_height_px)

        if self._canvas_border_item:
            self._scene.removeItem(self._canvas_border_item)

        self._canvas_border_item = CanvasBorderItem(border_rect)
        self._canvas_border_item.setVisible(self._canvas_bounds_visible)
        self._scene.addItem(self._canvas_border_item)

        # Устанавливаем размер сцены точно по границам холста + небольшой отступ
        scene_rect = border_rect.adjusted(-50, -50, 50, 50)
        self.set_content_rect(scene_rect)

    def setPixmap(self, pixmap: QPixmap, settings: Optional[OutputSettings] = None, preserve_view: bool = False):
        """
        Устанавливает растровое изображение. Изображение центрируется внутри
        границ холста, если они заданы.
        """
        if pixmap is None or pixmap.isNull():
            self._clear_raster()
            return

        self._switch_to_raster_mode()

        if self._pixmap_item:
            self._scene.removeItem(self._pixmap_item)

        self._current_pixmap = pixmap
        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        self._pixmap_item.setFlags(self._pixmap_item.flags() & ~self._pixmap_item.ItemIsSelectable)

        content_rect = self._pixmap_item.boundingRect()

        if settings:
            canvas_width_px = settings.width_px
            canvas_height_px = settings.height_px
            x_pos = (canvas_width_px - pixmap.width()) / 2
            y_pos = (canvas_height_px - pixmap.height()) / 2
            self._pixmap_item.setPos(x_pos, y_pos)
            content_rect = QRectF(0, 0, canvas_width_px, canvas_height_px)

        self._scene.addItem(self._pixmap_item)
        self.set_content_rect(content_rect)

        if not preserve_view:
            self.fit_to_view(content_rect)

        self.imageChanged.emit()

    def load_project(self, project: Project, output_settings: OutputSettings, preserve_view: bool = False):
        """
        Загружает векторный проект. По умолчанию вид масштабируется для обзора.
        Для просмотра в реальном размере 1:1, как при экспорте, нажмите клавишу '1'.
        """
        self._switch_to_vector_mode()

        self._project = project
        self._output_settings = output_settings
        self._clear_vector_items()

        display_dpi = output_settings.dpi
        canvas_width_px = output_settings.width_px
        canvas_height_px = output_settings.height_px

        for rhinestone in project.rhinestones:
            item = VectorRhinestoneItem(rhinestone, display_dpi)
            self._scene.addItem(item)
            self._rhinestone_items.append(item)

        self.update_canvas_bounds(output_settings)
        content_rect = QRectF(0, 0, canvas_width_px, canvas_height_px)

        if not preserve_view:
            self.fit_to_view(content_rect)

        self.projectChanged.emit()
        self.imageChanged.emit()

    def _switch_to_raster_mode(self):
        if self._current_mode != "raster":
            self._clear_vector_items()
            if self._canvas_border_item:
                self._canvas_border_item.setVisible(False)
            self._current_mode = "raster"
            self.modeChanged.emit("raster")

    def _switch_to_vector_mode(self):
        if self._current_mode != "vector":
            self._clear_raster()
            if self._canvas_border_item:
                self._canvas_border_item.setVisible(self._canvas_bounds_visible)
            self._current_mode = "vector"
            self.modeChanged.emit("vector")

    def _clear_raster(self):
        if self._pixmap_item:
            self._scene.removeItem(self._pixmap_item)
            self._pixmap_item = None
        self._current_pixmap = None

    def _clear_vector_items(self):
        for item in self._rhinestone_items:
            if item.scene():
                self._scene.removeItem(item)
        self._rhinestone_items.clear()
        if self._canvas_border_item:
            self._scene.removeItem(self._canvas_border_item)
            self._canvas_border_item = None

    def clear(self):
        self._clear_raster()
        self._clear_vector_items()
        self._project = None
        self._output_settings = None
        # Сбрасываем сцену к минимальному размеру
        self.set_content_rect(QRectF(0, 0, 1, 1))
        self.imageChanged.emit()

    def pixmap(self) -> Optional[QPixmap]:
        return self._current_pixmap if self._current_mode == "raster" else None

    def get_project(self) -> Optional[Project]:
        return self._project if self._current_mode == "vector" else None