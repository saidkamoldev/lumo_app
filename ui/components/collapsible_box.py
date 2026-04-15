# ui/components/collapsible_box.py

from typing import Optional
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QToolButton, QFrame, QVBoxLayout, QSizePolicy

class CollapsibleBox(QWidget):
    """
    Виджет-контейнер, который можно сворачивать и разворачивать.
    """
    def __init__(self, title: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.toggle_button = QToolButton(self)
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        self.toggle_button.setObjectName("collapsibleHeader") # Для QSS
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.DownArrow)
        self.toggle_button.clicked.connect(self.toggle)

        self.content_area = QFrame(self)
        self.content_area.setObjectName("collapsibleContent") # Для QSS
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.content_area.setVisible(True)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)

    def toggle(self, checked: bool):
        self.toggle_button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.content_area.setVisible(checked)

    def setContent(self, content_widget: QWidget):
        if self.content_area.layout() is None:
            self.content_area.setLayout(QVBoxLayout())
            self.content_area.layout().setContentsMargins(0, 0, 0, 0)
        self.content_area.layout().addWidget(content_widget)