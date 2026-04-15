# ui/dialogs/settings_dialog.py
from typing import Optional

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QProgressBar, QDialogButtonBox,
    QTextEdit, QScrollArea, QFrame, QSizePolicy
)
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor
from core.models import AppSettings, UpdateInfoResponse


class SettingsDialog(QDialog):
    """Диалог для проверки и установки обновлений с секцией "Что нового"."""

    check_for_updates_requested = pyqtSignal()
    install_update_requested = pyqtSignal(UpdateInfoResponse)

    def __init__(self, app_settings: AppSettings, parent=None):
        super().__init__(parent)
        self.app_settings = app_settings
        self._update_info: UpdateInfoResponse = None

        self.setWindowTitle("Управление обновлениями")
        self.setObjectName("updateDialog")
        self.setFixedSize(580, 650)
        self.setModal(True)

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)

        # --- Заголовок ---
        self._create_header(main_layout)

        # --- Информация о версии ---
        self._create_version_info(main_layout)

        # --- Секция "Что нового" ---
        self._create_whats_new_section(main_layout)

        # --- Управление обновлениями ---
        self._create_update_controls(main_layout)

        # --- Кнопки ---
        self._create_buttons(main_layout)

        main_layout.setStretch(2, 1)

    def _create_header(self, parent_layout):
        """Создает красивый заголовок диалога."""
        header_frame = QFrame()
        header_frame.setObjectName("updateDialogHeader")
        header_frame.setFixedHeight(80)

        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)

        icon_label = QLabel()
        icon_label.setObjectName("updateDialogIcon")
        icon_label.setFixedSize(50, 50)
        icon_label.setStyleSheet("border: 2px solid #4A90E2; border-radius: 25px;")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setText("L")

        # Текст заголовка
        title_layout = QVBoxLayout()
        title_label = QLabel("Центр обновлений Lumo")
        title_label.setObjectName("updateDialogTitle")

        subtitle_label = QLabel("Проверка и установка новых версий")
        subtitle_label.setObjectName("updateDialogSubtitle")

        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        title_layout.addStretch()

        header_layout.addWidget(icon_label)
        header_layout.addSpacing(15)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        parent_layout.addWidget(header_frame)

    def _create_version_info(self, parent_layout):
        """Создает секцию с информацией о текущей версии."""
        version_group = QGroupBox("Текущая версия")
        version_group.setObjectName("updateDialogVersionGroup")
        version_layout = QVBoxLayout(version_group)

        self.version_label = QLabel(f"Установлена версия: {self.app_settings.current_version}")
        self.version_label.setObjectName("updateDialogVersionLabel")

        self.update_status_label = QLabel("Нажмите 'Проверить обновления' для поиска новых версий")
        self.update_status_label.setObjectName("updateDialogStatusLabel")
        self.update_status_label.setWordWrap(True)

        version_layout.addWidget(self.version_label)
        version_layout.addWidget(self.update_status_label)

        parent_layout.addWidget(version_group)

    def _create_whats_new_section(self, parent_layout):
        """Создает секцию "Что нового"."""
        whats_new_group = QGroupBox("Что нового")
        whats_new_group.setObjectName("updateDialogWhatsNewGroup")

        whats_new_layout = QVBoxLayout(whats_new_group)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("updateDialogScrollArea")
        scroll_area.setWidgetResizable(True)

        self.release_notes = QTextEdit()
        self.release_notes.setObjectName("updateDialogReleaseNotes")
        self.release_notes.setReadOnly(True)
        self.release_notes.setPlainText("Выберите 'Проверить обновления' чтобы увидеть информацию о новых версиях.")

        scroll_area.setWidget(self.release_notes)
        whats_new_layout.addWidget(scroll_area)

        # Дополнительная информация об обновлении
        self.update_details_label = QLabel("")
        self.update_details_label.setObjectName("updateDialogDetailsLabel")
        self.update_details_label.setWordWrap(True)
        whats_new_layout.addWidget(self.update_details_label)

        parent_layout.addWidget(whats_new_group)

    def _create_update_controls(self, parent_layout):
        """Создает элементы управления обновлениями."""
        controls_group = QGroupBox("Управление")
        controls_group.setObjectName("updateDialogControlsGroup")
        controls_layout = QVBoxLayout(controls_group)

        # Прогресс-бар
        self.update_progress = QProgressBar()
        self.update_progress.setObjectName("updateDialogProgressBar")
        self.update_progress.setVisible(False)
        self.update_progress.setTextVisible(True)
        self.update_progress.setFormat("Загрузка: %p%")

        # Кнопки управления в горизонтальном макете
        buttons_layout = QHBoxLayout()

        self.btn_check_updates = QPushButton("🔍 Проверить обновления")
        self.btn_check_updates.setObjectName("updateDialogCheckButton")
        self.btn_check_updates.setMinimumHeight(40)

        self.btn_install_update = QPushButton("⬇️ Скачать и установить")
        self.btn_install_update.setObjectName("updateDialogInstallButton")
        self.btn_install_update.setMinimumHeight(40)
        self.btn_install_update.setVisible(False)

        buttons_layout.addWidget(self.btn_check_updates)
        buttons_layout.addWidget(self.btn_install_update)

        controls_layout.addWidget(self.update_progress)
        controls_layout.addLayout(buttons_layout)

        parent_layout.addWidget(controls_group)

    def _create_buttons(self, parent_layout):
        """Создает кнопки диалога."""
        parent_layout.addStretch()

        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.setObjectName("updateDialogButtonBox")
        self.button_box.button(QDialogButtonBox.Close).setText("Закрыть")
        self.button_box.button(QDialogButtonBox.Close).setObjectName("updateDialogCloseButton")

        parent_layout.addWidget(self.button_box)

    def _connect_signals(self):
        self.button_box.rejected.connect(self.reject)
        self.btn_check_updates.clicked.connect(self.check_for_updates_requested.emit)
        self.btn_install_update.clicked.connect(self._on_install_clicked)

    def _on_install_clicked(self):
        if self._update_info:
            self.install_update_requested.emit(self._update_info)

    def set_checking_for_updates(self, is_checking: bool):
        """Обновляет UI для состояния проверки."""
        self.btn_check_updates.setEnabled(not is_checking)
        if is_checking:
            self.update_status_label.setText("🔄 Проверка наличия обновлений...")
            self.btn_install_update.setVisible(False)
            self.release_notes.setPlainText("Проверка...")

    def on_update_check_finished(self, success: bool, info: Optional[UpdateInfoResponse], message: str):
        """Обновляет UI по результатам проверки."""
        self.set_checking_for_updates(False)
        self.update_status_label.setText(message)

        self._update_info = info
        if success and info and info.update_available:
            self._display_update_info(info)
        else:
            self._display_no_update_info(message)

    def _display_update_info(self, info: UpdateInfoResponse):
        """Отображает информацию о доступном обновлении."""
        # Кнопка установки
        file_size_mb = info.file_size / (1024 ** 2)
        self.btn_install_update.setText(f"⬇️ Скачать v{info.version} ({file_size_mb:.1f} МБ)")
        self.btn_install_update.setVisible(True)

        # Заметки о релизе
        if info.notes:
            self.release_notes.setPlainText(info.notes)
        else:
            self.release_notes.setPlainText(f"Доступна новая версия {info.version}")

        # Дополнительные детали
        details_parts = []
        if info.release_date:
            details_parts.append(f"📅 Дата выпуска: {info.release_date}")
        if info.forced_update:
            details_parts.append("⚠️ Обязательное обновление")

        if details_parts:
            self.update_details_label.setText(" | ".join(details_parts))
        else:
            self.update_details_label.setText("")

    def _display_no_update_info(self, message: str):
        """Отображает информацию когда обновлений нет."""
        self.btn_install_update.setVisible(False)
        self.release_notes.setPlainText("У вас установлена последняя версия. Новых обновлений не обнаружено.")
        self.update_details_label.setText("")

    def set_update_progress(self, progress: int, message: str):
        """Обновляет UI во время загрузки/установки."""
        # 1. Статус-лейбл теперь показывает ТОЛЬКО сообщение, без процентов.
        self.update_status_label.setText(f"Статус: {message}...")

        # 2. Показываем и настраиваем прогресс-бар.
        self.update_progress.setVisible(True)
        self.update_progress.setValue(progress)

        # 3. ИСПРАВЛЕНА ОШИБКА ФОРМАТА:
        self.update_progress.setFormat(f"{message}: %p%")

        # 4. Блокируем кнопки, чтобы пользователь ничего не нажал во время процесса.
        self.btn_install_update.setEnabled(False)
        self.btn_check_updates.setEnabled(False)