import os
import io

import fitz
from PIL import Image


class Importer:
    def from_image(self, filepath, output_path=None):
        if not os.path.isfile(filepath):
            return False, f"File not found: {filepath}", ""

        try:
            img = Image.open(filepath)
        except Exception as e:
            return False, f"Cannot open image: {e}", ""

        if output_path is None:
            stem = os.path.splitext(filepath)[0]
            output_path = stem + ".pdf"

        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        doc = fitz.open()
        page = doc.new_page(width=img.width, height=img.height)
        rect = page.rect

        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        page.insert_image(rect, stream=img_bytes.getvalue())

        doc.save(output_path, deflate=True)
        doc.close()
        return True, "Image converted to PDF successfully", output_path

    def from_docx(self, filepath, output_path=None):
        if not os.path.isfile(filepath):
            return False, f"File not found: {filepath}", ""

        try:
            from docx import Document as DocxDocument
        except ImportError:
            return False, "python-docx is not installed", ""

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
        except ImportError:
            return False, "reportlab is not installed", ""

        if output_path is None:
            stem = os.path.splitext(filepath)[0]
            output_path = stem + ".pdf"

        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        try:
            docx_doc = DocxDocument(filepath)
        except Exception as e:
            return False, f"Cannot open DOCX: {e}", ""

        styles = getSampleStyleSheet()
        story = []

        for para in docx_doc.paragraphs:
            if para.text.strip():
                p = Paragraph(para.text, styles["Normal"])
                story.append(p)
                story.append(Spacer(1, 0.1 * inch))

        pdf = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )
        pdf.build(story)
        return True, "DOCX converted to PDF successfully", output_path

    def merge_images(self, filepaths, output_path=None):
        if not filepaths:
            return False, "No image files provided", ""

        valid = []
        for fp in filepaths:
            if os.path.isfile(fp):
                valid.append(fp)
        if not valid:
            return False, "No valid image files found", ""

        if output_path is None:
            basedir = os.path.dirname(os.path.abspath(valid[0]))
            output_path = os.path.join(basedir, "merged.pdf")

        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        doc = fitz.open()
        for fp in valid:
            try:
                img = Image.open(fp)
                img_rgb = img.convert("RGB")
                img_bytes = io.BytesIO()
                img_rgb.save(img_bytes, format="PNG")
                pix = fitz.Pixmap(img_bytes.getvalue())

                page = doc.new_page(width=img_rgb.width, height=img_rgb.height)
                page.insert_image(page.rect, stream=img_bytes.getvalue())
            except Exception:
                continue

        if doc.page_count == 0:
            doc.close()
            return False, "No pages could be created from the provided images", ""

        doc.save(output_path, deflate=True)
        doc.close()
        return True, f"Merged {doc.page_count} image(s) into PDF", output_path
