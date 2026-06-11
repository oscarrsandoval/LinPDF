import fitz
from PySide6.QtCore import Signal, QObject

from linpdf.core.page import Page


class Document(QObject):
    document_loaded = Signal()
    document_closed = Signal()
    document_modified = Signal()
    page_count_changed = Signal(int)
    current_page_changed = Signal(int)
    saving = Signal()
    saved = Signal()

    def __init__(self):
        super().__init__()
        self._doc = None
        self._path = None
        self._modified = False
        self._current_page_index = 0

    @property
    def path(self):
        return self._path

    @property
    def is_loaded(self):
        return self._doc is not None

    @property
    def is_modified(self):
        return self._modified

    @property
    def page_count(self):
        return len(self._doc) if self._doc else 0

    @property
    def current_page_index(self):
        return self._current_page_index

    def open(self, path):
        if self._doc:
            self.close()
        self._doc = fitz.open(path)
        self._path = path
        self._modified = False
        self._current_page_index = 0
        self.document_loaded.emit()
        self.page_count_changed.emit(self.page_count)
        self.current_page_changed.emit(0)

    def save(self, path=None):
        if not self._doc:
            return False
        target = path or self._path
        if not target:
            return False
        self.saving.emit()
        self._doc.save(
            target,
            incremental=False,
            deflate=True,
            clean=True,
        )
        self._path = target
        self._modified = False
        self.saved.emit()
        self.document_modified.emit()
        return True

    def save_as(self, path):
        return self.save(path)

    def close(self):
        if self._doc:
            self._doc.close()
            self._doc = None
            self._path = None
            self._modified = False
            self._current_page_index = 0
            self.document_closed.emit()

    def get_page(self, index):
        if self._doc and 0 <= index < len(self._doc):
            return Page(self._doc[index])
        return None

    def get_page_rect(self, index):
        if self._doc and 0 <= index < len(self._doc):
            rect = self._doc[index].rect
            return rect.width, rect.height
        return 0, 0

    def get_metadata(self):
        if not self._doc:
            return {}
        return dict(self._doc.metadata)

    def get_table_of_contents(self):
        if not self._doc:
            return []
        return self._doc.get_toc()

    def mark_modified(self):
        if not self._modified:
            self._modified = True
            self.document_modified.emit()

    def __del__(self):
        if self._doc:
            self._doc.close()
