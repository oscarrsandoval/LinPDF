import fitz
from PySide6.QtCore import QSizeF
from PySide6.QtGui import QPixmap, QImage


class Page:
    def __init__(self, fitz_page):
        self._page = fitz_page

    @property
    def index(self):
        return self._page.number

    @property
    def size(self):
        rect = self._page.rect
        return QSizeF(rect.width, rect.height)

    @property
    def width(self):
        return self._page.rect.width

    @property
    def height(self):
        return self._page.rect.height

    def render(self, zoom=1.0, clip_rect=None):
        matrix = fitz.Matrix(zoom, zoom)
        if clip_rect:
            clip = fitz.Rect(
                clip_rect.x(), clip_rect.y(),
                clip_rect.x() + clip_rect.width(),
                clip_rect.y() + clip_rect.height(),
            )
            pixmap = self._page.get_pixmap(matrix=matrix, clip=clip)
        else:
            pixmap = self._page.get_pixmap(matrix=matrix)

        img = QImage(
            pixmap.samples,
            pixmap.width,
            pixmap.height,
            pixmap.stride,
            QImage.Format_RGB888,
        )
        return QPixmap.fromImage(img)

    def render_thumbnail(self, max_width=200):
        page_width = self.width
        zoom = max_width / page_width if page_width > 0 else 0.1
        return self.render(zoom)

    def get_text(self):
        return self._page.get_text("text")

    def get_text_blocks(self):
        return self._page.get_text("blocks")

    def get_text_words(self):
        return self._page.get_text("words")

    def get_images(self, full=True):
        return self._page.get_images(full=full)

    def search(self, text, hit_max=100):
        return self._page.search_for(text, hit_max=hit_max)

    def get_links(self):
        return self._page.get_links()

    def get_annotations(self):
        return list(self._page.annots())

    def add_annotation(self, annot_type, rect, **kwargs):
        method_map = {
            "Highlight": self._page.add_highlight_annot,
            "Underline": self._page.add_underline_annot,
            "StrikeOut": self._page.add_strikeout_annot,
            "Squiggly": self._page.add_squiggly_annot,
            "Text": self._page.add_text_annot,
            "FreeText": self._page.add_freetext_annot,
            "Stamp": self._page.add_stamp_annot,
            "Line": self._page.add_line_annot,
            "Square": self._page.add_rect_annot,
            "Circle": self._page.add_circle_annot,
            "Polygon": self._page.add_polygon_annot,
            "PolyLine": self._page.add_polyline_annot,
            "Ink": self._page.add_ink_annot,
            "FileAttachment": self._page.add_file_annot,
            "Caret": self._page.add_caret_annot,
            "Redaction": self._page.add_redact_annot,
        }
        method = method_map.get(annot_type)
        if method:
            if annot_type in ("Line", "Arrow"):
                p1 = rect.topLeft()
                p2 = rect.bottomRight()
                return method(p1, p2, **kwargs)
            return method(rect, **kwargs)
        return None

    def __del__(self):
        pass
