# ui/theme/theme_manager.py
# Управляет загрузкой и применением файлов стилей (.qss).

import os
import sys
from PyQt5.QtCore import QObject, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel

def resource_path(relative_path):
    """ 
    PyInstaller va oddiy Python muhiti uchun fayl yo'lini aniqlaydi.
    Oddiy run va .exe o'rtasidagi farqni avtomatik hal qiladi. 
    """
    try:
        # PyInstaller vaqtinchalik papka yaratadi (_MEIPASS) 
        base_path = sys._MEIPASS
    except Exception:
        # Agar oddiy python main.py bo'lsa, loyiha ildiz papkasini oladi
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class ThemeManager(QObject):
    """
    Загружает файлы стилей (.qss) и применяет их к приложению.
    Управляет переключением между светлой и темной темами.
    """
    themeChanged = pyqtSignal(str)  # 'dark' or 'light'

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.current_theme = 'dark'
        
        # Temalar joylashgan papkaga to'liq va xatosiz yo'l [cite: 5, 8, 9]
        # ui/theme papkasini loyiha ildiziga nisbatan qidiradi
        self.themes_dir = resource_path(os.path.join("ui", "theme"))
        
        # Debug uchun terminalda yo'lni ko'rsatamiz
        print(f"[DEBUG] Mavzular papkasi: {self.themes_dir}")

    def apply_theme(self, theme_name: str):
        """Загружает и применяет .qss файл темы ко всему приложению."""
        if theme_name not in ['dark', 'light']:
            print(f"Ошибка: Тема '{theme_name}' не найдена.")
            return

        # Fayl nomini yasash va to'liq yo'lni aniqlash
        qss_file_name = f"{theme_name}_theme.qss"
        qss_file_path = os.path.join(self.themes_dir, qss_file_name)

        # DEBUG: Qayerdan fayl qidirayotganini ko'rish uchun 
        print(f"[DEBUG] Yuklanayotgan fayl: {qss_file_path}")

        if not os.path.exists(qss_file_path):
            print(f"КРИТИЧЕСКАЯ ОШИБКА: Файл темы не найден по адресу: {qss_file_path}")
            return

        try:
            with open(qss_file_path, "r", encoding="utf-8") as f:
                stylesheet = f.read()
                self.app.setStyleSheet(stylesheet)
                self.current_theme = theme_name
                self.themeChanged.emit(theme_name)
                print(f"Тема '{theme_name}' успешно применена.")
        except Exception as e:
            print(f"Ошибка при применении темы: {e}")

    def toggle_theme(self, animate: bool = True):
        """Переключает между темной и светлой темой."""
        next_theme = 'light' if self.current_theme == 'dark' else 'dark'

        if not animate or not self.app.activeWindow():
            self.apply_theme(next_theme)
            return

        # Анимация смены темы
        window = self.app.activeWindow()
        pixmap = QPixmap(window.size())
        window.render(pixmap)
        overlay = QLabel(window)
        overlay.setPixmap(pixmap)
        overlay.setGeometry(window.rect())
        overlay.show()

        self.apply_theme(next_theme)

        animation = QPropertyAnimation(overlay, b"windowOpacity")
        animation.setDuration(400)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.finished.connect(overlay.deleteLater)
        animation.start()
        
        self._current_animation = animation

    def get_canvas_color(self) -> QColor:
        """Возвращает подходящий цвет холста для текущей темы."""
        return QColor("#2D2D2D") if self.current_theme == 'dark' else QColor("#FFFFFF")

    def is_dark(self) -> bool:
        return self.current_theme == 'dark'