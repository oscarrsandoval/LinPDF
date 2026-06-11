import fitz
import os


class PageManager:
    def __init__(self, document):
        self._doc = document

    def _fitz_doc(self):
        return self._doc._doc

    def _mark_modified(self):
        self._doc.mark_modified()

    def _emit_page_count(self):
        self._doc.page_count_changed.emit(self._doc.page_count)

    def insert_blank_page(self, index, width=595, height=842):
        doc = self._fitz_doc()
        if not doc:
            return False
        try:
            rect = fitz.Rect(0, 0, width, height)
            if index < 0 or index > len(doc):
                index = len(doc)
            doc.new_page(pno=index, width=width, height=height)
            self._mark_modified()
            self._emit_page_count()
            return True
        except Exception:
            return False

    def insert_from_file(self, index, filepath):
        doc = self._fitz_doc()
        if not doc or not os.path.isfile(filepath):
            return False
        try:
            src = fitz.open(filepath)
            doc.insert_pdf(src, from_page=0, to_page=len(src) - 1, start_at=index)
            src.close()
            self._mark_modified()
            self._emit_page_count()
            return True
        except Exception:
            return False

    def delete_page(self, index):
        doc = self._fitz_doc()
        if not doc or index < 0 or index >= len(doc):
            return False
        try:
            doc.delete_page(index)
            self._mark_modified()
            self._emit_page_count()
            return True
        except Exception:
            return False

    def rotate_page(self, index, degrees=90):
        doc = self._fitz_doc()
        if not doc or index < 0 or index >= len(doc):
            return False
        valid = {90, 180, 270}
        if degrees not in valid:
            return False
        try:
            page = doc[index]
            page.set_rotation(degrees)
            self._mark_modified()
            return True
        except Exception:
            return False

    def crop_page(self, index, rect):
        doc = self._fitz_doc()
        if not doc or index < 0 or index >= len(doc):
            return False
        try:
            page = doc[index]
            page.set_cropbox(rect)
            self._mark_modified()
            return True
        except Exception:
            return False

    def extract_page(self, index, output_path):
        doc = self._fitz_doc()
        if not doc or index < 0 or index >= len(doc):
            return False
        try:
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=index, to_page=index)
            new_doc.save(output_path, deflate=True)
            new_doc.close()
            return True
        except Exception:
            return False

    def replace_page(self, index, filepath, source_index=0):
        doc = self._fitz_doc()
        if not doc or index < 0 or index >= len(doc) or not os.path.isfile(filepath):
            return False
        try:
            src = fitz.open(filepath)
            if source_index < 0 or source_index >= len(src):
                src.close()
                return False
            doc.insert_pdf(src, from_page=source_index, to_page=source_index, start_at=index + 1)
            doc.delete_page(index)
            src.close()
            self._mark_modified()
            return True
        except Exception:
            return False

    def split_document(self, output_pattern):
        doc = self._fitz_doc()
        if not doc:
            return False
        try:
            for i in range(len(doc)):
                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=i, to_page=i)
                path = output_pattern.format(page=i + 1)
                new_doc.save(path, deflate=True)
                new_doc.close()
            return True
        except Exception:
            return False

    def merge_document(self, filepaths):
        doc = self._fitz_doc()
        if not doc:
            return False
        try:
            for filepath in filepaths:
                if not os.path.isfile(filepath):
                    continue
                src = fitz.open(filepath)
                doc.insert_pdf(src)
                src.close()
            self._mark_modified()
            self._emit_page_count()
            return True
        except Exception:
            return False

    def move_page(self, from_index, to_index):
        doc = self._fitz_doc()
        if not doc:
            return False
        n = len(doc)
        if from_index < 0 or from_index >= n or to_index < 0 or to_index >= n:
            return False
        if from_index == to_index:
            return True
        try:
            doc.move_page(from_index, to_index)
            self._mark_modified()
            return True
        except Exception:
            return False

    def duplicate_page(self, index):
        doc = self._fitz_doc()
        if not doc or index < 0 or index >= len(doc):
            return False
        try:
            doc.insert_pdf(doc, from_page=index, to_page=index, start_at=index + 1)
            self._mark_modified()
            self._emit_page_count()
            return True
        except Exception:
            return False
