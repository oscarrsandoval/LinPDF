import os
import fitz

from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout,
    QStatusBar, QLabel, QFileDialog, QMessageBox,
    QInputDialog, QDialog, QColorDialog,
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QAction, QKeySequence, QColor

from linpdf.constants import (
    APP_NAME, APP_VERSION, ToolMode, AnnotationType,
)
from linpdf.config import Config
from linpdf.core.document import Document
from linpdf.core.renderer import Renderer
from linpdf.ui.ribbon.ribbon_bar import RibbonBar
from linpdf.ui.viewer.pdf_viewer import PDFViewer
from linpdf.ui.viewer.thumbnail_panel import ThumbnailWidget
from linpdf.annotations.annotation_manager import AnnotationManager
from linpdf.annotations.properties_dialog import PropertiesDialog
from linpdf.page_management.page_manager import PageManager
from linpdf.page_management.watermark import (
    add_text_watermark, add_page_numbers,
    add_header, add_footer,
)
from linpdf.conversion.exporter import Exporter
from linpdf.conversion.importer import Importer
from linpdf.conversion.ocr_processor import OCRProcessor
from linpdf.security.pdf_security import PDFSecurity
from linpdf.forms.form_manager import FormManager


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._config = Config()
        self._document = Document()
        self._renderer = Renderer()
        self._current_file = None
        self._current_tool = ToolMode.SELECT

        self._setup_window()
        self._create_managers()
        self._create_ribbon()
        self._create_viewer()
        self._create_status_bar()
        self._create_menu_bar()
        self._connect_signals()
        self._restore_state()

    def _setup_window(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1024, 700)
        self.resize(1280, 800)

    def _create_managers(self):
        self._page_manager = PageManager(self._document)
        self._exporter = Exporter(self._document)
        self._importer = Importer()
        self._ocr = OCRProcessor(self._document)
        self._security = PDFSecurity()
        self._forms = FormManager()

    def _create_ribbon(self):
        self._ribbon = RibbonBar(self)

        home = self._ribbon.add_tab("Home")
        file_panel = home.add_panel("File")
        self._btn_open = file_panel.add_button("Open", tooltip="Open PDF (Ctrl+O)")
        self._btn_save = file_panel.add_button("Save", tooltip="Save PDF (Ctrl+S)")
        self._btn_save_as = file_panel.add_button("Save As", tooltip="Save as new file")
        self._btn_print = file_panel.add_button("Print", tooltip="Print PDF (Ctrl+P)")

        edit_panel = home.add_panel("Edit")
        self._btn_undo = edit_panel.add_button("Undo", tooltip="Undo (Ctrl+Z)")
        self._btn_redo = edit_panel.add_button("Redo", tooltip="Redo (Ctrl+Y)")
        edit_panel.add_separator()
        self._btn_select = edit_panel.add_button("Select", tooltip="Select text/objects", checkable=True)
        self._btn_pan = edit_panel.add_button("Pan", tooltip="Pan mode", checkable=True)
        self._btn_select.setChecked(True)

        annot_panel = home.add_panel("Annotate")
        self._btn_highlight = annot_panel.add_button("Highlight", tooltip="Highlight text")
        self._btn_underline = annot_panel.add_button("Underline", tooltip="Underline text")
        self._btn_strikeout = annot_panel.add_button("Strikeout", tooltip="Strikeout text")
        self._btn_note = annot_panel.add_button("Note", tooltip="Add sticky note")

        view_panel = home.add_panel("View")
        self._btn_zoom_in = view_panel.add_button("Zoom In", tooltip="Zoom in (Ctrl++)")
        self._btn_zoom_out = view_panel.add_button("Zoom Out", tooltip="Zoom out (Ctrl+-)")
        self._btn_fit_width = view_panel.add_button("Fit Width", tooltip="Fit page width")
        self._btn_fit_page = view_panel.add_button("Fit Page", tooltip="Fit whole page")

        insert = self._ribbon.add_tab("Insert")
        pages_panel = insert.add_panel("Pages")
        self._btn_blank_page = pages_panel.add_button("Blank Page", tooltip="Insert blank page")
        self._btn_from_file = pages_panel.add_button("From File", tooltip="Insert pages from another PDF")
        insert_panel = insert.add_panel("Insert")
        self._btn_insert_image = insert_panel.add_button("Image", tooltip="Insert image")
        self._btn_link = insert_panel.add_button("Link", tooltip="Insert hyperlink")
        stamp_panel = insert.add_panel("Stamps")
        self._btn_stamp = stamp_panel.add_button("Stamp", tooltip="Add stamp")

        page_tab = self._ribbon.add_tab("Page Layout")
        org_panel = page_tab.add_panel("Organize")
        self._btn_rotate_cw = org_panel.add_button("Rotate CW", tooltip="Rotate page clockwise")
        self._btn_rotate_ccw = org_panel.add_button("Rotate CCW", tooltip="Rotate counter-clockwise")
        self._btn_delete_page = org_panel.add_button("Delete", tooltip="Delete current page")
        self._btn_extract = org_panel.add_button("Extract", tooltip="Extract current page")

        review = self._ribbon.add_tab("Review")
        protect_panel = review.add_panel("Protect")
        self._btn_encrypt = protect_panel.add_button("Encrypt", tooltip="Password protect PDF")
        self._btn_sign = protect_panel.add_button("Sign", tooltip="Digitally sign")
        self._btn_redact = protect_panel.add_button("Redact", tooltip="Redact sensitive content")

        convert = self._ribbon.add_tab("Convert")
        export_panel = convert.add_panel("Export To")
        self._btn_to_word = export_panel.add_button("Word", tooltip="Export to Microsoft Word")
        self._btn_to_excel = export_panel.add_button("Excel", tooltip="Export to Microsoft Excel")
        self._btn_to_ppt = export_panel.add_button("PowerPoint", tooltip="Export to PowerPoint")
        export_panel.add_separator()
        self._btn_to_image = export_panel.add_button("Image", tooltip="Export as images")
        ocr_panel = convert.add_panel("OCR")
        self._btn_ocr = ocr_panel.add_button("OCR", tooltip="Recognize text in scanned document")

        forms = self._ribbon.add_tab("Forms")
        form_panel = forms.add_panel("Forms")
        self._btn_fill_form = form_panel.add_button("Fill Form", tooltip="Fill interactive form")
        self._btn_create_form = form_panel.add_button("Create Form", tooltip="Create form fields")

        self._wire_ribbon_buttons()
        self._ribbon.set_active_tab("Home")

    def _wire_ribbon_buttons(self):
        self._btn_open.clicked.connect(self.open_file)
        self._btn_save.clicked.connect(self.save_file)
        self._btn_save_as.clicked.connect(self.save_file_as)
        self._btn_print.clicked.connect(self.print_file)
        self._btn_zoom_in.clicked.connect(lambda: self._viewer.zoom_in())
        self._btn_zoom_out.clicked.connect(lambda: self._viewer.zoom_out())
        self._btn_fit_width.clicked.connect(lambda: self._viewer.fit_width())
        self._btn_fit_page.clicked.connect(lambda: self._viewer.fit_page())
        self._btn_select.clicked.connect(lambda: self._set_tool(ToolMode.SELECT))
        self._btn_pan.clicked.connect(lambda: self._set_tool(ToolMode.PAN))
        self._btn_delete_page.clicked.connect(self._delete_current_page)
        self._btn_encrypt.clicked.connect(self._encrypt_document)
        self._btn_sign.clicked.connect(self._sign_document)
        self._btn_redact.clicked.connect(self._redact_document)
        self._btn_to_word.clicked.connect(lambda: self._export_file("docx"))
        self._btn_to_excel.clicked.connect(lambda: self._export_file("xlsx"))
        self._btn_to_ppt.clicked.connect(lambda: self._export_file("pptx"))
        self._btn_to_image.clicked.connect(self._export_images)
        self._btn_ocr.clicked.connect(self._run_ocr)
        self._btn_blank_page.clicked.connect(self._insert_blank_page)
        self._btn_from_file.clicked.connect(self._insert_from_file)
        self._btn_insert_image.clicked.connect(self._insert_image)
        self._btn_link.clicked.connect(self._show_coming_soon)
        self._btn_stamp.clicked.connect(self._add_stamp)
        self._btn_rotate_cw.clicked.connect(lambda: self._rotate_page(90))
        self._btn_rotate_ccw.clicked.connect(lambda: self._rotate_page(270))
        self._btn_extract.clicked.connect(self._extract_page)
        self._btn_highlight.clicked.connect(lambda: self._set_tool(ToolMode.HIGHLIGHT))
        self._btn_underline.clicked.connect(lambda: self._set_tool(ToolMode.UNDERLINE))
        self._btn_strikeout.clicked.connect(lambda: self._set_tool(ToolMode.STRIKEOUT))
        self._btn_note.clicked.connect(lambda: self._set_tool(ToolMode.NOTE))
        self._btn_fill_form.clicked.connect(self._fill_form)
        self._btn_create_form.clicked.connect(self._create_form)
        self._btn_undo.clicked.connect(self._undo)
        self._btn_redo.clicked.connect(self._redo)

    def _create_status_bar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._page_label = QLabel("No document")
        self._zoom_label = QLabel("100%")
        self._file_label = QLabel("")

        self._status_bar.addWidget(self._page_label)
        self._status_bar.addPermanentWidget(self._zoom_label)
        self._status_bar.addPermanentWidget(self._file_label)

    def _create_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&Open...", self.open_file, QKeySequence.Open)
        file_menu.addAction("&Save", self.save_file, QKeySequence.Save)
        file_menu.addAction("Save &As...", self.save_file_as, QKeySequence("Ctrl+Shift+S"))
        file_menu.addSeparator()
        file_menu.addAction("&Print...", self.print_file, QKeySequence.Print)
        file_menu.addSeparator()
        file_menu.addAction("&Close", self.close_file)
        file_menu.addAction("E&xit", self.close, QKeySequence.Quit)

        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction("&Undo", self._undo, QKeySequence.Undo)
        edit_menu.addAction("&Redo", self._redo, QKeySequence("Ctrl+Y"))
        edit_menu.addSeparator()
        edit_menu.addAction("&Delete Page", self._delete_current_page)
        edit_menu.addAction("&Extract Page", self._extract_page)

        view_menu = menubar.addMenu("&View")
        view_menu.addAction("Zoom &In", lambda: self._viewer.zoom_in(), QKeySequence.ZoomIn)
        view_menu.addAction("Zoom &Out", lambda: self._viewer.zoom_out(), QKeySequence.ZoomOut)
        view_menu.addSeparator()
        self._toggle_thumb_action = view_menu.addAction(
            "&Thumbnail Panel",
            self._toggle_thumbnail_panel,
            QKeySequence("Ctrl+T"),
        )
        self._toggle_thumb_action.setCheckable(True)
        self._toggle_thumb_action.setChecked(True)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About", self._show_about)

    def _connect_signals(self):
        self._document.document_loaded.connect(self._on_document_loaded)
        self._document.document_closed.connect(self._on_document_closed)
        self._document.document_modified.connect(self._on_document_modified)
        self._document.page_count_changed.connect(self._on_page_count_changed)
        self._viewer.zoom_changed.connect(self._on_zoom_changed)
        self._viewer.page_changed.connect(self._on_page_changed)
        self._viewer.document_dropped.connect(self.open_path)
        self._thumbnail_panel.page_selected.connect(self._viewer.go_to_page)

    def _ensure_document(self):
        if not self._document.is_loaded:
            QMessageBox.information(self, "No Document", "Please open a PDF first.")
            return False
        return True

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF",
            self._config.last_directory,
            "PDF Files (*.pdf);;All Files (*)",
        )
        if path:
            self.open_path(path)

    def open_path(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "File Not Found", f"Cannot find:\n{path}")
            return
        try:
            self._document.open(path)
            self._current_file = path
            self._config.last_directory = os.path.dirname(path)
            self._config.add_recent_file(path)

            if self._document.is_loaded:
                self._annot_mgr = AnnotationManager(
                    self._document,
                    self._viewer._scene,
                )
                self._annot_mgr.load_all_annotations(self._viewer.zoom)
        except Exception as e:
            QMessageBox.critical(self, "Open Failed", f"Failed to open PDF:\n{e}")

    def save_file(self):
        if self._current_file and (self._document.is_modified or (self._annot_mgr and self._annot_mgr.has_undo())):
            self._document.save(self._current_file)
        elif not self._current_file:
            self.save_file_as()

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF As",
            self._config.last_directory,
            "PDF Files (*.pdf)",
        )
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self._document.save(path)
            self._current_file = path

    def close_file(self):
        if self._document.is_modified:
            ret = QMessageBox.question(
                self, "Unsaved Changes",
                "Save changes before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            )
            if ret == QMessageBox.Save:
                self.save_file()
            elif ret == QMessageBox.Cancel:
                return
        self._document.close()

    def print_file(self):
        self._show_coming_soon()

    def _undo(self):
        if self._annot_mgr:
            self._annot_mgr.undo()

    def _redo(self):
        if self._annot_mgr:
            self._annot_mgr.redo()

    def _delete_current_page(self):
        if not self._ensure_document():
            return
        index = self._viewer.get_current_page()
        if self._document.page_count <= 1:
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete the last page.")
            return
        ret = QMessageBox.question(
            self, "Delete Page",
            f"Delete page {index + 1}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret == QMessageBox.Yes:
            self._page_manager.delete_page(index)
            self._rebuild_viewer()

    def _extract_page(self):
        if not self._ensure_document():
            return
        index = self._viewer.get_current_page()
        path, _ = QFileDialog.getSaveFileName(
            self, "Extract Page As",
            self._config.last_directory,
            "PDF Files (*.pdf)",
        )
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            success = self._page_manager.extract_page(index, path)
            if success:
                QMessageBox.information(self, "Extracted", f"Page {index + 1} saved.")
            else:
                QMessageBox.warning(self, "Error", "Failed to extract page.")

    def _rotate_page(self, degrees):
        if not self._ensure_document():
            return
        index = self._viewer.get_current_page()
        self._page_manager.rotate_page(index, degrees)
        self._rebuild_viewer()

    def _insert_blank_page(self):
        if not self._ensure_document():
            return
        index = self._viewer.get_current_page() + 1
        self._page_manager.insert_blank_page(index)
        self._rebuild_viewer()
        self._viewer.go_to_page(index)

    def _insert_from_file(self):
        if not self._ensure_document():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Insert PDF", self._config.last_directory, "PDF Files (*.pdf)",
        )
        if path:
            index = self._viewer.get_current_page() + 1
            self._page_manager.insert_from_file(index, path)
            self._rebuild_viewer()

    def _insert_image(self):
        self._show_coming_soon()

    def _add_stamp(self):
        if not self._ensure_document():
            return
        stamps = ["DRAFT", "CONFIDENTIAL", "APPROVED", "REVIEWED", "RECEIVED",
                  "VOID", "SIGNED", "INITIALED", "COMPLETED", "REJECTED"]
        stamp, ok = QInputDialog.getItem(self, "Select Stamp", "Stamp:", stamps, 0, False)
        if ok and stamp:
            index = self._viewer.get_current_page()
            page = self._document.get_page(index)
            if page:
                w, h = page.width, page.height
                rect = QRectF(w * 0.3, h * 0.3, w * 0.4, h * 0.15)
                if self._annot_mgr:
                    data = {
                        'page_index': index,
                        'type': AnnotationType.STAMP,
                        'rect': rect,
                        'icon': stamp,
                        'color': (1, 0, 0),
                        'fill_color': (1, 1, 0),
                        'opacity': 0.7,
                        'author': "LinPDF User",
                    }
                    self._annot_mgr.create_annotation(data, self._viewer.zoom)

    def _export_file(self, fmt):
        if not self._ensure_document():
            return
        filters = {
            "docx": "Word Documents (*.docx)",
            "xlsx": "Excel Files (*.xlsx)",
            "pptx": "PowerPoint Files (*.pptx)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self, f"Export as {fmt.upper()}",
            self._config.last_directory,
            filters.get(fmt, f"*.{fmt}"),
        )
        if not path:
            return
        if not path.lower().endswith(f".{fmt}"):
            path += f".{fmt}"

        methods = {
            "docx": self._exporter.to_docx,
            "xlsx": self._exporter.to_xlsx,
            "pptx": self._exporter.to_pptx,
        }
        method = methods.get(fmt)
        if method:
            self._status_bar.showMessage(f"Exporting to {fmt.upper()}...")
            success, msg, out_path = method(path)
            if success:
                self._status_bar.showMessage(f"Exported to {out_path}", 5000)
                QMessageBox.information(self, "Export Complete", f"Saved to:\n{out_path}")
            else:
                self._status_bar.showMessage(f"Export failed: {msg}", 5000)
                QMessageBox.warning(self, "Export Failed", msg)

    def _export_images(self):
        if not self._ensure_document():
            return
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self._config.last_directory)
        if not folder:
            return
        self._status_bar.showMessage("Exporting images...")
        success, msg, out_path = self._exporter.to_image(folder)
        if success:
            self._status_bar.showMessage("Images exported.", 5000)
            QMessageBox.information(self, "Export Complete", f"Images saved to:\n{folder}")
        else:
            self._status_bar.showMessage(f"Export failed: {msg}", 5000)
            QMessageBox.warning(self, "Export Failed", msg)

    def _run_ocr(self):
        if not self._ensure_document():
            return
        ret = QMessageBox.question(
            self, "Run OCR",
            "Recognize text in all pages? This may take a while.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret == QMessageBox.Yes:
            self._status_bar.showMessage("Running OCR...")
            path = self._current_file + ".ocr.pdf" if self._current_file else "/tmp/ocr_output.pdf"
            try:
                self._ocr.make_searchable(path)
                self._status_bar.showMessage("OCR complete.", 5000)
                QMessageBox.information(self, "OCR Complete", f"Searchable PDF saved to:\n{path}")
            except Exception as e:
                self._status_bar.showMessage("OCR failed.", 5000)
                QMessageBox.warning(self, "OCR Failed", str(e))

    def _encrypt_document(self):
        if not self._ensure_document():
            return
        password, ok = QInputDialog.getText(
            self, "Encrypt PDF", "Enter password:",
            echo=QInputDialog.Password,
        )
        if ok and password:
            success, msg, _ = self._security.encrypt(self._document, password)
            if success:
                QMessageBox.information(self, "Encrypted", "Document encrypted.")
            else:
                QMessageBox.warning(self, "Encryption Failed", msg)

    def _sign_document(self):
        if not self._ensure_document():
            return
        cert_path, _ = QFileDialog.getOpenFileName(
            self, "Select Certificate",
            "", "Certificate Files (*.p12 *.pfx);;All Files (*)",
        )
        if not cert_path:
            return
        password, ok = QInputDialog.getText(
            self, "Certificate Password", "Enter certificate password:",
            echo=QInputDialog.Password,
        )
        if not ok:
            return
        index = self._viewer.get_current_page()
        page = self._document.get_page(index)
        if page:
            w, h = page.width, page.height
            rect = fitz.Rect(w * 0.5, h * 0.7, w * 0.85, h * 0.85)
            success, msg, _ = self._security.sign_page(
                self._document, index, rect, cert_path, password,
                reason="Document approval", location="",
            )
            if success:
                QMessageBox.information(self, "Signed", "Signature added.")
                self._rebuild_viewer()
            else:
                QMessageBox.warning(self, "Sign Failed", msg)

    def _redact_document(self):
        if not self._ensure_document():
            return
        text, ok = QInputDialog.getText(
            self, "Redact Text", "Enter text to redact:",
        )
        if ok and text:
            self._status_bar.showMessage("Redacting...")
            success, msg, details = self._security.redact_text(self._document, text)
            if success:
                ret = QMessageBox.question(
                    self, "Apply Redactions",
                    f"Found redactions in pages. Apply permanently?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if ret == QMessageBox.Yes:
                    self._security.apply_redactions(self._document)
                    QMessageBox.information(self, "Redacted", "Redactions applied.")
                    self._rebuild_viewer()
            else:
                QMessageBox.warning(self, "Redaction Failed", msg)

    def _fill_form(self):
        if not self._ensure_document():
            return
        success, msg, data = self._forms.get_form_fields(self._document)
        if not success:
            QMessageBox.warning(self, "Form Error", msg)
            return
        fields = data.get("fields", [])
        if not fields:
            QMessageBox.information(self, "No Fields", "No form fields found.")
            return
        QMessageBox.information(
            self, "Form Fields",
            f"Found {len(fields)} form field(s).\nForm filling dialog coming in next update.",
        )

    def _create_form(self):
        self._show_coming_soon()

    def _rebuild_viewer(self):
        self._renderer.clear_cache()
        self._viewer.set_document(self._document, self._renderer)
        self._thumbnail_panel.refresh()
        if self._annot_mgr:
            self._annot_mgr.rebuild_all(self._viewer.zoom)

    def _set_tool(self, mode):
        self._current_tool = mode
        is_select = mode == ToolMode.SELECT
        is_pan = mode == ToolMode.PAN
        self._btn_select.setChecked(is_select)
        self._btn_pan.setChecked(is_pan)

        if is_pan:
            self._viewer.setDragMode(self._viewer.ScrollHandDrag)
            if self._annot_mgr:
                self._annot_mgr.set_active_tool(None)
        elif is_select:
            self._viewer.setDragMode(self._viewer.RubberBandDrag)
            if self._annot_mgr:
                self._annot_mgr.set_active_tool(None)
        else:
            self._viewer.setDragMode(self._viewer.NoDrag)
            if self._annot_mgr:
                tool_map = {
                    ToolMode.HIGHLIGHT: AnnotationType.HIGHLIGHT,
                    ToolMode.UNDERLINE: AnnotationType.UNDERLINE,
                    ToolMode.STRIKEOUT: AnnotationType.STRIKEOUT,
                    ToolMode.NOTE: AnnotationType.TEXT,
                }
                atype = tool_map.get(mode)
                if atype:
                    self._annot_mgr.set_active_tool(atype)

    def _create_viewer(self):
        self._viewer = PDFViewer()
        self._thumbnail_panel = ThumbnailWidget()
        self._annot_mgr = None

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.addWidget(self._thumbnail_panel)
        self._splitter.addWidget(self._viewer)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([200, 800])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._ribbon)
        layout.addWidget(self._splitter)
        self.setCentralWidget(central)

    def _toggle_thumbnail_panel(self):
        visible = self._thumbnail_panel.isVisible()
        self._thumbnail_panel.setVisible(not visible)
        self._toggle_thumb_action.setChecked(not visible)

    def _on_document_loaded(self):
        self._renderer.clear_cache()
        self._viewer.set_document(self._document, self._renderer)
        self._thumbnail_panel.set_document(self._document, self._renderer)

        if self._document.is_loaded:
            self._annot_mgr = AnnotationManager(
                self._document,
                self._viewer._scene,
            )
            self._annot_mgr.load_all_annotations(self._viewer.zoom)

        self._update_title()
        self._page_label.setText(f"Page 1 of {self._document.page_count}")

    def _on_document_closed(self):
        self._viewer.clear()
        self._thumbnail_panel.clear()
        self._annot_mgr = None
        self._current_file = None
        self._update_title()
        self._page_label.setText("No document")

    def _on_document_modified(self):
        self._update_title()

    def _on_page_count_changed(self, count):
        self._thumbnail_panel.refresh()

    def _on_page_changed(self, index):
        self._thumbnail_panel.select_page(index)
        total = self._document.page_count if self._document else 0
        self._page_label.setText(f"Page {index + 1} of {total}")

    def _on_zoom_changed(self, zoom):
        percent = int(zoom * 100)
        self._zoom_label.setText(f"{percent}%")
        if self._annot_mgr:
            self._annot_mgr.rebuild_all(zoom)

    def _update_title(self):
        title = APP_NAME
        if self._current_file:
            name = os.path.basename(self._current_file)
            title = f"{name} - {APP_NAME}"
            if self._document.is_modified:
                title += " *"
        self.setWindowTitle(title)

    def _restore_state(self):
        geom = self._config.window_geometry
        if geom:
            self.restoreGeometry(geom)
        state = self._config.window_state
        if state:
            self.restoreState(state)

    def closeEvent(self, event):
        if self._document.is_loaded and self._document.is_modified:
            ret = QMessageBox.question(
                self, "Unsaved Changes",
                "Save changes before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            )
            if ret == QMessageBox.Save:
                self.save_file()
            elif ret == QMessageBox.Cancel:
                event.ignore()
                return

        self._config.window_geometry = self.saveGeometry()
        self._config.window_state = self.saveState()
        self._document.close()
        super().closeEvent(event)

    def _show_coming_soon(self):
        btn = self.sender()
        feature = btn.text() if btn else "This feature"
        QMessageBox.information(
            self, "Coming Soon",
            f"{feature} will be available in a future update.",
        )

    def _show_about(self):
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            "<p>A Linux-native PDF editor inspired by Foxit PDF Editor.</p>"
            "<p>Built with Python, PySide6, and PyMuPDF.</p>",
        )
