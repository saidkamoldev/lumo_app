# core/services/update_service.py
import requests
from typing import Optional, Tuple, Callable
import threading
import time

from ..models import AppSettings, UpdateInfoResponse


class UpdateService:
    """
    Сервис для взаимодействия с API обновлений на сервере.
    Полностью асинхронный без блокировок UI.
    """

    def __init__(self, app_settings: AppSettings):
        self.settings = app_settings
        self.base_url = self.settings.update_server_url.rstrip('/')
        self._cancel_download = False

    def check_for_updates(self) -> Tuple[bool, Optional[UpdateInfoResponse], str]:
        """
        Проверяет наличие обновлений на сервере.
        Возвращает (успех, информация об обновлении, сообщение об ошибке/статусе).
        """
        check_url = f"{self.base_url}/updates/check"
        payload = {"current_version": self.settings.current_version}

        try:
            response = requests.post(
                check_url,
                json=payload,
                timeout=10,
                verify=True,
                headers={
                    'User-Agent': f'Lumo/{self.settings.current_version}',
                    'Content-Type': 'application/json'
                }
            )
            response.raise_for_status()

            data = response.json()
            update_info = UpdateInfoResponse(**data)

            if update_info.update_available:
                return True, update_info, f"Доступна новая версия: {update_info.version}"
            else:
                return True, None, "У вас установлена последняя версия."

        except requests.exceptions.ConnectionError:
            return False, None, "Нет подключения к серверу обновлений."
        except requests.exceptions.Timeout:
            return False, None, "Таймаут при проверке обновлений."
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "неизвестно"
            return False, None, f"Ошибка сервера: {status_code}"
        except requests.exceptions.RequestException as e:
            return False, None, f"Ошибка сети: {str(e)}"
        except Exception as e:
            return False, None, f"Неизвестная ошибка: {str(e)}"

    def download_update(self, version: str, progress_callback: Optional[Callable[[int], None]] = None) -> Tuple[
        bool, Optional[bytes], str]:
        """
        Загружает файл обновления с сервера асинхронно с прогрессом.
        Возвращает (успех, данные файла, сообщение об ошибке).
        """
        download_url = f"{self.base_url}/updates/download/{version}"
        self._cancel_download = False

        try:
            # Используем stream=True для асинхронной загрузки
            with requests.get(
                    download_url,
                    stream=True,
                    timeout=30,  # Timeout для начального соединения
                    verify=True,
                    headers={
                        'User-Agent': f'Lumo/{self.settings.current_version}',
                        'Accept': 'application/octet-stream'
                    }
            ) as response:
                response.raise_for_status()

                # Получаем размер файла
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0

                # Буфер для данных
                content = bytearray()

                # Читаем данные чанками для асинхронности
                chunk_size = 8192  # 8KB chunks
                last_progress_time = 0

                for chunk in response.iter_content(chunk_size=chunk_size):
                    # Проверяем отмену
                    if self._cancel_download:
                        return False, None, "Загрузка отменена пользователем."

                    if chunk:  # фильтруем keep-alive chunks
                        content.extend(chunk)
                        downloaded_size += len(chunk)

                        # Обновляем прогресс не чаще чем раз в 100ms для плавности
                        current_time = time.time()
                        if progress_callback and (current_time - last_progress_time) > 0.1:
                            if total_size > 0:
                                progress = min(100, int((downloaded_size / total_size) * 100))
                                progress_callback(progress)
                            last_progress_time = current_time

                # Финальный прогресс 100%
                if progress_callback:
                    progress_callback(100)

                return True, bytes(content), "Загрузка завершена успешно."

        except requests.exceptions.ConnectionError:
            return False, None, "Потеряно подключение к серверу во время загрузки."
        except requests.exceptions.Timeout:
            return False, None, "Таймаут при загрузке файла обновления."
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "неизвестно"
            if status_code == 404:
                return False, None, f"Версия {version} не найдена на сервере."
            elif status_code == 403:
                return False, None, "Доступ к загрузке обновления запрещен."
            else:
                return False, None, f"Ошибка сервера при загрузке: {status_code}"
        except requests.exceptions.RequestException as e:
            return False, None, f"Ошибка сети при загрузке: {str(e)}"
        except MemoryError:
            return False, None, "Недостаточно памяти для загрузки обновления."
        except Exception as e:
            return False, None, f"Критическая ошибка при загрузке: {str(e)}"

    def cancel_download(self):
        """
        Отменяет текущую загрузку.
        Можно вызывать из любого потока.
        """
        self._cancel_download = True

    def download_update_async(self, version: str, progress_callback: Optional[Callable[[int], None]] = None,
                              completion_callback: Optional[Callable[[bool, Optional[bytes], str], None]] = None):
        """
        Асинхронная версия download_update с колбэками.
        Запускает загрузку в отдельном потоке.
        """

        def download_worker():
            try:
                success, data, message = self.download_update(version, progress_callback)
                if completion_callback:
                    completion_callback(success, data, message)
            except Exception as e:
                if completion_callback:
                    completion_callback(False, None, f"Ошибка в потоке загрузки: {str(e)}")

        # Запускаем в daemon потоке, чтобы не блокировать выход из приложения
        thread = threading.Thread(target=download_worker, daemon=True)
        thread.start()
        return thread

    def get_update_info(self, version: str) -> Tuple[bool, Optional[UpdateInfoResponse], str]:
        """
        Получает детальную информацию о конкретной версии.
        """
        info_url = f"{self.base_url}/updates/info/{version}"

        try:
            response = requests.get(
                info_url,
                timeout=10,
                verify=True,
                headers={
                    'User-Agent': f'Lumo/{self.settings.current_version}',
                    'Accept': 'application/json'
                }
            )
            response.raise_for_status()

            data = response.json()
            update_info = UpdateInfoResponse(**data)
            return True, update_info, "Информация получена успешно."

        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 404:
                return False, None, f"Версия {version} не найдена."
            return False, None, f"Ошибка сервера: {e.response.status_code if e.response else 'неизвестно'}"
        except requests.exceptions.RequestException as e:
            return False, None, f"Ошибка сети: {str(e)}"
        except Exception as e:
            return False, None, f"Неизвестная ошибка: {str(e)}"

    def verify_server_connection(self) -> Tuple[bool, str]:
        """
        Проверяет доступность сервера обновлений.
        Полезно для диагностики проблем с сетью.
        """
        ping_url = f"{self.base_url}/ping"

        try:
            response = requests.get(
                ping_url,
                timeout=5,
                verify=True,
                headers={'User-Agent': f'Lumo/{self.settings.current_version}'}
            )
            response.raise_for_status()

            return True, "Сервер обновлений доступен."

        except requests.exceptions.ConnectionError:
            return False, "Не удается подключиться к серверу обновлений."
        except requests.exceptions.Timeout:
            return False, "Сервер обновлений не отвечает (таймаут)."
        except requests.exceptions.HTTPError as e:
            return False, f"Ошибка сервера: {e.response.status_code if e.response else 'неизвестно'}"
        except Exception as e:
            return False, f"Ошибка проверки соединения: {str(e)}"

    def set_server_url(self, new_url: str):
        """
        Изменяет URL сервера обновлений.
        Полезно для переключения между prod/test серверами.
        """
        self.base_url = new_url.rstrip('/')
        self.settings.update_server_url = new_url