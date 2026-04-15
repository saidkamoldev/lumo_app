# ui/components/editable_canvas.py
# Супер-оптимизированный интерактивный холст для редактирования макетов стразов.

from typing import List, Optional, Dict, Set
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsView

from core.models import Rhinestone, Project, OutputSettings, Point, CanvasSettings
from app.command_manager import CommandManager
from core.commands import MoveRhinestonesCommand, DeleteRhinestonesCommand, AddRhinestonesCommand
from ui.components.base_canvas import BaseCanvas
from ui.components.hybrid_viewer import CanvasBorderItem


class OptimizedRhinestoneItem(QGraphicsEllipseItem):
    """
    Максимально оптимизированный графический элемент страза.
    """

    def __init__(self, rhinestone: Rhinestone, dpi: float, index: int):
        # Расчет радиуса в пикселях для отображения на экране
        radius_px = (rhinestone.size.diameter_mm * dpi / 25.4) / 2
        super().__init__(-radius_px, -radius_px, radius_px * 2, radius_px * 2)

        self.rhinestone = rhinestone
        self.index = index
        self.setPos(rhinestone.position.x, rhinestone.position.y)

        # Установка цвета без сглаживания для скорости
        self._update_appearance()

        # По умолчанию элемент только выделяемый для максимальной производительности
        self.setFlags(QGraphicsItem.ItemIsSelectable)

        # Отключение кеширования для экономии памяти при большом количестве объектов
        self.setCacheMode(QGraphicsItem.NoCache)

        self._is_being_removed = False

    def _update_appearance(self):
        """Быстрое обновление внешнего вида элемента."""
        color = QColor(self.rhinestone.color.color.r,
                       self.rhinestone.color.color.g,
                       self.rhinestone.color.color.b)
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.NoPen))

    def update_rhinestone_data(self, rhinestone: Rhinestone, new_index: int):
        """
        БЫСТРОЕ обновление данных страза без пересоздания элемента.
        """
        old_rhinestone = self.rhinestone
        self.rhinestone = rhinestone
        self.index = new_index

        # Обновляем только если что-то реально изменилось
        if (old_rhinestone.position.x != rhinestone.position.x or
                old_rhinestone.position.y != rhinestone.position.y):
            self.setPos(rhinestone.position.x, rhinestone.position.y)

        if (old_rhinestone.color.color.r != rhinestone.color.color.r or
                old_rhinestone.color.color.g != rhinestone.color.color.g or
                old_rhinestone.color.color.b != rhinestone.color.color.b):
            self._update_appearance()

        # Проверяем изменение размера
        if old_rhinestone.size.diameter_mm != rhinestone.size.diameter_mm:
            # Пересчитываем радиус только если размер изменился
            from PyQt5.QtWidgets import QGraphicsView
            views = self.scene().views()
            if views:
                canvas = views[0]
                if hasattr(canvas, '_output_settings') and canvas._output_settings:
                    dpi = canvas._output_settings.dpi
                    radius_px = (rhinestone.size.diameter_mm * dpi / 25.4) / 2
                    self.setRect(-radius_px, -radius_px, radius_px * 2, radius_px * 2)

    def enable_interaction(self):
        """Включает полное взаимодействие (перемещение, выделение) для выбранных элементов."""
        if not self._is_being_removed and self.scene() is not None:
            self.setFlags(QGraphicsItem.ItemIsMovable |
                          QGraphicsItem.ItemIsSelectable |
                          QGraphicsItem.ItemSendsGeometryChanges)

    def disable_interaction(self):
        """Отключает взаимодействие для невыбранных элементов для оптимизации."""
        if not self._is_being_removed and self.scene() is not None:
            self.setFlags(QGraphicsItem.ItemIsSelectable)

    def paint(self, painter, option, widget):
        """Переопределенный метод отрисовки для отключения сглаживания."""
        painter.setRenderHint(QPainter.Antialiasing, False)
        super().paint(painter, option, widget)

    def itemChange(self, change, value):
        """Отслеживаем изменения позиции элементов."""
        if (change == QGraphicsItem.ItemPositionHasChanged and
                not self._is_being_removed and
                hasattr(self.scene(), 'views')):
            # Уведомляем холст о том, что элемент был перемещен
            for view in self.scene().views():
                if hasattr(view, '_on_item_moved'):
                    view._on_item_moved(self)
        return super().itemChange(change, value)

    def mark_for_removal(self):
        """Отмечает элемент как удаляемый для предотвращения операций."""
        self._is_being_removed = True


