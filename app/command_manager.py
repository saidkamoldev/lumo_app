# app/command_manager.py
# Менеджер для управления историей команд (Undo/Redo) с улучшенной отладкой.

from typing import List
from core.commands import Command


class CommandManager:
    """Управляет стеками команд для Undo и Redo с отладкой и защитой от дублей."""

    def __init__(self, max_history_size: int = 50):
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        self.max_history_size = max_history_size
        self._debug = False  # Включить для отладки

    def execute_command(self, command: Command):
        """Выполняет команду и добавляет ее в историю."""
        if self._debug:
            print(f"🔄 Executing command: {type(command).__name__}")
            print(f"📚 Undo stack before: {len(self.undo_stack)} commands")
            print(f"📚 Redo stack before: {len(self.redo_stack)} commands")

        try:
            # Выполняем команду
            command.execute()

            # Добавляем в стек отмены
            self.undo_stack.append(command)

            # При выполнении новой команды история "Redo" очищается
            if self.redo_stack:
                if self._debug:
                    print(f"🗑️  Clearing redo stack ({len(self.redo_stack)} commands)")
                self.redo_stack.clear()

            # Ограничиваем размер истории
            if len(self.undo_stack) > self.max_history_size:
                removed = self.undo_stack.pop(0)
                if self._debug:
                    print(f"♻️  Removed oldest command: {type(removed).__name__}")

            if self._debug:
                print(f"✅ Command executed successfully")
                print(f"📚 Undo stack after: {len(self.undo_stack)} commands")
                self._print_stack_summary()

        except Exception as e:
            if self._debug:
                print(f"❌ Command execution failed: {e}")
            raise

    def undo(self):
        """Отменяет последнюю выполненную команду."""
        if not self.undo_stack:
            if self._debug:
                print("⚠️  Cannot undo: undo stack is empty")
            return False

        command = self.undo_stack.pop()

        if self._debug:
            print(f"↩️  Undoing command: {type(command).__name__}")
            print(f"📚 Undo stack before: {len(self.undo_stack) + 1} commands")
            print(f"📚 Redo stack before: {len(self.redo_stack)} commands")

        try:
            command.undo()
            self.redo_stack.append(command)

            if self._debug:
                print(f"✅ Undo successful")
                print(f"📚 Undo stack after: {len(self.undo_stack)} commands")
                print(f"📚 Redo stack after: {len(self.redo_stack)} commands")
                self._print_stack_summary()

            return True

        except Exception as e:
            # Если undo не удалось, возвращаем команду в стек
            self.undo_stack.append(command)
            if self._debug:
                print(f"❌ Undo failed: {e}")
            raise

    def redo(self):
        """Повторяет последнюю отмененную команду."""
        if not self.redo_stack:
            if self._debug:
                print("⚠️  Cannot redo: redo stack is empty")
            return False

        command = self.redo_stack.pop()

        if self._debug:
            print(f"↪️  Redoing command: {type(command).__name__}")
            print(f"📚 Undo stack before: {len(self.undo_stack)} commands")
            print(f"📚 Redo stack before: {len(self.redo_stack) + 1} commands")

        try:
            command.execute()
            self.undo_stack.append(command)

            if self._debug:
                print(f"✅ Redo successful")
                print(f"📚 Undo stack after: {len(self.undo_stack)} commands")
                print(f"📚 Redo stack after: {len(self.redo_stack)} commands")
                self._print_stack_summary()

            return True

        except Exception as e:
            # Если redo не удалось, возвращаем команду в стек
            self.redo_stack.append(command)
            if self._debug:
                print(f"❌ Redo failed: {e}")
            raise

    def can_undo(self) -> bool:
        """Проверяет, можно ли выполнить отмену."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Проверяет, можно ли выполнить повтор."""
        return len(self.redo_stack) > 0

    def clear_history(self):
        """Очищает всю историю команд."""
        if self._debug:
            print(f"🧹 Clearing all command history")
            print(f"📚 Clearing {len(self.undo_stack)} undo commands")
            print(f"📚 Clearing {len(self.redo_stack)} redo commands")

        self.undo_stack.clear()
        self.redo_stack.clear()

    def get_undo_count(self) -> int:
        """Возвращает количество команд, доступных для отмены."""
        return len(self.undo_stack)

    def get_redo_count(self) -> int:
        """Возвращает количество команд, доступных для повтора."""
        return len(self.redo_stack)

    def _print_stack_summary(self):
        """Выводит краткую сводку по стекам команд для отладки."""
        if not self._debug:
            return

        print("📊 Stack Summary:")
        print(f"   Undo: {len(self.undo_stack)} commands")
        if self.undo_stack:
            recent_undo = [type(cmd).__name__ for cmd in self.undo_stack[-3:]]
            print(f"   Last undo commands: {recent_undo}")

        print(f"   Redo: {len(self.redo_stack)} commands")
        if self.redo_stack:
            recent_redo = [type(cmd).__name__ for cmd in self.redo_stack[-3:]]
            print(f"   Last redo commands: {recent_redo}")
        print("---")

    def set_debug(self, enabled: bool):
        """Включает/выключает отладочные сообщения."""
        self._debug = enabled
        if enabled:
            print("🐛 Command Manager debug mode enabled")
        else:
            print("🐛 Command Manager debug mode disabled")

    def get_debug_info(self) -> dict:
        """Возвращает информацию о текущем состоянии для отладки."""
        return {
            'undo_count': len(self.undo_stack),
            'redo_count': len(self.redo_stack),
            'undo_commands': [type(cmd).__name__ for cmd in self.undo_stack],
            'redo_commands': [type(cmd).__name__ for cmd in self.redo_stack],
            'can_undo': self.can_undo(),
            'can_redo': self.can_redo()
        }