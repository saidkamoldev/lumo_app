# main.py
# Главный Entry Point

import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog

from core.licensing.license_manager import LicenseManager
from ui.dialogs.license_dialog import LicenseDialog

from app.canvas_manager import CanvasManager
from app.main_presenter import MainPresenter
from app.update_manager import UpdateManager
from core.models import RhinestoneSize, AppSettings
from core.services.export_service import ExportService
from core.services.image_processor_service import ImageProcessorService
from core.services.palette_service import PaletteService
from core.services.text_service import TextImageService
from core.services.trace_processor import TraceProcessor
from core.services.update_service import UpdateService
from ui.main_window import MainWindow
from ui.theme.theme_manager import ThemeManager
from ui.theme.theme_manager import resource_path

def check_license() -> bool:
    """
    Проверяет лицензию и показывает диалог активации при необходимости.
    Возвращает True, если лицензия действительна, иначе False.
    """
    license_manager = LicenseManager()

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setApplicationName("Lumo")

    if license_manager.is_licensed():
        return True

    license_dialog = LicenseDialog(license_manager)
    result = license_dialog.exec_()

    if result == QDialog.Accepted and license_manager.is_licensed():
        return True

    return False


def main():
    """Главная функция сборки и запуска приложения."""
    if not check_license():
        QMessageBox.critical(
            None,
            "Ошибка лицензирования",
            "Приложение не может быть запущено без действующей лицензии."
        )
        sys.exit(1)

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setWindowIcon(QIcon(resource_path("resources/icons/app_icon.ico")))

    try:
        # --- 1. Инициализация Настроек и Сервисов ---
        app_settings = AppSettings()

        palette_service = PaletteService(colors_filepath="resources/colors.json")
        text_service = TextImageService()
        export_service = ExportService()
        trace_processor = TraceProcessor()
        update_service = UpdateService(app_settings)

        available_sizes = [
            RhinestoneSize(f"SS{s}", d) for s, d in
            {"3": 1.5, "4": 1.7, "5": 1.9, "6": 2.1, "8": 2.5, "10": 2.9, "12": 3.2, "16": 4.0, "20": 4.8}.items()
        ]

        image_processor_service = ImageProcessorService(
            palette_service=palette_service,
            available_sizes=available_sizes
        )

        # --- 2. Инициализация Менеджеров и UI ---
        main_window = MainWindow()
        theme_manager = ThemeManager(app)
        theme_manager.apply_theme('dark')

        canvas_manager = CanvasManager(theme_manager=theme_manager)
        canvas_manager.register_canvas(main_window.photo_viewer)
        canvas_manager.register_canvas(main_window.editable_canvas)

        update_manager = UpdateManager(update_service)

        # --- 3. Инициализация Презентера ---
        presenter = MainPresenter(
            view=main_window,
            app_settings=app_settings,
            processor_service=image_processor_service,
            palette_service=palette_service,
            trace_processor=trace_processor,
            text_service=text_service,
            export_service=export_service,
            update_manager=update_manager,
            theme_manager=theme_manager,
            available_sizes=available_sizes
        )

        # --- 4. Связывание Сигналов и Слотов ---
        toolbar = main_window.left_toolbar
        settings_panel = main_window.settings_panel

        toolbar.loadImageClicked.connect(presenter.load_image)
        toolbar.editModeClicked.connect(presenter.toggle_edit_mode)
        toolbar.paletteClicked.connect(presenter.open_palette_dialog)
        toolbar.sizesClicked.connect(presenter.open_sizes_dialog)
        toolbar.exportClicked.connect(presenter.export_project)
        toolbar.traceClicked.connect(presenter.open_trace_dialog)
        toolbar.settingsClicked.connect(presenter.open_settings_dialog)
        toolbar.addTextClicked.connect(presenter.create_text_layout)
        toolbar.toggleThemeClicked.connect(presenter.theme_manager.toggle_theme)
        toolbar.canvasBackgroundClicked.connect(presenter._on_change_canvas_background)

        settings_panel.processClicked.connect(presenter.process_image)
        settings_panel.mirrorClicked.connect(presenter.mirror_image)

        # --- 5. Запуск приложения ---
        main_window.show()
        sys.exit(app.exec_())

    except Exception as e:
        QMessageBox.critical(
            None,
            "Критическая ошибка",
            f"Произошла критическая ошибка при запуске приложения:\n{str(e)}"
        )
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()