class EditableCanvas(BaseCanvas):
    """
    СУПЕР-ОПТИМИЗИРОВАННЫЙ интерактивный холст для создания и редактирования макетов стразов.
    """
    selectionChanged = pyqtSignal(list)
    projectModified = pyqtSignal(Project)

    def __init__(self, settings: Optional[CanvasSettings] = None, parent=None):
        super().__init__(settings, parent)

        self.command_manager = CommandManager()
        self.setDragMode(self.RubberBandDrag)

        self._rhinestone_items: List[OptimizedRhinestoneItem] = []
        self._project: Optional[Project] = None
        self._output_settings: Optional[OutputSettings] = None

        self._scene.selectionChanged.connect(self._on_selection_changed)

        # Система отслеживания перемещений
        self._move_start_positions = {}
        self._any_item_moved = False
        self._move_timer = QTimer()
        self._move_timer.setSingleShot(True)
        self._move_timer.timeout.connect(self._finalize_move_command)

        # Режим добавления стразов
        self._addition_mode = False
        self._addition_color = None
        self._addition_size = None
        self._set_default_addition_settings()

        self._canvas_border_item: Optional['CanvasBorderItem'] = None
        self._canvas_bounds_visible = True

        # КРИТИЧЕСКАЯ ОПТИМИЗАЦИЯ: Отключаем лишние обновления
        self.setOptimizationFlags(QGraphicsView.DontSavePainterState |
                                  QGraphicsView.DontAdjustForAntialiasing)
        self.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)

        self.setFocusPolicy(Qt.StrongFocus)

    def _set_default_addition_settings(self):
        """Устанавливает настройки по умолчанию для режима добавления."""
        try:
            from core.models import PaletteColor, RGBColor, RhinestoneSize
            self._addition_color = PaletteColor(name="Default Red", color=RGBColor(255, 0, 0))
            self._addition_size = RhinestoneSize(name="SS16", diameter_mm=4.0)
        except Exception as e:
            print(f"Ошибка установки настроек по умолчанию: {e}")

    def set_addition_mode(self, active: bool):
        """Включает/выключает режим добавления страз."""
        self._addition_mode = active
        self.setDragMode(QGraphicsView.NoDrag if active else QGraphicsView.RubberBandDrag)

    def set_addition_color(self, color):
        self._addition_color = color

    def set_addition_size(self, size):
        self._addition_size = size

    def _add_rhinestone_at_position(self, view_pos):
        """БЫСТРОЕ добавление нового страза."""
        if not all([self._project, self._addition_color, self._addition_size]):
            return

        scene_pos = self.mapToScene(view_pos)
        new_rhinestone = Rhinestone(
            position=Point(scene_pos.x(), scene_pos.y()),
            color=self._addition_color,
            size=self._addition_size
        )

        command = AddRhinestonesCommand(self._project, [new_rhinestone])
        self.command_manager.execute_command(command)

        # ОПТИМИЗАЦИЯ: Добавляем только новый элемент вместо полной перестройки
        self._add_new_items_only()
        self._update_project_report()
        self.projectModified.emit(self._project)

    def load_project(self, project: Project, output_settings: OutputSettings):
        """Загружает проект, создавая интерактивные элементы стразов."""
        self._clear_scene()

        self._project = project
        self._output_settings = output_settings

        # Отключаем обновления для производительности при загрузке
        self.setUpdatesEnabled(False)

        for i, rhinestone in enumerate(project.rhinestones):
            item = OptimizedRhinestoneItem(rhinestone, output_settings.dpi, i)
            self._scene.addItem(item)
            self._rhinestone_items.append(item)

        self.setUpdatesEnabled(True)

        self.update_canvas_bounds(output_settings)
        self.fit_to_view(self.sceneRect())
        self._update_project_report()

    def _on_selection_changed(self):
        """Включаем интерактивность для всех выделенных элементов."""
        selected_items = self._scene.selectedItems()

        valid_selected_items = []
        for item in selected_items:
            if isinstance(item, OptimizedRhinestoneItem) and item.scene() is not None:
                valid_selected_items.append(item)

        # ОПТИМИЗАЦИЯ: Блокируем сигналы во время массовых изменений
        self._scene.blockSignals(True)

        # Отключаем интерактивность у всех элементов
        for item in self._rhinestone_items:
            if item.scene() is not None:
                item.disable_interaction()

        # Включаем интерактивность только для валидных выделенных элементов
        for item in valid_selected_items:
            item.enable_interaction()

        self._scene.blockSignals(False)

        # Отправляем сигнал об изменении выделения
        selected_indices = [item.index for item in valid_selected_items]
        self.selectionChanged.emit(selected_indices)

    def mousePressEvent(self, event):
        """Начало операции - запоминаем начальные позиции выделенных элементов."""
        if self._space_pressed and event.button() == Qt.LeftButton:
            super().mousePressEvent(event)
            return

        if self._addition_mode and event.button() == Qt.LeftButton:
            self._add_rhinestone_at_position(event.pos())
            return

        super().mousePressEvent(event)

        if event.button() == Qt.LeftButton:
            QTimer.singleShot(1, self._start_move_tracking)

    def _start_move_tracking(self):
        """Начинает отслеживание перемещения для выделенных элементов."""
        self._move_start_positions.clear()
        self._any_item_moved = False

        selected_items = self._scene.selectedItems()
        for item in selected_items:
            if isinstance(item, OptimizedRhinestoneItem):
                pos = item.pos()
                self._move_start_positions[item.index] = Point(pos.x(), pos.y())

    def _on_item_moved(self, item: OptimizedRhinestoneItem):
        """Вызывается когда элемент был перемещен."""
        if item.index in self._move_start_positions:
            self._any_item_moved = True
            self._move_timer.start(100)

    def _finalize_move_command(self):
        """Создает команду перемещения после завершения операции."""
        if not self._any_item_moved or not self._move_start_positions:
            return

        moves = {}
        for index, old_pos in self._move_start_positions.items():
            if index < len(self._rhinestone_items):
                current_pos = self._rhinestone_items[index].pos()
                new_pos = Point(current_pos.x(), current_pos.y())

                if self._is_significant_move(old_pos, new_pos):
                    moves[index] = new_pos

        if moves and self._project:
            command = MoveRhinestonesCommand(self._project, moves)
            self.command_manager.execute_command(command)
            self._fast_sync_positions_only()  # БЫСТРАЯ синхронизация
            self.projectModified.emit(self._project)

        self._move_start_positions.clear()
        self._any_item_moved = False

    def mouseReleaseEvent(self, event):
        """Обрабатываем завершение операции мыши."""
        if self._space_pressed and event.button() == Qt.LeftButton:
            super().mouseReleaseEvent(event)
            return
        super().mouseReleaseEvent(event)

    def _is_significant_move(self, old_pos: Point, new_pos: Point) -> bool:
        """Проверяет, является ли перемещение значимым."""
        distance = ((new_pos.x - old_pos.x) ** 2 + (new_pos.y - old_pos.y) ** 2) ** 0.5
        return distance > 1.0

    def keyPressEvent(self, event):
        """Обрабатывает горячие клавиши для undo/redo, удаления и навигации."""
        if event.key() == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
            if event.modifiers() & Qt.ShiftModifier:
                self._execute_redo()
            else:
                self._execute_undo()
        elif event.key() == Qt.Key_Delete:
            self._delete_selected()
        else:
            super().keyPressEvent(event)

    def _execute_undo(self):
        """
        ИСПРАВЛЕНИЕ: Отмена последней команды с корректной и надежной синхронизацией UI.
        """
        if not self._project:
            return

        # Сохраняем ссылки на ВЫДЕЛЕННЫЕ объекты, чтобы восстановить выделение после операции
        selected_rhinestones_before = {id(r) for r in self.get_selected_rhinestones()}

        if self.command_manager.undo():
            # После отмены, данные проекта (`self._project`) - единственный источник правды.
            # Мы должны полностью перестроить UI, чтобы он точно соответствовал данным.

            # Находим новые индексы ранее выделенных объектов в обновленном списке стразов
            new_indices_to_select = []
            for i, r_after in enumerate(self._project.rhinestones):
                if id(r_after) in selected_rhinestones_before:
                    new_indices_to_select.append(i)

            # Полная перестройка сцены - самый надежный способ синхронизации после команд,
            # которые меняют состав или порядок элементов (добавление, удаление).
            # Это решает проблему с "месивом" и хаотичными линиями.
            self._full_rebuild_scene(preserve_selection=new_indices_to_select)
            self._update_project_report()
            self.projectModified.emit(self._project)

    def _execute_redo(self):
        """
        ИСПРАВЛЕНИЕ: Повтор отмененной команды с той же надежной синхронизацией UI.
        """
        if not self._project:
            return

        selected_rhinestones_before = {id(r) for r in self.get_selected_rhinestones()}

        if self.command_manager.redo():
            # Та же логика, что и в undo: перестраиваем UI из нового состояния данных
            new_indices_to_select = []
            for i, r_after in enumerate(self._project.rhinestones):
                if id(r_after) in selected_rhinestones_before:
                    new_indices_to_select.append(i)

            self._full_rebuild_scene(preserve_selection=new_indices_to_select)
            self._update_project_report()
            self.projectModified.emit(self._project)

    def _delete_selected(self):
        """
        ИСПРАВЛЕНИЕ: Быстрое удаление выделенных стразов с оптимизацией производительности.
        """
        selected_indices = self.get_selected_indices()
        if not selected_indices or not self._project:
            return

        # Блокируем сигналы сцены на время всей операции для максимальной производительности.
        # Это предотвращает многократный вызов _on_selection_changed, который сильно тормозил процесс.
        self._scene.blockSignals(True)
        try:
            command = DeleteRhinestonesCommand(self._project, selected_indices)
            self.command_manager.execute_command(command)

            # Синхронизируем UI с измененной моделью данных
            self._remove_items_by_indices(selected_indices)
            self._reindex_remaining_items()
            self._update_project_report()
            self.projectModified.emit(self._project)

            # После удаления выделение становится пустым. Отправляем сигнал вручную,
            # чтобы UI (например, тулбар) обновился.
            self.selectionChanged.emit([])

        finally:
            # Обязательно разблокируем сигналы в любом случае, даже если произошла ошибка
            self._scene.blockSignals(False)

    def _smart_sync_after_command(self, preserve_selection: List[int] = None):
        """
        УМНАЯ синхронизация: выбирает оптимальный способ обновления.
        """
        if not self._project or not self._output_settings:
            return

        current_rhinestones_count = len(self._project.rhinestones)
        current_items_count = len(self._rhinestone_items)

        if current_rhinestones_count == current_items_count:
            # Количество не изменилось - быстрое обновление
            self._fast_update_existing_items()
        elif current_rhinestones_count > current_items_count:
            # Добавлены элементы - добавляем только новые
            self._add_new_items_only()
        else:
            # Удалены элементы - требует более сложной обработки
            self._handle_deleted_items()

        if preserve_selection:
            self._restore_selection(preserve_selection)

    def _fast_update_existing_items(self):
        """ИСПРАВЛЕННОЕ быстрое обновление существующих элементов."""
        self.setUpdatesEnabled(False)

        for i, rhinestone in enumerate(self._project.rhinestones):
            if i < len(self._rhinestone_items):
                item = self._rhinestone_items[i]
                item.update_rhinestone_data(rhinestone, i)

        self.setUpdatesEnabled(True)

        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Принудительное обновление отображения
        self._scene.update()
        self.viewport().update()

    def _add_new_items_only(self):
        """Добавляет только новые элементы."""
        current_count = len(self._rhinestone_items)
        total_count = len(self._project.rhinestones)

        if total_count <= current_count:
            return

        self.setUpdatesEnabled(False)

        # Сначала быстро обновляем существующие
        self._fast_update_existing_items()

        # Затем добавляем только новые
        for i in range(current_count, total_count):
            rhinestone = self._project.rhinestones[i]
            item = OptimizedRhinestoneItem(rhinestone, self._output_settings.dpi, i)
            self._scene.addItem(item)
            self._rhinestone_items.append(item)

        self.setUpdatesEnabled(True)

    def _remove_items_by_indices(self, indices_to_remove: List[int]):
        """СУПЕР-БЫСТРОЕ удаление элементов по индексам для больших объемов."""
        if not indices_to_remove:
            return

        self.setUpdatesEnabled(False)

        # КРИТИЧЕСКАЯ ОПТИМИЗАЦИЯ: Используем set для O(1) поиска
        indices_set = set(indices_to_remove)
        items_to_keep = []

        # Одним проходом разделяем элементы на удаляемые и сохраняемые
        for i, item in enumerate(self._rhinestone_items):
            if i in indices_set:
                item.mark_for_removal()
                if item.scene():
                    self._scene.removeItem(item)
            else:
                items_to_keep.append(item)

        # Заменяем список одной операцией
        self._rhinestone_items = items_to_keep

        self.setUpdatesEnabled(True)

    def _reindex_remaining_items(self):
        """БЫСТРОЕ переиндексирование оставшихся элементов."""
        for i, item in enumerate(self._rhinestone_items):
            item.index = i
            # Обновляем ссылку на данные, если нужно
            if i < len(self._project.rhinestones):
                item.rhinestone = self._project.rhinestones[i]

    def _handle_deleted_items(self):
        """Обрабатывает удаленные элементы с умной оптимизацией."""
        # В сложных случаях удаления все же делаем полную перестройку,
        # но только когда это действительно необходимо
        current_rhinestones = {id(r) for r in self._project.rhinestones}

        # Удаляем элементы, данные которых больше нет в проекте
        items_to_remove = []
        for i, item in enumerate(self._rhinestone_items):
            if id(item.rhinestone) not in current_rhinestones:
                items_to_remove.append(i)

        if items_to_remove:
            self._remove_items_by_indices(items_to_remove)
            self._reindex_remaining_items()

    def _fast_sync_positions_only(self):
        """БЫСТРАЯ синхронизация только позиций без пересоздания элементов."""
        if not self._project:
            return

        for i, item in enumerate(self._rhinestone_items):
            if i < len(self._project.rhinestones):
                pos = item.pos()
                self._project.rhinestones[i].position = Point(pos.x(), pos.y())

    def _full_rebuild_scene(self, preserve_selection: List[int] = None):
        """Полная перестройка сцены (используется для надежной синхронизации)."""
        if not self._project or not self._output_settings:
            return

        self.setUpdatesEnabled(False)
        old_transform = self.transform()

        # Очищаем все элементы стразов
        for item in self._rhinestone_items:
            if item.scene():
                item.mark_for_removal()
                self._scene.removeItem(item)
        self._rhinestone_items.clear()

        # Создаем новые элементы из актуальных данных проекта
        for i, rhinestone in enumerate(self._project.rhinestones):
            item = OptimizedRhinestoneItem(rhinestone, self._output_settings.dpi, i)
            self._scene.addItem(item)
            self._rhinestone_items.append(item)

        if preserve_selection:
            valid_selection = [idx for idx in preserve_selection
                               if 0 <= idx < len(self._project.rhinestones)]
            self._restore_selection(valid_selection)

        self.setTransform(old_transform)
        self.setUpdatesEnabled(True)
        # Принудительно обновляем вид, чтобы изменения отобразились сразу
        self._scene.update()
        self.viewport().update()

    def _restore_selection(self, selected_indices: List[int]):
        """Восстанавливает выделение после синхронизации."""
        if not selected_indices:
            self._scene.clearSelection()
            return

        self._scene.blockSignals(True)
        # Сначала снимаем текущее выделение
        self._scene.clearSelection()
        valid_indices = set(selected_indices)
        for item in self._rhinestone_items:
            if (item.index in valid_indices and
                    item.index < len(self._project.rhinestones)):
                item.setSelected(True)
        self._scene.blockSignals(False)
        # Явно вызываем наш обработчик, чтобы включить интерактивность для выделенных элементов
        self._on_selection_changed()

    def _update_project_report(self):
        """Быстрый пересчет статистики проекта."""
        if not self._project:
            return
        from collections import defaultdict
        report_data = defaultdict(int)
        for r in self._project.rhinestones:
            report_data[(r.color.name, r.size.name)] += 1
        self._project.report = dict(report_data)
        self._project.total_count = len(self._project.rhinestones)

    def get_selected_rhinestones(self) -> List[Rhinestone]:
        return [item.rhinestone for item in self._scene.selectedItems()
                if isinstance(item, OptimizedRhinestoneItem)]

    def get_selected_indices(self) -> List[int]:
        return [item.index for item in self._scene.selectedItems()
                if isinstance(item, OptimizedRhinestoneItem)]

    def update_canvas_bounds(self, output_settings: OutputSettings):
        """Обновляет границы холста."""
        if self._canvas_border_item:
            try:
                if self._canvas_border_item.scene():
                    self._scene.removeItem(self._canvas_border_item)
            except RuntimeError:
                pass
            finally:
                self._canvas_border_item = None

        if not output_settings:
            return

        border_rect = QRectF(0, 0, output_settings.width_px, output_settings.height_px)
        self._canvas_border_item = CanvasBorderItem(border_rect)
        self._canvas_border_item.setVisible(self._canvas_bounds_visible)
        self._scene.addItem(self._canvas_border_item)

        scene_rect = border_rect.adjusted(-50, -50, 50, 50)
        self.set_content_rect(scene_rect)

    def set_canvas_bounds_visible(self, visible: bool):
        """Управляет видимостью границ холста."""
        self._canvas_bounds_visible = visible
        if self._canvas_border_item:
            self._canvas_border_item.setVisible(visible)

    def _clear_scene(self):
        """Очищает сцену от всех элементов."""
        self._scene.clearSelection()

        if self._move_timer.isActive():
            self._move_timer.stop()

        self._move_start_positions.clear()
        self._any_item_moved = False

        self.setUpdatesEnabled(False)

        for item in self._rhinestone_items:
            if item.scene():
                item.mark_for_removal()
                self._scene.removeItem(item)
        self._rhinestone_items.clear()

        if self._canvas_border_item:
            try:
                if self._canvas_border_item.scene():
                    self._scene.removeItem(self._canvas_border_item)
            except RuntimeError:
                pass
            finally:
                self._canvas_border_item = None

        self.setUpdatesEnabled(True)

    # Публичные методы для интеграции с презентером
    def undo(self):
        """Публичный метод для отмены."""
        self._execute_undo()

    def redo(self):
        """Публичный метод для повтора."""
        self._execute_redo()

    def delete_selected(self):
        """Публичный метод для удаления выделенных элементов."""
        self._delete_selected()