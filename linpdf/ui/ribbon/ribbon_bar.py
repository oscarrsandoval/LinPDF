from PySide6.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QToolButton, QLabel, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QSize


class RibbonPanel(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(4, 2, 4, 2)

        self._button_layout = QHBoxLayout()
        self._button_layout.setSpacing(1)
        self._button_layout.setAlignment(Qt.AlignCenter)
        layout.addLayout(self._button_layout)

        self._title = QLabel(title)
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet("""
            QLabel {
                font-size: 9px;
                padding-top: 2px;
                border-top: 1px solid palette(mid);
            }
        """)
        self._title.setFixedHeight(18)
        layout.addWidget(self._title)

    def add_button(self, text, icon=None, tooltip="", checkable=False):
        btn = QToolButton()
        btn.setText(text)
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if icon:
            btn.setIcon(icon)
        btn.setToolTip(tooltip)
        btn.setCheckable(checkable)
        btn.setFixedSize(48, 52)
        btn.setIconSize(QSize(24, 24))
        btn.setStyleSheet("""
            QToolButton {
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 2px;
                font-size: 8px;
            }
            QToolButton:hover {
                border-color: palette(highlight);
                background: palette(light);
            }
            QToolButton:pressed, QToolButton:checked {
                border-color: palette(dark);
                background: palette(midlight);
            }
        """)
        self._button_layout.addWidget(btn)
        return btn

    def add_widget(self, widget):
        self._button_layout.addWidget(widget)
        return widget

    def add_separator(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setFixedWidth(2)
        self._button_layout.addWidget(sep)
        return sep


class RibbonTab(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._title = title
        layout = QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setAlignment(Qt.AlignLeft)
        self.setLayout(layout)

    @property
    def title(self):
        return self._title

    def add_panel(self, title):
        panel = RibbonPanel(title)
        self.layout().addWidget(panel)
        return panel

    def add_stretch(self):
        self.layout().addStretch()


class RibbonBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(130)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tab_widget = QTabWidget()
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.tabBar().setExpanding(False)
        self._tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid palette(mid);
                border-top: none;
            }
            QTabBar::tab {
                padding: 6px 14px;
                border: 1px solid palette(mid);
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 10px;
                min-width: 60px;
            }
            QTabBar::tab:selected {
                font-weight: bold;
            }
        """)
        layout.addWidget(self._tab_widget)

        self._tabs = {}

    def add_tab(self, title):
        tab = RibbonTab(title)
        index = self._tab_widget.addTab(tab, title)
        self._tabs[title] = tab
        return tab

    def get_tab(self, title):
        return self._tabs.get(title)

    def set_active_tab(self, title):
        tab = self._tabs.get(title)
        if tab:
            index = self._tab_widget.indexOf(tab)
            self._tab_widget.setCurrentIndex(index)

    def clear_tabs(self):
        self._tab_widget.clear()
        self._tabs.clear()
