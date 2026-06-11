import os

from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout,
    QStatusBar, QLabel, QFileDialog, QMessageBox,
    QApplication, QMenuBar, QMenu, QToolBar,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence, QIcon, QPixmap

from linpdf.constants import (
    APP_NAME, APP_VERSION, ToolMode, ViewMode,
    DEFAULT_ZOOM, FILE_EXTENSIONS_PDF,
)
from linpdf.config import Config
from linpdf.core.document import Document
from linpdf.core.renderer import Renderer
from linpdf.ui.ribbon.ribbon_bar import RibbonBar
from linpdf.ui.viewer.pdf_viewer import PDFViewer
from linpdf.ui.viewer.thumbnail_panel import ThumbnailWidget


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
        self._btn_encrypt.clicked.connect(self._show_coming_soon)
        self._btn_sign.clicked.connect(self._show_coming_soon)
        self._btn_redact.clicked.connect(self._show_coming_soon)
        self._btn_to_word.clicked.connect(self._show_coming_soon)
        self._btn_to_excel.clicked.connect(self._show_coming_soon)
        self._btn_to_ppt.clicked.connect(self._show_coming_soon)
        self._btn_to_image.clicked.connect(self._show_coming_soon)
        self._btn_ocr.clicked.connect(self._show_coming_soon)
        self._btn_blank_page.clicked.connect(self._show_coming_soon)
        self._btn_from_file.clicked.connect(self._show_coming_soon)
        self._btn_insert_image.clicked.connect(self._show_coming_soon)
        self._btn_link.clicked.connect(self._show_coming_soon)
        self._btn_stamp.clicked.connect(self._show_coming_soon)
        self._btn_rotate_cw.clicked.connect(self._show_coming_soon)
        self._btn_rotate_ccw.clicked.connect(self._show_coming_soon)
        self._btn_extract.clicked.connect(self._show_coming_soon)
        self._btn_highlight.clicked.connect(self._show_coming_soon)
        self._btn_underline.clicked.connect(self._show_coming_soon)
        self._btn_strikeout.clicked.connect(self._show_coming_soon)
        self._btn_note.clicked.connect(self._show_coming_soon)
        self._btn_fill_form.clicked.connect(self._show_coming_soon)
        self._btn_create_form.clicked.connect(self._show_coming_soon)
        self._btn_undo.clicked.connect(self._show_coming_soon)
        self._btn_redo.clicked.connect(self._show_coming_soon)

    def _set_tool(self, mode):
        self._current_tool = mode
        if mode == ToolMode.SELECT:
            self._viewer.setDragMode(self._viewer.RubberBandDrag)
            self._btn_select.setChecked(True)
            self._btn_pan.setChecked(False)
        elif mode == ToolMode.PAN:
            self._viewer.setDragMode(self._viewer.ScrollHandDrag)
            self._btn_select.setChecked(False)
            self._btn_pan.setChecked(True)

    def _create_viewer(self):
        self._viewer = PDFViewer()
        self._thumbnail_panel = ThumbnailWidget()

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
        edit_menu.addAction("&Undo", self._show_coming_soon, QKeySequence.Undo)
        edit_menu.addAction("&Redo", self._show_coming_soon, QKeySequence("Ctrl+Y"))

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
        except Exception as e:
            QMessageBox.critical(self, "Open Failed", f"Failed to open PDF:\n{e}")

    def save_file(self):
        if self._current_file and self._document.is_modified:
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

    def _delete_current_page(self):
        self._show_coming_soon()

    def _toggle_thumbnail_panel(self):
        visible = self._thumbnail_panel.isVisible()
        self._thumbnail_panel.setVisible(not visible)
        self._toggle_thumb_action.setChecked(not visible)

    def _on_document_loaded(self):
        self._renderer.clear_cache()
        self._viewer.set_document(self._document, self._renderer)
        self._thumbnail_panel.set_document(self._document, self._renderer)
        self._update_title()
        self._page_label.setText(f"Page 1 of {self._document.page_count}")

    def _on_document_closed(self):
        self._viewer.clear()
        self._thumbnail_panel.clear()
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
