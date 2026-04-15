# ui/panels/report_panel.py
# Панель для отображения отчета по цветам и размерам.

from typing import List, Dict, Optional, Tuple

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea
)

from core.models import Project


class ReportItem(QFrame):
    """
    Один элемент (одна строка) в отчете.
    Представляет одну группу "цвет + размер".
    """
    # Сигнал отправляется при клике на элемент
    clicked = pyqtSignal(str, str)  # color_name, size_name

    def __init__(self, color_name: str, size_name: str, color_rgb: tuple, count: int, percentage: float, parent=None):
        super().__init__(parent)
        self.color_name = color_name
        self.size_name = size_name

        self.setObjectName("reportItem")
        self.setFixedHeight(50)
        self.setCursor(Qt.PointingHandCursor)

        # --- Виджеты ---
        self.color_circle = QLabel()
        self.color_circle.setObjectName("reportColorCircle")
        self.color_circle.setFixedSize(22, 22)
        # Устанавливаем цвет круга напрямую, остальное - через QSS
        self.color_circle.setStyleSheet(f"""
            QLabel#reportColorCircle {{
                background-color: rgb({color_rgb[0]}, {color_rgb[1]}, {color_rgb[2]});
                border-radius: 11px;
            }}
        """)

        # Форматируем длинные названия
        display_name = color_name if len(color_name) <= 15 else color_name[:12] + "..."
        self.name_label = QLabel(f"{display_name} ({size_name})")
        self.name_label.setObjectName("reportItemName")

        self.stats_label = QLabel(f"{count} шт. ({percentage:.1f}%)")
        self.stats_label.setObjectName("reportItemStats")

        # --- Компоновка ---
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.stats_label)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(12)
        main_layout.addWidget(self.color_circle)
        main_layout.addLayout(info_layout, 1)

    def mousePressEvent(self, event):
        """Обработка клика для отправки сигнала."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.color_name, self.size_name)
        super().mousePressEvent(event)


class ReportPanel(QWidget):
    """Панель отчета, стилизуется через QSS."""
    colorSelected = pyqtSignal(str, str)  # color_name, size_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("reportPanel")

        self.current_project: Optional[Project] = None
        self.report_items: List[ReportItem] = []

        # Таймер для отложенного обновления, чтобы избежать лишних перерисовок
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._update_report_display)

        self._setup_ui()

    def _setup_ui(self):
        """Собирает интерфейс панели."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0) # Добавлен отступ сверху
        layout.setSpacing(8)

        # --- Заголовок с общей статистикой ---
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0,0,0,0)
        header_layout.setSpacing(2)

        self.total_colors_label = QLabel("Всего цветов: 0")
        self.total_colors_label.setObjectName("reportTotalColors")
        self.total_colors_label.setAlignment(Qt.AlignCenter)

        self.total_rhinestones_label = QLabel("Всего страз: 0")
        self.total_rhinestones_label.setObjectName("reportTotalRhinestones")
        self.total_rhinestones_label.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(self.total_colors_label)
        header_layout.addWidget(self.total_rhinestones_label)
        layout.addWidget(header_widget)

        # --- Разделитель ---
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName("reportSeparator")
        layout.addWidget(separator)

        # --- Скролл-область для списка ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setObjectName("reportScrollArea") # Добавлено имя для стилизации

        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(6, 6, 6, 6)
        self.items_layout.setSpacing(4)
        self.items_layout.setAlignment(Qt.AlignTop) # Гарантирует, что элементы добавляются сверху

        # --- Сообщение, если отчет пуст ---
        self.empty_label = QLabel("Создайте макет для просмотра отчета")
        self.empty_label.setObjectName("reportEmptyLabel")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.items_layout.addWidget(self.empty_label)

        scroll_area.setWidget(self.items_container)
        layout.addWidget(scroll_area, 1)


    def update_report(self, project: Optional[Project]):
        """Запускает отложенное обновление отчета на основе данных проекта."""
        self.current_project = project
        self.update_timer.stop()
        self.update_timer.start(50)

    def _update_report_display(self):
        """(Пере)создает элементы отчета."""
        self._clear_report_items()

        if not self.current_project or not self.current_project.rhinestones:
            self._show_empty_state(True)
            return

        self._show_empty_state(False)

        total_rhinestones = len(self.current_project.rhinestones)
        # Группируем стразы по цвету и размеру
        stats = self._calculate_stats()

        unique_colors = {key[0] for key in stats.keys()}
        self.total_colors_label.setText(f"Всего цветов: {len(unique_colors)}")

        self.total_rhinestones_label.setText(f"Всего страз: {total_rhinestones}")

        # Сортируем группы по количеству страз
        sorted_stats = sorted(stats.items(), key=lambda x: x[1]['count'], reverse=True)

        for (color_name, size_name), data in sorted_stats:
            percentage = (data['count'] / total_rhinestones) * 100
            item = ReportItem(
                color_name, size_name, data['color_rgb'], data['count'], percentage
            )
            item.clicked.connect(self.colorSelected.emit)
            self.items_layout.addWidget(item) # Вставляем в конец
            self.report_items.append(item)

    def _calculate_stats(self) -> Dict[Tuple[str, str], Dict]:
        """Собирает статистику по стразам в проекте."""
        stats = {}
        if not self.current_project:
            return stats

        for r in self.current_project.rhinestones:
            key = (r.color.name, r.size.name)
            if key not in stats:
                stats[key] = {
                    'count': 0,
                    'color_rgb': (r.color.color.r, r.color.color.g, r.color.color.b)
                }
            stats[key]['count'] += 1
        return stats

    def _clear_report_items(self):
        """Удаляет старые виджеты из списка."""
        for item in self.report_items:
            item.deleteLater()
        self.report_items.clear()

    def _show_empty_state(self, is_empty: bool):
        """Показывает или скрывает сообщение о пустом отчете."""
        self.empty_label.setVisible(is_empty)
        if is_empty:
            self.total_colors_label.setText("Всего цветов: 0")
            self.total_rhinestones_label.setText("Всего страз: 0")