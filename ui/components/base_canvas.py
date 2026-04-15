# ui/base_canvas.py
# Базовый класс для всех холстов с общим управлением масштабом, панорамированием и настройками.

from typing import Optional
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRectF, QPointF
from PyQt5.QtGui import QColor, QPainter, QBrush
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QFrame, QScrollBar


class CanvasSettings:
    """Общие настройки для всех холстов."""

    def __init__(self):
        self.background_color = QColor("#2D2D2D")
        self.zoom_factor = 1.0
        self.min_zoom = 0.05
        self.max_zoom = 50.0
        self.zoom_step = 1.15

    def copy(self):
        new_settings = CanvasSettings()
        new_settings.background_color = QColor(self.background_color)
        new_settings.zoom_factor = self.zoom_factor
        new_settings.min_zoom = self.min_zoom
        new_settings.max_zoom = self.max_zoom
        new_settings.zoom_step = self.zoom_step
        return new_settings


class ThemedScrollBar(QScrollBar):
    """Кастомный скроллбар с `objectName` для стилизации через QSS."""

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setObjectName("themedScrollBar")


class BaseCanvas(QGraphicsView):
    """
    Базовый класс для холстов, предоставляющий функции масштабирования,
    панорамирования (с зажатым `Space`), управления скроллбарами и настройками.
    """
    backgroundColorChanged = pyqtSignal(QColor)
    zoomChanged = pyqtSignal(float)

    def __init__(self, settings: Optional[CanvasSettings] = None, parent=None):
        super().__init__(parent)
        self._settings = settings if settings else CanvasSettings()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._setup_base_widget()
        self._pan_mode = False
        self._space_pressed = False
        self._mouse_pressed = False
        self._last_pan_pos = QPointF()
        self._extended_scene_margin = 2000
        self._content_rect = QRectF()
        self.setDragMode(QGraphicsView.NoDrag)
        self._zoom_timer = QTimer()
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.timeout.connect(self._on_zoom_finished)
        self._h_scroll_bar = ThemedScrollBar(Qt.Horizontal, self)
        self._v_scroll_bar = ThemedScrollBar(Qt.Vertical, self)
        self._h_scroll_bar.valueChanged.connect(self._on_manual_scroll)
        self._v_scroll_bar.valueChanged.connect(self._on_manual_scroll)
        self._is_scrolling_manually = False

        self._apply_settings()
        self.setFocusPolicy(Qt.StrongFocus)
        self._update_scroll_bars()

    def set_content_rect(self, rect: QRectF):
        """Устанавливает основную область контента и расширяет сцену вокруг нее."""
        self._content_rect = rect
        self._update_extended_scene()
        self._update_scroll_bars()

    def _update_extended_scene(self):
        """Создает большую "буферную" зону вокруг контента для плавной прокрутки."""
        if self._content_rect.isEmpty(): return
        margin = self._extended_scene_margin
        extended_rect = self._content_rect.adjusted(-margin, -margin, margin, margin)
        self._scene.setSceneRect(extended_rect)

    def _setup_base_widget(self):
        """Базовая настройка виджета QGraphicsView."""
        self.setFrameShape(QFrame.NoFrame)
        # Фон самого виджета делаем прозрачным, чтобы цвет сцены был виден
        self.setStyleSheet("background: transparent; border: none;")
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

    def _apply_settings(self):
        """Применяет текущие настройки к холсту."""
        # Устанавливаем цвет фона только для сцены, а не для всего виджета
        self._scene.setBackgroundBrush(QBrush(self._settings.background_color))
        self.resetTransform()
        if self._settings.zoom_factor != 1.0:
            self.scale(self._settings.zoom_factor, self._settings.zoom_factor)

    def apply_settings(self, settings: CanvasSettings):
        old_background = self._settings.background_color
        self._settings = settings.copy()
        self._apply_settings()
        if old_background != self._settings.background_color:
            self.backgroundColorChanged.emit(self._settings.background_color)

    def get_settings(self) -> CanvasSettings:
        return self._settings

    def setBackgroundColor(self, color: QColor):
        """Публичный метод для установки цвета фона сцены."""
        self._settings.background_color = QColor(color)
        self._scene.setBackgroundBrush(QBrush(color))
        self.backgroundColorChanged.emit(color)

    def getBackgroundColor(self) -> QColor:
        return QColor(self._settings.background_color)

    def _zoom(self, factor: float):
        """Масштабирует вид с учетом ограничений."""
        new_zoom = self._settings.zoom_factor * factor
        if new_zoom < self._settings.min_zoom:
            factor = self._settings.min_zoom / self._settings.zoom_factor
        elif new_zoom > self._settings.max_zoom:
            factor = self._settings.max_zoom / self._settings.zoom_factor

        self.scale(factor, factor)
        self._settings.zoom_factor = self.transform().m11()
        self._zoom_timer.start(50)  # Отложенный сигнал для производительности

    def _on_zoom_finished(self):
        """Вызывается после завершения серии операций масштабирования."""
        self.zoomChanged.emit(self._settings.zoom_factor)
        self._update_scroll_bars()

    def fit_to_view(self, rect: QRectF = None):
        """Масштабирует и центрирует вид, чтобы уместить указанный прямоугольник."""
        if rect is None:
            rect = self._content_rect if not self._content_rect.isEmpty() else self._scene.sceneRect()
        if rect.isEmpty() or rect.width() == 0 or rect.height() == 0: return

        view_rect = self.viewport().rect()
        scale = min(view_rect.width() / rect.width(), view_rect.height() / rect.height()) * 0.95
        scale = max(self._settings.min_zoom, min(self._settings.max_zoom, scale))

        self.resetTransform()
        self.scale(scale, scale)
        self._settings.zoom_factor = scale
        self.centerOn(rect.center())
        self.zoomChanged.emit(self._settings.zoom_factor)
        self._update_scroll_bars()

    def reset_zoom(self):
        """Сбрасывает масштаб к 100%."""
        self.resetTransform()
        self._settings.zoom_factor = 1.0
        self.zoomChanged.emit(self._settings.zoom_factor)
        self._update_scroll_bars()

    def _update_scroll_bars(self):
        """Обновляет состояние и положение кастомных скроллбаров."""
        if self._is_scrolling_manually: return
        view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        scene_rect = self.sceneRect()

        self._h_scroll_bar.blockSignals(True)
        self._v_scroll_bar.blockSignals(True)

        if scene_rect.width() > view_rect.width():
            self._h_scroll_bar.show()
            self._h_scroll_bar.setRange(int(scene_rect.left()), int(scene_rect.right() - view_rect.width()))
            self._h_scroll_bar.setPageStep(int(view_rect.width()))
            self._h_scroll_bar.setValue(int(view_rect.left()))
        else:
            self._h_scroll_bar.hide()

        if scene_rect.height() > view_rect.height():
            self._v_scroll_bar.show()
            self._v_scroll_bar.setRange(int(scene_rect.top()), int(scene_rect.bottom() - view_rect.height()))
            self._v_scroll_bar.setPageStep(int(view_rect.height()))
            self._v_scroll_bar.setValue(int(view_rect.top()))
        else:
            self._v_scroll_bar.hide()

        self._h_scroll_bar.blockSignals(False)
        self._v_scroll_bar.blockSignals(False)

    def _on_manual_scroll(self):
        """Центрирует вид при ручной прокрутке скроллбаром."""
        self._is_scrolling_manually = True
        view_center = self.mapToScene(self.viewport().rect().center())
        new_center_x = self._h_scroll_bar.value() + self.mapToScene(self.viewport().rect()).boundingRect().width() / 2
        new_center_y = self._v_scroll_bar.value() + self.mapToScene(self.viewport().rect()).boundingRect().height() / 2
        if self.sender() == self._h_scroll_bar:
            self.centerOn(QPointF(new_center_x, view_center.y()))
        elif self.sender() == self._v_scroll_bar:
            self.centerOn(QPointF(view_center.x(), new_center_y))
        self._is_scrolling_manually = False

    def _start_pan_mode(self):
        """Включает режим панорамирования (перетаскивания холста)."""
        if not self._pan_mode:
            self._pan_mode = True
            self.viewport().setCursor(Qt.OpenHandCursor)

    def _stop_pan_mode(self):
        """Выключает режим панорамирования."""
        if self._pan_mode:
            self._pan_mode = False
            self.viewport().setCursor(Qt.ArrowCursor)

    def resizeEvent(self, event):
        """Перемещает скроллбары при изменении размера окна."""
        super().resizeEvent(event)
        v_width = self._v_scroll_bar.sizeHint().width()
        h_height = self._h_scroll_bar.sizeHint().height()
        viewport_rect = self.viewport().rect()
        self._v_scroll_bar.setGeometry(viewport_rect.right() - v_width, viewport_rect.top(), v_width,
                                       viewport_rect.height())
        self._h_scroll_bar.setGeometry(viewport_rect.left(), viewport_rect.bottom() - h_height, viewport_rect.width(),
                                       h_height)
        self._update_scroll_bars()

    def wheelEvent(self, event):
        """Обрабатывает масштабирование колесом мыши."""
        delta = event.angleDelta().y()
        zoom_factor = self._settings.zoom_step if delta > 0 else 1.0 / self._settings.zoom_step
        self._zoom(zoom_factor)
        event.accept()

    def keyPressEvent(self, event):
        """Обрабатывает горячие клавиши для навигации."""
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            if not self._space_pressed:
                self._space_pressed = True
                self._start_pan_mode()
            event.accept()
        elif event.key() in [Qt.Key_Plus, Qt.Key_Equal]:
            self._zoom(self._settings.zoom_step)
            event.accept()
        elif event.key() == Qt.Key_Minus:
            self._zoom(1.0 / self._settings.zoom_step)
            event.accept()
        elif event.key() == Qt.Key_0:
            self.fit_to_view()
            event.accept()
        elif event.key() == Qt.Key_1:
            self.reset_zoom()
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            if self._space_pressed:
                self._space_pressed = False
                self._stop_pan_mode()
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        """Начинает перетаскивание холста, если включен режим панорамирования."""
        if self._pan_mode and event.button() == Qt.LeftButton:
            self._mouse_pressed = True
            self._last_pan_pos = self.mapToScene(event.pos())
            self.viewport().setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Перемещает холст вслед за курсором."""
        if self._pan_mode and self._mouse_pressed:
            current_pos = self.mapToScene(event.pos())
            delta = current_pos - self._last_pan_pos
            view_center = self.mapToScene(self.viewport().rect().center())
            self.centerOn(view_center - delta)
            self._update_scroll_bars()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._pan_mode and event.button() == Qt.LeftButton:
            self._mouse_pressed = False
            self.viewport().setCursor(Qt.OpenHandCursor)
            self._update_scroll_bars()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        """Устанавливает фокус на виджет при входе курсора."""
        self.setFocus(Qt.MouseFocusReason)
        super().enterEvent(event)