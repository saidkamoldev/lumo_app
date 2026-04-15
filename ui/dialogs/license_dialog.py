import sys
import webbrowser
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QProgressBar, QFrame, QApplication
)
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPalette
from core.licensing.license_manager import LicenseManager


class LicenseValidationWorker(QThread):
    """Worker для проверки лицензии в отдельном потоке."""

    validation_complete = pyqtSignal(bool, str, int)  # success, message, error_code

    def __init__(self, license_manager: LicenseManager, license_key: str, is_activation: bool = False):
        super().__init__()
        self.license_manager = license_manager
        self.license_key = license_key
        self.is_activation = is_activation

    def run(self):
        try:
            success, message = self.license_manager.validate_license_online(self.license_key)
            # Извлекаем код ошибки из сообщения если есть
            error_code = 0
            if not success and "Ошибка сервера:" in message:
                try:
                    error_code = int(message.split("Ошибка сервера: ")[1].split(" ")[0])
                except:
                    error_code = 500
            elif not success:
                error_code = 400

            self.validation_complete.emit(success, message, error_code)
        except Exception as e:
            self.validation_complete.emit(False, f"Критическая ошибка: {str(e)}", 999)


class LicenseDialog(QDialog):
    """Диалог активации лицензии с статус баром."""

    def __init__(self, license_manager: LicenseManager, parent=None):
        super().__init__(parent)
        self.license_manager = license_manager
        self.validation_worker = None

        self.setWindowTitle("Активация лицензии - Lumo")
        self.setFixedSize(550, 520)  # Увеличен размер для статус бара
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.MSWindowsFixedSizeDialogHint)
        self.setModal(True)

        self._init_ui()
        self._apply_styles()
        self._set_status("Введите лицензионный ключ для активации")

    def _init_ui(self):
        """Инициализирует интерфейс диалога."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(35, 30, 35, 20)

        # --- Заголовок ---
        title_label = QLabel("Активация лицензии")
        title_label.setObjectName("licenseTitle")
        title_label.setAlignment(Qt.AlignCenter)

        subtitle_label = QLabel("Для продолжения работы с Lumo введите ваш лицензионный ключ.")
        subtitle_label.setObjectName("licenseSubtitle")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setWordWrap(True)

        header_layout = QVBoxLayout()
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.setSpacing(5)

        # --- Идентификатор ---
        id_group_layout = QVBoxLayout()
        id_group_layout.setSpacing(5)

        id_label = QLabel("Ваш ID для получения ключа:")
        id_label.setObjectName("licenseIdLabel")

        id_field_layout = QHBoxLayout()
        self.id_display = QLineEdit()
        self.id_display.setReadOnly(True)
        self.id_display.setText(self.license_manager.get_encrypted_identifier())
        self.id_display.setObjectName("licenseIdField")
        self.id_display.setCursorPosition(0)

        self.copy_button = QPushButton("Копировать ID")
        self.copy_button.setObjectName("licenseCopyButton")
        self.copy_button.clicked.connect(self._copy_identifier)
        self.copy_button.setCursor(Qt.PointingHandCursor)

        id_field_layout.addWidget(self.id_display, 1)
        id_field_layout.addWidget(self.copy_button)
        id_group_layout.addWidget(id_label)
        id_group_layout.addLayout(id_field_layout)

        # --- Поле ввода ключа ---
        key_group_layout = QVBoxLayout()
        key_group_layout.setSpacing(5)
        key_label = QLabel("Лицензионный ключ:")
        key_label.setObjectName("licenseKeyLabel")

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_input.setObjectName("licenseKeyField")
        self.key_input.returnPressed.connect(self._validate_license)
        self.key_input.textChanged.connect(self._on_key_text_changed)

        key_group_layout.addWidget(key_label)
        key_group_layout.addWidget(self.key_input)

        # --- Прогресс-бар ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setObjectName("licenseProgress")
        self.progress_bar.setTextVisible(False)

        # --- Кнопки ---
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        self.buy_button = QPushButton("Получить ключ")
        self.buy_button.setObjectName("licenseBuyButton")
        self.buy_button.clicked.connect(self._open_purchase_link)
        self.buy_button.setCursor(Qt.PointingHandCursor)

        self.ok_button = QPushButton("Активировать")
        self.ok_button.setObjectName("licenseOkButton")
        self.ok_button.clicked.connect(self._validate_license)
        self.ok_button.setDefault(True)
        self.ok_button.setCursor(Qt.PointingHandCursor)

        button_layout.addWidget(self.buy_button)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)

        # --- Статус бар ---
        self.status_label = QLabel()
        self.status_label.setObjectName("licenseStatusBar")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(40)

        # --- Сборка интерфейса ---
        main_layout.addLayout(header_layout)
        main_layout.addWidget(QFrame(frameShape=QFrame.HLine, objectName="licenseSeparator"))
        main_layout.addSpacing(10)
        main_layout.addLayout(id_group_layout)
        main_layout.addSpacing(10)
        main_layout.addLayout(key_group_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addStretch(1)
        main_layout.addLayout(button_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.status_label)

    def _set_status(self, message: str, status_type: str = "info"):
        """Устанавливает сообщение в статус баре."""
        self.status_label.setText(message)

        # Меняем стиль в зависимости от типа
        if status_type == "error":
            self.status_label.setObjectName("licenseStatusBarError")
        elif status_type == "success":
            self.status_label.setObjectName("licenseStatusBarSuccess")
        elif status_type == "loading":
            self.status_label.setObjectName("licenseStatusBarLoading")
        else:
            self.status_label.setObjectName("licenseStatusBar")

        # Перепременяем стили
        self.status_label.setStyleSheet(self.styleSheet())

    def _on_key_text_changed(self):
        """Обработчик изменения текста в поле ключа."""
        if self.status_label.text().startswith("Ошибка"):
            self._set_status("Введите лицензионный ключ для активации")

    def _copy_identifier(self):
        """Копирует полный идентификатор в буфер обмена."""
        QApplication.clipboard().setText(self.license_manager.get_encrypted_identifier())
        original_text = self.copy_button.text()
        self.copy_button.setText("Скопировано!")
        self.copy_button.setEnabled(False)
        self._set_status("ID скопирован в буфер обмена", "success")
        QTimer.singleShot(2000, lambda: (
            self.copy_button.setText(original_text),
            self.copy_button.setEnabled(True),
            self._set_status("Введите лицензионный ключ для активации")
        ))

    def _open_purchase_link(self):
        """Открывает ссылку для покупки лицензии."""
        telegram_url = "https://t.me/ivangazul"
        webbrowser.open(telegram_url)
        self._set_status("Ссылка для покупки открыта в браузере", "info")

    def _validate_license(self):
        """Валидирует введенный лицензионный ключ."""
        license_key = self.key_input.text().strip()
        if not license_key:
            self._set_status("Введите лицензионный ключ", "error")
            self.key_input.setFocus()
            return

        self._set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self._set_status("Проверка лицензии...", "loading")

        self.validation_worker = LicenseValidationWorker(self.license_manager, license_key, is_activation=True)
        self.validation_worker.validation_complete.connect(self._on_validation_complete)
        self.validation_worker.start()

    def _on_validation_complete(self, success: bool, message: str, error_code: int):
        """Обрабатывает результат валидации."""
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)

        if success:
            self._set_status("Лицензия успешно активирована!", "success")
            QTimer.singleShot(1500, self.accept)  # Закрываем диалог через 1.5 секунды
        else:
            if error_code != 0:
                self._set_status(f"Ошибка {error_code}", "error")
            else:
                self._set_status("Недействительная лицензия", "error")

            self._set_ui_enabled(True)
            self.key_input.setFocus()
            self.key_input.selectAll()

    def _set_ui_enabled(self, enabled: bool):
        """Включает/отключает элементы интерфейса."""
        self.key_input.setEnabled(enabled)
        self.ok_button.setEnabled(enabled)
        self.buy_button.setEnabled(enabled)
        self.copy_button.setEnabled(enabled)

    def closeEvent(self, event):
        """Переопределяем закрытие диалога."""
        event.accept()

    def reject(self):
        """Переопределяем отмену диалога (нажатие Escape)."""
        super().reject()

    def _apply_styles(self):
        """Применяет CSS-стили к диалогу."""
        styles = """
        /*
            --- Цветовая палитра ---
            Фон: #2B2D30
            Вторичный фон: #36393F
            Акцентный цвет: #5865F2 (Discord Blue)
            Акцентный (Hover): #4752C4
            Зеленый (Успех): #2D7D46
            Красный (Ошибка): #ED4245
            Оранжевый (Загрузка): #FEE75C
            Текст основной: #DBDEE1
            Текст вторичный: #B8BCC2
            Границы: #40434B
        */
        QDialog {
            background-color: #2B2D30;
            font-family: "Segoe UI", "Inter", sans-serif;
        }

        /* --- Заголовки --- */
        QLabel#licenseTitle {
            font-size: 24px;
            font-weight: 600;
            color: #FFFFFF;
        }
        QLabel#licenseSubtitle {
            font-size: 14px;
            color: #B8BCC2;
        }

        /* --- Метки полей ввода --- */
        QLabel#licenseIdLabel, QLabel#licenseKeyLabel {
            font-size: 13px;
            font-weight: 500;
            color: #B8BCC2;
            padding-left: 2px;
        }

        /* --- Разделитель --- */
        QFrame#licenseSeparator {
            background-color: #40434B;
            border: none;
            height: 1px;
        }

        /* --- Поля ввода --- */
        QLineEdit {
            background-color: #202225;
            border: 1px solid #40434B;
            border-radius: 5px;
            padding: 12px;
            color: #DBDEE1;
            font-size: 14px;
        }
        QLineEdit:focus {
            border: 1px solid #5865F2;
        }
        QLineEdit#licenseIdField {
            font-family: "Consolas", "Courier New", monospace;
            font-size: 13px;
        }

        /* --- Кнопки --- */
        QPushButton {
            border: none;
            border-radius: 5px;
            padding: 12px 20px;
            font-size: 14px;
            font-weight: 600;
            transition: background-color 0.2s ease-in-out;
        }

        /* Кнопка 'Копировать ID' */
        QPushButton#licenseCopyButton {
            background-color: #40434B;
            color: #FFFFFF;
        }
        QPushButton#licenseCopyButton:hover {
            background-color: #4A4D55;
        }
        QPushButton#licenseCopyButton:disabled {
            background-color: #36393F;
            color: #8A8C90;
        }

        /* Кнопка 'Получить ключ' */
        QPushButton#licenseBuyButton {
            background-color: #36393F;
            color: #FFFFFF;
        }
        QPushButton#licenseBuyButton:hover {
            background-color: #40434B;
        }

        /* Кнопка 'Активировать' (основная) */
        QPushButton#licenseOkButton {
            background-color: #5865F2;
            color: white;
        }
        QPushButton#licenseOkButton:hover {
            background-color: #4752C4;
        }
        QPushButton#licenseOkButton:disabled {
            background-color: #36393F;
            color: #8A8C90;
        }

        /* --- Прогресс-бар --- */
        QProgressBar#licenseProgress {
            background-color: #202225;
            border: 1px solid #40434B;
            border-radius: 5px;
            height: 8px;
            text-align: center;
        }
        QProgressBar#licenseProgress::chunk {
            background-color: #5865F2;
            border-radius: 4px;
        }

        /* --- Статус бар --- */
        QLabel#licenseStatusBar {
            background-color: #36393F;
            border: 1px solid #40434B;
            border-radius: 5px;
            padding: 10px 15px;
            color: #DBDEE1;
            font-size: 13px;
        }

        QLabel#licenseStatusBarError {
            background-color: #3C2B2B;
            border: 1px solid #ED4245;
            border-radius: 5px;
            padding: 10px 15px;
            color: #ED4245;
            font-size: 13px;
            font-weight: 500;
        }

        QLabel#licenseStatusBarSuccess {
            background-color: #2B3C2B;
            border: 1px solid #2D7D46;
            border-radius: 5px;
            padding: 10px 15px;
            color: #57F287;
            font-size: 13px;
            font-weight: 500;
        }

        QLabel#licenseStatusBarLoading {
            background-color: #3C3A2B;
            border: 1px solid #FEE75C;
            border-radius: 5px;
            padding: 10px 15px;
            color: #FEE75C;
            font-size: 13px;
            font-weight: 500;
        }
        """
        self.setStyleSheet(styles)