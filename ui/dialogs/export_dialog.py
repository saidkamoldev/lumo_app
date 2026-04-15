# ui/dialogs/export_dialog.py
# Диалог для настройки параметров экспорта.

import os
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QRadioButton, QDialogButtonBox,
    QFileDialog, QCheckBox, QMessageBox
)

from core.models import ExportSettings, ExportFormat, ExportVariant
from core.services.export_service import ExportService


class ExportDialog(QDialog):
    """
    Диалог для настройки параметров экспорта, таких как формат, режим,
    имя файла и дополнительные опции.
    """

    def __init__(self, export_service: ExportService, parent=None):
        super().__init__(parent)
        self.export_service = export_service
        self.settings = ExportSettings()

        self.setWindowTitle("Настройки экспорта")
        self.setFixedWidth(580)
        self.setObjectName("exportDialog")

        self._init_ui()
        self._connect_signals()
        self._update_ui_from_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # --- Формат файла ---
        format_group = QGroupBox("Выберите формат файла:")
        format_group.setObjectName("exportGroup")
        format_layout = QHBoxLayout(format_group)
        self.rb_png = QRadioButton("PNG")
        self.rb_svg = QRadioButton("SVG")
        self.rb_jpg = QRadioButton("JPG")
        self.rb_png.setChecked(True)
        format_layout.addWidget(self.rb_png)
        format_layout.addWidget(self.rb_svg)
        format_layout.addWidget(self.rb_jpg)
        format_layout.addStretch()

        # --- Режим экспорта ---
        variant_group = QGroupBox("Режим экспорта:")
        variant_group.setObjectName("exportGroup")
        variant_layout = QVBoxLayout(variant_group)
        self.rb_clean = QRadioButton("Только стразы")
        self.rb_numbered = QRadioButton("Пронумерованные стразы")
        self.rb_numbered.setChecked(True)
        variant_layout.addWidget(self.rb_clean)
        variant_layout.addWidget(self.rb_numbered)

        # --- Дополнительные опции ---
        options_group = QGroupBox("Дополнительные параметры:")
        options_group.setObjectName("exportGroup")
        options_layout = QVBoxLayout(options_group)
        self.check_separate_table = QCheckBox("Сохранить таблицу отчета в отдельный файл")
        self.check_separate_table.setChecked(True)
        self.check_separate_table.setToolTip(
            "Создает PNG-файл с таблицей, содержащей информацию о количестве\n"
            "стразов каждого цвета и размера."
        )
        self.check_stroke = QCheckBox("Добавить тонкую черную обводку")
        self.check_stroke.setToolTip("Добавляет тонкую черную линию вокруг каждого страза.")
        options_layout.addWidget(self.check_separate_table)
        options_layout.addWidget(self.check_stroke)

        # --- Путь сохранения ---
        path_group = QGroupBox("Сохранение")
        path_group.setObjectName("exportGroup")
        path_layout = QGridLayout(path_group)
        self.le_filename = QLineEdit()
        self.le_filepath = QLineEdit()
        self.le_filepath.setPlaceholderText("Выберите папку...")
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        self.le_filepath.setText(desktop_path)
        self.btn_browse = QPushButton("Обзор...")
        self.lbl_file_info = QLabel("")
        self.lbl_file_info.setStyleSheet("color: #666; font-style: italic; font-size: 22px;")
        path_layout.addWidget(QLabel("Имя файла:"), 0, 0)
        path_layout.addWidget(self.le_filename, 0, 1)
        path_layout.addWidget(QLabel("Папка:"), 1, 0)
        path_layout.addWidget(self.le_filepath, 1, 1)
        path_layout.addWidget(self.btn_browse, 1, 2)
        path_layout.addWidget(self.lbl_file_info, 2, 0, 1, 3)

        # --- Кнопки ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Save).setText("Сохранить")
        self.button_box.button(QDialogButtonBox.Cancel).setText("Отмена")

        main_layout.addWidget(format_group)
        main_layout.addWidget(variant_group)
        main_layout.addWidget(options_group)
        main_layout.addWidget(path_group)
        main_layout.addStretch()
        main_layout.addWidget(self.button_box)

    def _connect_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.btn_browse.clicked.connect(self._select_output_path)

        # При любом изменении настроек обновляем состояние
        self.rb_png.toggled.connect(self._on_settings_changed)
        self.rb_svg.toggled.connect(self._on_settings_changed)
        self.rb_jpg.toggled.connect(self._on_settings_changed)
        self.rb_clean.toggled.connect(self._on_settings_changed)
        self.rb_numbered.toggled.connect(self._on_settings_changed)
        self.check_separate_table.toggled.connect(self._on_settings_changed)
        self.check_stroke.toggled.connect(self._on_settings_changed)
        self.le_filename.textChanged.connect(self._on_settings_changed)

    def _on_settings_changed(self):
        """Обновляет объект настроек `self.settings` при изменении любого параметра в UI."""
        # Сохраняем текущее имя файла без расширения
        current_filename = self.le_filename.text()
        name_without_ext = os.path.splitext(current_filename)[0] if current_filename else ""

        # Определяем новый формат
        if self.rb_png.isChecked():
            self.settings.format = ExportFormat.PNG
            new_ext = "png"
        elif self.rb_svg.isChecked():
            self.settings.format = ExportFormat.SVG
            new_ext = "svg"
        else:
            self.settings.format = ExportFormat.JPG
            new_ext = "jpg"

        # ИСПРАВЛЕНИЕ: Автоматически обновляем расширение файла
        if name_without_ext:
            new_filename = f"{name_without_ext}.{new_ext}"
            # Блокируем сигналы, чтобы избежать рекурсии
            self.le_filename.blockSignals(True)
            self.le_filename.setText(new_filename)
            self.le_filename.blockSignals(False)
        elif not current_filename:
            # Если имя файла пустое, генерируем новое с правильным расширением
            default_filename = self.export_service.generate_default_filename(new_ext)
            self.le_filename.blockSignals(True)
            self.le_filename.setText(default_filename)
            self.le_filename.blockSignals(False)

        if self.rb_clean.isChecked():
            self.settings.variant = ExportVariant.CLEAN
        else:
            self.settings.variant = ExportVariant.NUMBERED

        self.settings.add_stroke = self.check_stroke.isChecked()
        self.settings.save_table_separately = self.check_separate_table.isChecked()

        self._update_file_info()

    def _update_ui_from_settings(self):
        """Обновляет UI в соответствии с текущими настройками (имя файла, инфо-метка)."""
        if not self.le_filename.text():
            ext = self.settings.format.name.lower()
            base_filename = self.export_service.generate_default_filename(ext)
            self.le_filename.setText(base_filename)
        self._update_file_info()

    def _update_file_info(self):
        """Обновляет информационную метку, показывающую, какие файлы будут созданы."""
        info_lines = []
        filename = self.le_filename.text()
        if filename:
            info_lines.append(f"📄 Основной файл: {filename}")

        if self.check_separate_table.isChecked():
            if filename:
                name_without_ext = os.path.splitext(filename)[0]
                table_filename = f"{name_without_ext}_table.png"
                info_lines.append(f"📊 Таблица отчета: {table_filename}")
            else:
                info_lines.append("📊 Таблица отчета: [имя]_table.png")

        if self.rb_clean.isChecked():
            info_lines.append("📋 Режим: чистые стразы")
        else:
            info_lines.append("📋 Режим: пронумерованные стразы")

        if self.check_stroke.isChecked():
            info_lines.append("🖤 С черной обводкой")

        self.lbl_file_info.setText("\n".join(info_lines))

    def _select_output_path(self):
        """Открывает диалог выбора папки для сохранения."""
        current_path = self.le_filepath.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения", current_path)
        if folder:
            self.le_filepath.setText(folder)
            self._update_file_info()

    def get_settings(self) -> ExportSettings:
        """Возвращает итоговый объект с настройками экспорта."""
        self.settings.filename = self.le_filename.text()
        self.settings.output_path = self.le_filepath.text()
        return self.settings

    def accept(self):
        """Проверяет корректность данных перед закрытием диалога."""
        if not self.le_filename.text().strip():
            QMessageBox.warning(self, "Внимание", "Укажите имя файла для сохранения.")
            self.le_filename.setFocus()
            return

        if not self.le_filepath.text().strip() or not os.path.isdir(self.le_filepath.text()):
            QMessageBox.warning(self, "Внимание", "Выберите существующую папку для сохранения.")
            return

        super().accept()