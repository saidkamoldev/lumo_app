# core/licensing/license_utils.py
# Утилиты для работы с лицензиями

import re
import hashlib
import base64
from typing import Optional
from cryptography.fernet import Fernet


class CryptoUtils:
    """Утилиты для шифрования/дешифрования."""

    @staticmethod
    def _generate_key_from_seed(seed_string: str) -> bytes:
        """Генерирует ключ Fernet из строки-семени."""
        digest = hashlib.sha256(seed_string.encode()).digest()
        return base64.urlsafe_b64encode(digest[:32])

    @staticmethod
    def decrypt_string(encrypted_data: str, seed: str) -> str:
        """Дешифрует строку используя семя."""
        try:
            key = CryptoUtils._generate_key_from_seed(seed)
            f = Fernet(key)
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted = f.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception:
            return ""


class LicenseKeyValidator:
    """Валидатор лицензионных ключей."""

    @staticmethod
    def is_valid_format(license_key: str) -> bool:
        """
        Проверяет формат лицензионного ключа.
        Ожидаемый формат: XXXX-XXXX-XXXX-XXXX (где X - буква или цифра)
        """
        if not license_key:
            return False

        # Убираем пробелы и переводим в верхний регистр
        clean_key = license_key.strip().upper()

        # Проверяем формат через регулярное выражение
        pattern = r'^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}'
        return bool(re.match(pattern, clean_key))

    @staticmethod
    def normalize_key(license_key: str) -> str:
        """Нормализует лицензионный ключ (убирает пробелы, приводит к верхнему регистру)."""
        return license_key.strip().upper().replace(' ', '')

    @staticmethod
    def generate_checksum(data: str) -> str:
        """Генерирует контрольную сумму для данных."""
        return hashlib.sha256(data.encode()).hexdigest()[:8].upper()


class HardwareInfo:
    """Класс для получения информации об оборудовании."""

    @staticmethod
    def get_system_info() -> dict:
        """Возвращает подробную информацию о системе."""
        import platform
        import socket

        info = {
            'system': platform.system(),
            'node': platform.node(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
        }

        try:
            info['hostname'] = socket.gethostname()
            info['ip'] = socket.gethostbyname(socket.gethostname())
        except:
            info['hostname'] = 'unknown'
            info['ip'] = 'unknown'

        return info