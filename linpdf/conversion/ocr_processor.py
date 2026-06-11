import io
import os

import fitz
from PIL import Image

from linpdf.core.document import Document


class OCRProcessor:
    def __init__(self, document: Document):
        self._doc = document

    def _ensure_doc_loaded(self):
        if not self._doc.is_loaded:
            return False, "No document is open"
        return None

    def _get_tesseract(self):
        try:
            import pytesseract
            return pytesseract
        except ImportError:
            return None

    def recognize_page(self, page_index, language="eng"):
        err = self._ensure_doc_loaded()
        if err:
            return err

        tesseract = self._get_tesseract()
        if tesseract is None:
            return False, "pytesseract is not installed"

        src = self._doc._doc
        if page_index < 0 or page_index >= len(src):
            return False, f"Page index {page_index} out of range"

        page = src[page_index]
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        try:
            text = tesseract.image_to_string(img, lang=language)
            return True, text
        except Exception as e:
            return False, f"OCR failed: {e}"

    def recognize_document(self, language="eng"):
        err = self._ensure_doc_loaded()
        if err:
            return err

        tesseract = self._get_tesseract()
        if tesseract is None:
            return False, "pytesseract is not installed"

        src = self._doc._doc
        results = []
        for i in range(len(src)):
            page = src[i]
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            try:
                text = tesseract.image_to_string(img, lang=language)
                results.append((i, text))
            except Exception as e:
                results.append((i, f"[OCR failed: {e}]"))

        return True, results

    def make_searchable(self, output_path, language="eng"):
        err = self._ensure_doc_loaded()
        if err:
            return err

        tesseract = self._get_tesseract()
        if tesseract is None:
            return False, "pytesseract is not installed"

        src = self._doc._doc
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        new_doc = fitz.open()

        for i in range(len(src)):
            src_page = src[i]
            rect = src_page.rect

            pix = src_page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            pil_img = Image.open(io.BytesIO(img_bytes))

            data = tesseract.image_to_data(
                pil_img, lang=language, output_type=tesseract.Output.DICT
            )

            new_page = new_doc.new_page(width=rect.width, height=rect.height)
            new_page.insert_image(rect, stream=img_bytes)

            scale_x = rect.width / pix.width
            scale_y = rect.height / pix.height

            for j in range(len(data["text"])):
                word = data["text"][j].strip()
                if not word:
                    continue
                conf = int(data["conf"][j])
                if conf < 10:
                    continue

                x = data["left"][j] * scale_x
                y = (data["top"][j] + data["height"][j]) * scale_y
                h = data["height"][j] * scale_y
                font_size = max(h * 1.1, 4)

                new_page.insert_text(
                    fitz.Point(x, y),
                    word,
                    fontname="helv",
                    fontsize=font_size,
                    stroke_opacity=0,
                    fill_opacity=0,
                )

        new_doc.save(output_path, deflate=True)
        new_doc.close()
        return True, f"Searchable PDF saved to {output_path}", output_path
