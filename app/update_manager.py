# app/update_manager.py
import os
import sys
import tempfile
import zipfile
import hashlib
import subprocess
import shutil
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, QThread

from core.models import UpdateInfoResponse
from core.services.update_service import UpdateService


class UpdateWorker(QObject):
    """
    Worker для выполнения задач обновления (загрузка, распаковка) в отдельном потоке.
    """
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int)

    def __init__(self, update_service: UpdateService, update_info: UpdateInfoResponse):
        super().__init__()
        self.update_service = update_service
        self.update_info = update_info
        self.temp_dir = tempfile.mkdtemp(prefix="lumo_update_")
        print(f"[LOG] Создана временная директория: {self.temp_dir}")

    def run(self):
        """Выполняет полный цикл загрузки и подготовки обновления."""
        try:
            print("[LOG] Начинаем процесс обновления...")

            # 1. Загрузка
            print("[LOG] Начинаем загрузку обновления...")
            self.progress.emit(0)
            success, file_data, message = self.update_service.download_update(
                self.update_info.version,
                lambda p: self.progress.emit(p)
            )
            if not success or not file_data:
                print(f"[ERROR] Ошибка загрузки: {message}")
                self.finished.emit(False, f"Ошибка загрузки: {message}")
                return

            print(f"[LOG] Загрузка завершена. Размер файла: {len(file_data)} байт")
            self.progress.emit(100)

            # 2. Проверка хеша
            print("[LOG] Проверяем контрольную сумму...")
            downloaded_hash = hashlib.sha256(file_data).hexdigest()
            expected_hash = self.update_info.file_hash.lower() if self.update_info.file_hash else ""
            print(f"[LOG] Скачанный хеш: {downloaded_hash}")
            print(f"[LOG] Ожидаемый хеш: {expected_hash}")

            if expected_hash and downloaded_hash.lower() != expected_hash:
                print("[ERROR] Контрольная сумма файла не совпадает!")
                self.finished.emit(False, "Ошибка: контрольная сумма файла не совпадает.")
                return

            # 3. Сохранение и распаковка
            print("[LOG] Сохраняем и распаковываем архив...")
            zip_path = os.path.join(self.temp_dir, "update.zip")
            with open(zip_path, "wb") as f:
                f.write(file_data)
            print(f"[LOG] Архив сохранен: {zip_path}")

            # Создаем папку для распакованных файлов
            extract_dir = os.path.join(self.temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            print(f"[LOG] Архив распакован в: {extract_dir}")

            # Удаляем zip файл после распаковки
            os.remove(zip_path)
            print("[LOG] Zip файл удален")

            # 4. Создание скрипта-установщика
            print("[LOG] Создаем скрипт установки...")
            self._create_updater_script(extract_dir)

            print("[LOG] Подготовка обновления завершена успешно")
            self.finished.emit(True, self.temp_dir)

        except Exception as e:
            print(f"[ERROR] Критическая ошибка в процессе обновления: {e}")
            self.finished.emit(False, f"Критическая ошибка: {e}")

    def _create_updater_script(self, extract_dir):
        """Создает .bat скрипт для замены файлов и перезапуска."""
        # Определяем путь к приложению - только для EXE режима
        if getattr(sys, 'frozen', False):
            # Если это скомпилированный exe файл
            app_path = os.path.dirname(sys.executable)
            app_name = os.path.basename(sys.executable)
            print(f"[LOG] Режим EXE. Путь приложения: {app_path}")
            print(f"[LOG] EXE файл: {app_name}")
        else:
            # Если это Python скрипт - используем путь где должен быть EXE
            current_dir = os.path.dirname(os.path.abspath(__file__))
            app_path = os.path.dirname(current_dir)  # Поднимаемся на уровень выше из app/
            app_name = "Lumo.exe"
            print(f"[LOG] Режим разработки. Путь приложения: {app_path}")
            print(f"[LOG] EXE файл: {app_name}")

        restart_command = f'start "" "{os.path.join(app_path, app_name)}"'
        print(f"[LOG] Путь для копирования файлов: {app_path}")
        print(f"[LOG] Источник файлов: {extract_dir}")

        # Проверяем, что есть файлы для копирования
        if os.path.exists(extract_dir):
            files_to_copy = os.listdir(extract_dir)
            print(f"[LOG] Файлы для копирования: {files_to_copy}")
        else:
            print(f"[ERROR] Директория с файлами не найдена: {extract_dir}")

        script_content = f"""@echo off
chcp 65001 >nul 2>&1

REM Завершаем процесс Lumo.exe
taskkill /IM "Lumo.exe" /F >nul 2>&1

REM Ожидание 3 секунды
timeout /t 3 /nobreak >nul 2>&1

REM Проверяем существование источника
if not exist "{extract_dir}" (
    exit /b 1
)

REM Копируем файлы с заменой в директорию где лежит EXE
xcopy "{extract_dir}\\*" "{app_path}\\" /E /Y /I /Q >nul 2>&1
set COPY_RESULT=%errorlevel%

REM Дополнительное ожидание после копирования для синхронизации файловой системы
timeout /t 5 /nobreak >nul 2>&1

REM Очистка временных файлов
REM rmdir /S /Q "{self.temp_dir}" >nul 2>&1

REM Еще одно ожидание перед запуском
timeout /t 2 /nobreak >nul 2>&1

REM Запуск обновленного EXE файла с полным путем
cd /d "{app_path}"
set EXE_PATH="{os.path.join(app_path, app_name)}"
if exist %EXE_PATH% (
    REM Запускаем через start с полным путем без окна консоли
    start "" /D "{app_path}" %EXE_PATH%
)

REM Удаляем батник только если все прошло успешно
if %COPY_RESULT% EQU 0 (
    del "%~f0"
)
"""
        script_path = os.path.join(self.temp_dir, "updater.bat")
        with open(script_path, "w", encoding='utf-8') as f:
            f.write(script_content)
        print(f"[LOG] Скрипт установки создан: {script_path}")


class UpdateManager(QObject):
    """
    Управляет процессом обновления приложения.
    """
    update_check_finished = pyqtSignal(bool, object, str)  # success, UpdateInfoResponse, message
    update_process_finished = pyqtSignal(bool, str)  # success, message
    update_progress = pyqtSignal(int)

    def __init__(self, update_service: UpdateService):
        super().__init__()
        self.update_service = update_service
        self._thread: Optional[QThread] = None
        self._worker: Optional[UpdateWorker] = None

    def check_for_updates(self):
        """Асинхронно проверяет наличие обновлений."""
        print("[LOG] Проверка обновлений...")
        success, info, message = self.update_service.check_for_updates()
        print(f"[LOG] Результат проверки: success={success}, message={message}")
        if info:
            print(f"[LOG] Доступно обновление до версии: {info.version}")
        self.update_check_finished.emit(success, info, message)

    def start_update(self, update_info: UpdateInfoResponse):
        """Запускает процесс загрузки и установки обновления."""
        print(f"[LOG] Начинаем процесс обновления до версии {update_info.version}")

        self._thread = QThread()
        self._worker = UpdateWorker(self.update_service, update_info)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_update_finished)
        self._worker.progress.connect(self.update_progress.emit)

        self._thread.start()

    def _on_update_finished(self, success: bool, result_path_or_message: str):
        """Обрабатывает завершение процесса обновления."""
        if success:
            print(f"[LOG] Обновление подготовлено успешно в: {result_path_or_message}")
            # Запускаем скрипт обновления
            updater_script = os.path.join(result_path_or_message, "updater.bat")
            if os.path.exists(updater_script):
                print(f"[LOG] Запускаем скрипт обновления: {updater_script}")
                try:
                    # Скрытый запуск BAT файла
                    process = subprocess.Popen(
                        f'"{updater_script}"',
                        shell=True,
                        cwd=os.path.dirname(updater_script)
                    )
                    print(f"[LOG] Скрипт обновления запущен")
                    self.update_process_finished.emit(True, "Перезапуск для обновления...")
                except Exception as e:
                    print(f"[ERROR] Ошибка запуска скрипта обновления: {e}")
                    # Попробуем альтернативный способ запуска
                    try:
                        print("[LOG] Пробуем альтернативный способ запуска...")
                        os.startfile(updater_script)
                        print("[LOG] Скрипт запущен через os.startfile")
                        self.update_process_finished.emit(True, "Перезапуск для обновления...")
                    except Exception as e2:
                        print(f"[ERROR] Альтернативный запуск тоже не сработал: {e2}")
                        self.update_process_finished.emit(False, f"Ошибка запуска обновления: {e}")
            else:
                print(f"[ERROR] Скрипт обновления не найден: {updater_script}")
                self.update_process_finished.emit(False, "Скрипт обновления не найден.")
        else:
            print(f"[ERROR] Обновление завершилось с ошибкой: {result_path_or_message}")
            self.update_process_finished.emit(False, result_path_or_message)

        # Очищаем ресурсы потока
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
            self._worker = None