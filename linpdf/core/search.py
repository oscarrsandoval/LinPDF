from PySide6.QtCore import QObject, Signal


class SearchResult:
    def __init__(self, page_index, text, quads, bbox):
        self.page_index = page_index
        self.text = text
        self.quads = quads
        self.bbox = bbox


class Searcher(QObject):
    search_started = Signal()
    search_finished = Signal(list)
    search_progress = Signal(int, int)

    def __init__(self):
        super().__init__()
        self._document = None

    def set_document(self, document):
        self._document = document

    def search(self, text, start_page=0, end_page=None):
        if not self._document or not self._document.is_loaded:
            self.search_finished.emit([])
            return

        results = []
        doc = self._document
        end = end_page or doc.page_count

        self.search_started.emit()

        for i in range(start_page, end):
            self.search_progress.emit(i - start_page, end - start_page)
            page = doc.get_page(i)
            if not page:
                continue

            matches = page.search(text)
            for m in matches:
                result = SearchResult(
                    page_index=i,
                    text=text,
                    quads=None,
                    bbox=m,
                )
                results.append(result)

        self.search_finished.emit(results)
