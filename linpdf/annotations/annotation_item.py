import math

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF, QLineF
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QPolygonF,
)

from linpdf.constants import AnnotationType


HANDLE_SIZE = 8.0


class AnnotationItem(QGraphicsItem):
    _text_markup_types = {
        AnnotationType.HIGHLIGHT,
        AnnotationType.UNDERLINE,
        AnnotationType.STRIKEOUT,
        AnnotationType.SQUIGGLY,
    }

    def __init__(self, annot_type, rect, properties=None, zoom=1.0, parent=None):
        super().__init__(parent)
        self._annot_type = annot_type
        self._rect = QRectF(rect)
        self._properties = properties or {}
        self._zoom = zoom
        self._resize_handle = None
        self._drag_start = None
        self._drag_rect = None
        self._is_hovering = False

        self.setFlags(
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.ArrowCursor)

    @property
    def annot_type(self):
        return self._annot_type

    @property
    def properties(self):
        return self._properties

    @properties.setter
    def properties(self, props):
        self._properties = props
        self.update()

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, z):
        self._zoom = z
        self.update()

    def set_rect(self, rect):
        self.prepareGeometryChange()
        self._rect = QRectF(rect)
        self.update()

    def rect_pdf(self):
        return self._rect

    def boundingRect(self):
        margin = HANDLE_SIZE + 4 if self.isSelected() else 4
        return self._rect.adjusted(-margin, -margin, margin, margin)

    def shape(self):
        path = QPainterPath()
        path.addRect(self._rect)
        return path

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)

        painter.save()
        if self._annot_type in self._text_markup_types:
            self._paint_text_markup(painter)
        elif self._annot_type == AnnotationType.TEXT:
            self._paint_text_note(painter)
        elif self._annot_type == AnnotationType.FREETEXT:
            self._paint_freetext(painter)
        elif self._annot_type == AnnotationType.STAMP:
            self._paint_stamp(painter)
        elif self._annot_type in (AnnotationType.LINE, AnnotationType.ARROW):
            self._paint_line(painter)
        elif self._annot_type == AnnotationType.RECTANGLE:
            self._paint_rectangle(painter)
        elif self._annot_type == AnnotationType.ELLIPSE:
            self._paint_ellipse(painter)
        elif self._annot_type in (AnnotationType.POLYGON, AnnotationType.POLYLINE):
            self._paint_polygon(painter)
        elif self._annot_type == AnnotationType.INK:
            self._paint_ink(painter)
        elif self._annot_type == AnnotationType.FILE_ATTACHMENT:
            self._paint_file_attachment(painter)
        elif self._annot_type == AnnotationType.CARET:
            self._paint_caret(painter)
        elif self._annot_type == AnnotationType.REDACTION:
            self._paint_redaction(painter)
        painter.restore()

        if self.isSelected():
            self._paint_handles(painter)

    def _stroke_pen(self):
        c = self._properties.get('stroke_color')
        color = QColor(*c) if c and len(c) == 3 else QColor(self.palette().windowText().color())
        pen = QPen(color, self._properties.get('line_width', 1.0))
        pen.setCosmetic(True)
        return pen

    def _fill_brush(self):
        c = self._properties.get('fill_color')
        if c and len(c) == 3:
            fill = QColor(*c)
            fill.setAlphaF(self._properties.get('opacity', 1.0))
            return QBrush(fill)
        return QBrush(Qt.NoBrush)

    # ---- Type-specific painters ----

    def _paint_text_markup(self, painter):
        fill = QColor(255, 255, 0)
        c = self._properties.get('fill_color')
        if c and len(c) == 3:
            fill = QColor(*c)
        fill.setAlphaF(self._properties.get('opacity', 0.3))
        painter.fillRect(self._rect, fill)

        if self._annot_type == AnnotationType.UNDERLINE:
            pen = QPen(fill.darker(120), 2)
            pen.setCosmetic(True)
            painter.setPen(pen)
            y = self._rect.bottom() - 1
            painter.drawLine(QPointF(self._rect.left(), y), QPointF(self._rect.right(), y))
        elif self._annot_type == AnnotationType.STRIKEOUT:
            pen = QPen(fill.darker(120), 2)
            pen.setCosmetic(True)
            painter.setPen(pen)
            y = (self._rect.top() + self._rect.bottom()) / 2
            painter.drawLine(QPointF(self._rect.left(), y), QPointF(self._rect.right(), y))
        elif self._annot_type == AnnotationType.SQUIGGLY:
            pen = QPen(fill.darker(120), 1.5)
            pen.setCosmetic(True)
            painter.setPen(pen)
            y = self._rect.bottom() - 1
            x = self._rect.left()
            path = QPainterPath()
            path.moveTo(x, y)
            w = self._rect.width()
            steps = max(int(w / 6), 2)
            for i in range(1, steps + 1):
                nx = x + w * i / steps
                ny = y - (3 if i % 2 == 0 else -3)
                path.lineTo(nx, ny)
            painter.drawPath(path)

    def _paint_text_note(self, painter):
        r = self._rect
        icon_size = min(r.width(), r.height())
        top_left = r.center() - QPointF(icon_size / 2, icon_size / 2)
        icon_rect = QRectF(top_left.x(), top_left.y(), icon_size, icon_size)

        painter.setPen(QPen(QColor(self.palette().windowText().color()), 1.5))
        painter.setBrush(QBrush(QColor(255, 255, 200)))
        painter.drawRect(icon_rect)

        fold = QPointF(icon_rect.right(), icon_rect.top() + icon_size * 0.3)
        painter.drawLine(fold, QPointF(icon_rect.right() - icon_size * 0.25, icon_rect.top()))
        painter.drawLine(QPointF(icon_rect.right() - icon_size * 0.25, icon_rect.top()), fold)

        note_size = icon_size * 0.12
        for i in range(3):
            y = icon_rect.top() + icon_size * 0.5 + i * note_size * 2.5
            painter.drawLine(
                QPointF(icon_rect.left() + note_size * 2, y),
                QPointF(icon_rect.right() - note_size * 1.5, y),
            )

    def _paint_freetext(self, painter):
        r = self._rect
        painter.setPen(self._stroke_pen())
        painter.setBrush(self._fill_brush())
        painter.drawRect(r)

        text = self._properties.get('text', '')
        if text:
            font_size = self._properties.get('font_size', 12) * self._zoom
            font_name = self._properties.get('font_name', 'sans-serif')
            font = QFont(font_name, max(1, int(font_size)))
            painter.setFont(font)
            painter.setPen(QPen(self._stroke_pen().color()))
            text_rect = r.adjusted(4, 4, -4, -4)
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, text)

    def _paint_stamp(self, painter):
        r = self._rect
        pen = QPen(QColor(self.palette().windowText().color()), 1.5)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 255, 220)))
        painter.drawRoundedRect(r, 6, 6)

        text = self._properties.get('text', 'Stamp')
        font_size = max(8, min(r.width(), r.height()) * 0.18) * self._zoom
        font = QFont('sans-serif', max(1, int(font_size)))
        painter.setFont(font)
        painter.setPen(QPen(QColor(180, 40, 40)))
        painter.drawText(r, Qt.AlignCenter, text)

    def _paint_line(self, painter):
        pen = self._stroke_pen()
        painter.setPen(pen)
        r = self._rect
        p1 = r.topLeft()
        p2 = r.bottomRight()

        if self._annot_type == AnnotationType.ARROW:
            self._draw_arrow(painter, p1, p2)
        else:
            painter.drawLine(QLineF(p1, p2))

    def _draw_arrow(self, painter, p1, p2):
        painter.drawLine(QLineF(p1, p2))
        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        arrow_size = 10 * self._zoom
        ax = math.cos(angle) * arrow_size
        ay = math.sin(angle) * arrow_size

        head_angle = math.radians(25)
        left_angle = angle + math.pi - head_angle
        right_angle = angle + math.pi + head_angle

        left = QPointF(p2.x() + math.cos(left_angle) * arrow_size,
                       p2.y() + math.sin(left_angle) * arrow_size)
        right = QPointF(p2.x() + math.cos(right_angle) * arrow_size,
                        p2.y() + math.sin(right_angle) * arrow_size)

        arrow_path = QPainterPath()
        arrow_path.moveTo(p2)
        arrow_path.lineTo(left)
        arrow_path.lineTo(right)
        arrow_path.closeSubpath()

        brush = QBrush(painter.pen().color())
        painter.setBrush(brush)
        painter.drawPath(arrow_path)

    def _paint_rectangle(self, painter):
        painter.setPen(self._stroke_pen())
        painter.setBrush(self._fill_brush())
        painter.drawRect(self._rect)

    def _paint_ellipse(self, painter):
        painter.setPen(self._stroke_pen())
        painter.setBrush(self._fill_brush())
        painter.drawEllipse(self._rect)

    def _paint_polygon(self, painter):
        points = self._properties.get('points')
        if not points:
            return
        poly = QPolygonF([QPointF(x * self._zoom, y * self._zoom) for (x, y) in points])
        painter.setPen(self._stroke_pen())
        if self._annot_type == AnnotationType.POLYGON:
            painter.setBrush(self._fill_brush())
            painter.drawPolygon(poly)
        else:
            painter.setBrush(Qt.NoBrush)
            painter.drawPolyline(poly)

    def _paint_ink(self, painter):
        strokes = self._properties.get('points', [])
        if not strokes:
            return
        painter.setPen(self._stroke_pen())
        painter.setBrush(Qt.NoBrush)
        for stroke in strokes:
            if len(stroke) < 2:
                continue
            path = QPainterPath()
            first = True
            for (x, y) in stroke:
                pt = QPointF(x * self._zoom, y * self._zoom)
                if first:
                    path.moveTo(pt)
                    first = False
                else:
                    path.lineTo(pt)
            painter.drawPath(path)

    def _paint_file_attachment(self, painter):
        r = self._rect
        c = r.center()
        size = min(r.width(), r.height()) * 0.6
        rect = QRectF(c.x() - size / 2, c.y() - size / 2, size, size)

        pen = QPen(QColor(self.palette().windowText().color()), 1.5)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(240, 240, 255)))
        painter.drawRect(rect)

        pin = QPainterPath()
        pin.moveTo(rect.center())
        pin.lineTo(rect.center() + QPointF(0, rect.height() * 0.3))
        painter.drawPath(pin)

        painter.drawEllipse(rect.center(), 3, 3)

    def _paint_caret(self, painter):
        r = self._rect
        pen = QPen(QColor(self.palette().windowText().color()), 1.5)
        painter.setPen(pen)
        center_x = (r.left() + r.right()) / 2
        painter.drawLine(QPointF(center_x, r.top()), QPointF(center_x, r.bottom()))
        caret_w = min(r.width(), 6)
        painter.drawLine(QPointF(center_x - caret_w, r.top()), QPointF(center_x + caret_w, r.top()))
        painter.drawLine(QPointF(center_x - caret_w, r.bottom()), QPointF(center_x + caret_w, r.bottom()))

    def _paint_redaction(self, painter):
        r = self._rect
        painter.fillRect(r, QColor(0, 0, 0))
        overlay = self._properties.get('text', '')
        if overlay:
            font = QFont('sans-serif', max(6, int(8 * self._zoom)))
            painter.setFont(font)
            painter.setPen(QPen(Qt.white))
            painter.drawText(r, Qt.AlignCenter, overlay)
        else:
            pen = QPen(QColor(80, 80, 80), 1)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawLine(r.topLeft(), r.bottomRight())
            painter.drawLine(r.topRight(), r.bottomLeft())

    # ---- Selection handles ----

    def _paint_handles(self, painter):
        pen = QPen(QColor(self.palette().highlight().color()), 2)
        pen.setCosmetic(True)
        brush = QBrush(Qt.white)
        handles = self._handle_rects()
        for h in handles:
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawRect(h)

    def _handle_rects(self):
        r = self._rect
        hs = HANDLE_SIZE
        return [
            QRectF(r.left() - hs / 2, r.top() - hs / 2, hs, hs),
            QRectF(r.right() - hs / 2, r.top() - hs / 2, hs, hs),
            QRectF(r.left() - hs / 2, r.bottom() - hs / 2, hs, hs),
            QRectF(r.right() - hs / 2, r.bottom() - hs / 2, hs, hs),
            QRectF((r.left() + r.right()) / 2 - hs / 2, r.top() - hs / 2, hs, hs),
            QRectF((r.left() + r.right()) / 2 - hs / 2, r.bottom() - hs / 2, hs, hs),
            QRectF(r.left() - hs / 2, (r.top() + r.bottom()) / 2 - hs / 2, hs, hs),
            QRectF(r.right() - hs / 2, (r.top() + r.bottom()) / 2 - hs / 2, hs, hs),
        ]

    def _handle_at(self, pos):
        if not self.isSelected():
            return None
        for i, h in enumerate(self._handle_rects()):
            if h.contains(pos):
                return i
        return None

    def _cursor_for_handle(self, handle):
        cursors = [
            Qt.SizeFDiagCursor, Qt.SizeBDiagCursor,
            Qt.SizeBDiagCursor, Qt.SizeFDiagCursor,
            Qt.SizeVerCursor, Qt.SizeVerCursor,
            Qt.SizeHorCursor, Qt.SizeHorCursor,
        ]
        return cursors[handle] if 0 <= handle < len(cursors) else Qt.ArrowCursor

    def _resize_from_handle(self, handle, delta):
        r = QRectF(self._rect)
        if handle == 0:
            r.setTopLeft(r.topLeft() + delta)
        elif handle == 1:
            r.setTopRight(r.topRight() + delta)
        elif handle == 2:
            r.setBottomLeft(r.bottomLeft() + delta)
        elif handle == 3:
            r.setBottomRight(r.bottomRight() + delta)
        elif handle == 4:
            r.setTop(r.top() + delta.y())
        elif handle == 5:
            r.setBottom(r.bottom() + delta.y())
        elif handle == 6:
            r.setLeft(r.left() + delta.x())
        elif handle == 7:
            r.setRight(r.right() + delta.x())
        if r.width() > 5 and r.height() > 5:
            self._rect = r.normalized()

    # ---- Mouse events ----

    def hoverMoveEvent(self, event):
        handle = self._handle_at(event.pos())
        if handle is not None:
            self.setCursor(self._cursor_for_handle(handle))
        else:
            self.setCursor(Qt.SizeAllCursor if self.isSelected() else Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return
        handle = self._handle_at(event.pos())
        if handle is not None:
            self._resize_handle = handle
            self._drag_start = event.scenePos()
            self._drag_rect = QRectF(self._rect)
        else:
            self._resize_handle = None
            self._drag_start = event.scenePos()
            self._drag_rect = QRectF(self._rect)
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self._drag_start is None:
            super().mouseMoveEvent(event)
            return
        delta = event.scenePos() - self._drag_start
        if self._resize_handle is not None:
            self._resize_from_handle(self._resize_handle, delta)
        else:
            self.prepareGeometryChange()
            self._rect = QRectF(self._drag_rect).translated(delta)
        self.update()

    def mouseReleaseEvent(self, event):
        self._resize_handle = None
        self._drag_start = None
        self._drag_rect = None
        super().mouseReleaseEvent(event)
