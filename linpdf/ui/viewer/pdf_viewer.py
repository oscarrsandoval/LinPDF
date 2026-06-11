from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QFrame, QScrollBar,
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QSizeF
from PySide6.QtGui import (
    QPixmap, QPainter, QPen, QColor, QBrush,
    QWheelEvent, QMouseEvent, QTransform,
)

from linpdf.constants import ViewMode, DEFAULT_ZOOM, MIN_ZOOM, MAX_ZOOM


class PageGraphicsItem(QGraphicsPixmapItem):
    def __init__(self, page_index, pixmap, page_size, parent=None):
        super().__init__(pixmap, parent)
        self.page_index = page_index
        self.page_size = page_size
        self.setFlag(QGraphicsPixmapItem.ItemIsSelectable, True)
        self.setCacheMode(QGraphicsPixmapItem.DeviceCoordinateCache)

    def boundingRect(self):
        return QRectF(self.offset(), self.pixmap().size())


class PDFViewer(QGraphicsView):
    page_changed = Signal(int)
    zoom_changed = Signal(float)
    mode_changed = Signal(object)
    document_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._document = None
        self._renderer = None
        self._zoom = DEFAULT_ZOOM
        self._view_mode = ViewMode.CONTINUOUS
        self._page_items = []
        self._page_spacing = 10
        self._rendering = False

        self.setRenderHints(
            QPainter.Antialiasing | QPainter.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setFrameShape(QFrame.NoFrame)
        self.setAcceptDrops(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setBackgroundBrush(QColor(180, 180, 180))

    def set_document(self, document, renderer):
        self._document = document
        self._renderer = renderer
        self._rebuild_pages()

    def _rebuild_pages(self):
        self._scene.clear()
        self._page_items = []

        if not self._document or not self._document.is_loaded:
            return

        y_offset = 10
        for i in range(self._document.page_count):
            page = self._document.get_page(i)
            if not page:
                continue

            pixmap = self._renderer.render_page(page, self._zoom)
            item = PageGraphicsItem(i, pixmap, page.size)
            item.setPos(0, y_offset)
            self._scene.addItem(item)
            self._page_items.append(item)

            w = pixmap.width()
            y_offset += pixmap.height() + self._page_spacing

        self._scene.setSceneRect(
            QRectF(0, 0, self._scene.width(), y_offset)
        )
        self._center_first_page()

    def _center_first_page(self):
        if self._page_items:
            self.centerOn(self._page_items[0])

    def set_zoom(self, zoom):
        zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        if abs(zoom - self._zoom) < 0.01:
            return
        self._zoom = zoom
        self._rebuild_pages()
        self.zoom_changed.emit(zoom)

    def zoom_in(self):
        self.set_zoom(self._zoom * 1.2)

    def zoom_out(self):
        self.set_zoom(self._zoom / 1.2)

    def fit_width(self):
        if not self._page_items:
            return
        viewport_w = self.viewport().width()
        if self._page_items[0].pixmap().width() > 0:
            zoom = viewport_w / self._page_items[0].pixmap().width()
            self.set_zoom(zoom * self._zoom)

    def fit_page(self):
        if not self._page_items:
            return
        viewport_w = self.viewport().width()
        viewport_h = self.viewport().height()
        pixmap = self._page_items[0].pixmap()
        if pixmap.width() > 0 and pixmap.height() > 0:
            zoom_x = viewport_w / pixmap.width()
            zoom_y = viewport_h / pixmap.height()
            self.set_zoom(min(zoom_x, zoom_y) * self._zoom)

    def set_view_mode(self, mode):
        self._view_mode = mode
        self._rebuild_pages()
        self.mode_changed.emit(mode)

    def go_to_page(self, index):
        if 0 <= index < len(self._page_items):
            self.centerOn(self._page_items[index])
            self.page_changed.emit(index)

    def get_current_page(self):
        if not self._page_items:
            return 0
        center = self.mapToScene(self.viewport().rect().center())
        closest = 0
        min_dist = float("inf")
        for i, item in enumerate(self._page_items):
            dist = abs(item.pos().y() + item.boundingRect().height() / 2 - center.y())
            if dist < min_dist:
                min_dist = dist
                closest = i
        return closest

    def clear(self):
        self._scene.clear()
        self._page_items = []
        self._document = None
        self._renderer = None

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.fit_width()
        super().mouseDoubleClickEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                self.document_dropped.emit(path)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    @property
    def zoom(self):
        return self._zoom
