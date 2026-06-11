from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QFrame,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont


class ThumbnailWidget(QWidget):
    page_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Pages")
        header.setAlignment(Qt.AlignCenter)
        header.setFixedHeight(32)
        header.setStyleSheet("""
            QLabel {
                background: #f0f0f0;
                border-bottom: 1px solid #d0d0d0;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setIconSize(QSize(160, 200))
        self._list.setSpacing(2)
        self._list.setFlow(QListWidget.TopToBottom)
        self._list.setViewMode(QListWidget.ListMode)
        self._list.setMovement(QListWidget.Static)
        self._list.setResizeMode(QListWidget.Adjust)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.setStyleSheet("""
            QListWidget {
                background: #fafafa;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 4px;
                border: 2px solid transparent;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                border: 2px solid #4a90d9;
                background: #e8f0fe;
            }
            QListWidget::item:hover {
                background: #f0f0f0;
            }
        """)
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list)

        self._document = None
        self._renderer = None

    def set_document(self, document, renderer):
        self._document = document
        self._renderer = renderer
        self._rebuild_thumbnails()

    def _rebuild_thumbnails(self):
        self._list.clear()
        if not self._document or not self._document.is_loaded:
            return

        for i in range(self._document.page_count):
            page = self._document.get_page(i)
            if not page:
                continue

            pixmap = self._renderer.render_thumbnail(page, 160)
            item = QListWidgetItem()
            label = f"Page {i + 1}"
            item.setText(label)

            final_pixmap = QPixmap(pixmap.size())
            final_pixmap.fill(Qt.white)
            painter = QPainter(final_pixmap)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

            item.setIcon(QIcon(final_pixmap))
            item.setData(Qt.UserRole, i)
            item.setSizeHint(QSize(180, max(pixmap.height() + 30, 60)))
            self._list.addItem(item)

    def select_page(self, index):
        if 0 <= index < self._list.count():
            self._list.blockSignals(True)
            self._list.setCurrentRow(index)
            self._list.blockSignals(False)

    def _on_row_changed(self, row):
        if row >= 0:
            self.page_selected.emit(row)

    def clear(self):
        self._list.clear()
        self._document = None
        self._renderer = None

    def refresh(self):
        self._rebuild_thumbnails()
