# core/commands.py
# Исправленная реализация паттерна "Команда" для корректной работы с индексами.

from abc import ABC, abstractmethod
from typing import List, Dict, Any

from .models import Project, Point, Rhinestone, PaletteColor, RhinestoneSize


class Command(ABC):
    """Абстрактный базовый класс для всех команд."""

    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def undo(self):
        pass


class MoveRhinestonesCommand(Command):
    """
    Команда для перемещения стразов.
    Правильно работает с undo/redo и синхронизацией UI.
    """

    def __init__(self, project: Project, moves: Dict[int, Point]):
        self.project = project
        # Сохраняем старые и новые позиции для каждого страза
        self.moves_data = []

        # Конвертируем индексы в стабильные данные
        for index, new_pos in moves.items():
            if 0 <= index < len(project.rhinestones):
                rhinestone = project.rhinestones[index]
                old_pos = Point(rhinestone.position.x, rhinestone.position.y)
                self.moves_data.append({
                    'rhinestone': rhinestone,
                    'index': index,
                    'old_pos': old_pos,
                    'new_pos': new_pos
                })

    def execute(self):
        """Применяет новые позиции к стразам."""
        for move_data in self.moves_data:
            rhinestone = move_data['rhinestone']
            new_pos = move_data['new_pos']
            rhinestone.position = new_pos

    def undo(self):
        """Восстанавливает старые позиции стразов."""
        for move_data in self.moves_data:
            rhinestone = move_data['rhinestone']
            old_pos = move_data['old_pos']
            rhinestone.position = old_pos


class DeleteRhinestonesCommand(Command):
    """
    СУПЕР-ОПТИМИЗИРОВАННАЯ команда для удаления стразов.
    Эффективно работает с большими объемами (700+ элементов).
    """

    def __init__(self, project: Project, indices: List[int]):
        self.project = project
        # ОПТИМИЗАЦИЯ: Используем set для быстрого поиска
        self.indices_set = set(indices)
        # Сохраняем элементы для восстановления в правильном порядке
        self.deleted_rhinestones: List[tuple] = []
        # Сохраняем также новый список для быстрого восстановления
        self.original_rhinestones = None

    def execute(self):
        """БЫСТРОЕ удаление стразов из проекта."""
        # Сохраняем оригинальный список для undo
        self.original_rhinestones = self.project.rhinestones.copy()

        # Очищаем список сохраненных элементов
        self.deleted_rhinestones.clear()

        # КРИТИЧЕСКАЯ ОПТИМИЗАЦИЯ: Создаем новый список вместо множественных pop()
        new_rhinestones = []

        for i, rhinestone in enumerate(self.project.rhinestones):
            if i in self.indices_set:
                # Сохраняем для восстановления
                self.deleted_rhinestones.append((i, rhinestone))
            else:
                # Оставляем в новом списке
                new_rhinestones.append(rhinestone)

        # Заменяем весь список одной операцией
        self.project.rhinestones = new_rhinestones

    def undo(self):
        """БЫСТРОЕ восстановление удаленных стразов."""
        if self.original_rhinestones is not None:
            # СУПЕР-БЫСТРОЕ восстановление: просто возвращаем оригинальный список
            self.project.rhinestones = self.original_rhinestones.copy()
        else:
            # Fallback: восстанавливаем по сохраненным элементам
            # Сортируем по оригинальным индексам для правильного порядка
            for original_index, rhinestone in sorted(self.deleted_rhinestones, key=lambda x: x[0]):
                # Проверяем, что индекс все еще валиден
                if original_index <= len(self.project.rhinestones):
                    self.project.rhinestones.insert(original_index, rhinestone)
                else:
                    # Если индекс больше текущего размера, добавляем в конец
                    self.project.rhinestones.append(rhinestone)


class AddRhinestonesCommand(Command):
    """
    ИСПРАВЛЕННАЯ команда для добавления новых стразов.
    Отслеживает позицию добавления для правильной отмены.
    """

    def __init__(self, project: Project, new_rhinestones: List[Rhinestone]):
        self.project = project
        self.new_rhinestones = new_rhinestones
        # Запоминаем позицию, с которой начинаем добавление
        self.start_index = len(project.rhinestones)

    def execute(self):
        """Добавляет стразы в конец списка."""
        self.project.rhinestones.extend(self.new_rhinestones)

    def undo(self):
        """Удаляет добавленные стразы с конца списка."""
        # Удаляем точно столько элементов, сколько добавили, начиная с того места где добавляли
        for _ in self.new_rhinestones:
            if len(self.project.rhinestones) > self.start_index:
                removed = self.project.rhinestones.pop()

class ChangeRhinestonePropertyCommand(Command):
    """
    ИСПРАВЛЕННЫЙ базовый класс для команд изменения свойств.
    Использует ссылки на объекты вместо индексов.
    """

    def __init__(self, project: Project, indices: List[int], new_value: Any):
        self.project = project
        self.new_value = new_value
        # Сохраняем пары: (ссылка_на_страз, старое_значение)
        self.changes = []

        # Конвертируем индексы в ссылки на объекты
        for index in indices:
            if 0 <= index < len(project.rhinestones):
                rhinestone = project.rhinestones[index]
                old_value = self._get_property(rhinestone)
                self.changes.append((rhinestone, old_value))

        property_name = self.__class__.__name__.replace('ChangeRhinestone', '').replace('Command', '')

    def _get_property(self, rhinestone: Rhinestone) -> Any:
        """Этот метод должны переопределить дочерние классы."""
        raise NotImplementedError

    def _set_property(self, rhinestone: Rhinestone, value: Any):
        """Этот метод должны переопределить дочерние классы."""
        raise NotImplementedError

    def execute(self):
        """Применяет новое значение свойства."""
        for rhinestone, _ in self.changes:
            self._set_property(rhinestone, self.new_value)

    def undo(self):
        """Восстанавливает старые значения свойств."""
        for rhinestone, old_value in self.changes:
            self._set_property(rhinestone, old_value)


class ChangeRhinestoneColorCommand(ChangeRhinestonePropertyCommand):
    """Команда для изменения цвета стразов."""

    def __init__(self, project: Project, indices: List[int], new_color: PaletteColor):
        super().__init__(project, indices, new_color)

    def _get_property(self, rhinestone: Rhinestone) -> PaletteColor:
        return rhinestone.color

    def _set_property(self, rhinestone: Rhinestone, value: PaletteColor):
        rhinestone.color = value


class ChangeRhinestoneSizeCommand(ChangeRhinestonePropertyCommand):
    """Команда для изменения размера стразов."""

    def __init__(self, project: Project, indices: List[int], new_size: RhinestoneSize):
        super().__init__(project, indices, new_size)

    def _get_property(self, rhinestone: Rhinestone) -> RhinestoneSize:
        return rhinestone.size

    def _set_property(self, rhinestone: Rhinestone, value: RhinestoneSize):
        rhinestone.size = value