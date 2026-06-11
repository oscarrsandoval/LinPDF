from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QPushButton, QSlider, QSpinBox, QDoubleSpinBox,
    QLineEdit, QTextEdit, QComboBox, QDialogButtonBox,
    QColorDialog, QWidget,
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont

from linpdf.constants import AnnotationType


ANNOTATION_TYPE_NAMES = {
    AnnotationType.HIGHLIGHT: "Highlight",
    AnnotationType.UNDERLINE: "Underline",
    AnnotationType.STRIKEOUT: "Strikeout",
    AnnotationType.SQUIGGLY: "Squiggly",
    AnnotationType.TEXT: "Sticky Note",
    AnnotationType.FREETEXT: "Text Box",
    AnnotationType.STAMP: "Stamp",
    AnnotationType.LINE: "Line",
    AnnotationType.ARROW: "Arrow",
    AnnotationType.RECTANGLE: "Rectangle",
    AnnotationType.ELLIPSE: "Oval",
    AnnotationType.POLYGON: "Polygon",
    AnnotationType.POLYLINE: "Polyline",
    AnnotationType.INK: "Freehand Draw",
    AnnotationType.FILE_ATTACHMENT: "File Attachment",
    AnnotationType.CARET: "Caret",
    AnnotationType.REDACTION: "Redaction",
}


class ColorButton(QPushButton):
    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self._color = color or QColor(0, 0, 0)
        self.setFixedSize(32, 24)
        self.set_cursor_color(self._color)
        self.clicked.connect(self._pick_color)

    def set_cursor_color(self, color):
        self._color = color
        self.setStyleSheet(
            f"background-color: {color.name()}; "
            f"border: 1px solid palette(mid); "
            f"border-radius: 3px;"
        )

    def color(self):
        return self._color

    def _pick_color(self):
        c = QColorDialog.getColor(self._color, self, "Choose Color")
        if c.isValid():
            self.set_cursor_color(c)


class PropertiesDialog(QDialog):
    def __init__(self, annotation_item, parent=None):
        super().__init__(parent)
        self._item = annotation_item
        self._properties = dict(annotation_item.properties)
        self._annot_type = annotation_item.annot_type

        self.setWindowTitle(f"Properties - {ANNOTATION_TYPE_NAMES.get(self._annot_type, 'Annotation')}")
        self.setMinimumWidth(380)
        self._setup_ui()
        self._load_properties()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self._type_label = QLabel(
            f"<b>Type:</b> {ANNOTATION_TYPE_NAMES.get(self._annot_type, 'Unknown')}"
        )
        layout.addWidget(self._type_label)

        if self._has_stroke():
            self._add_color_group(layout)
        if self._has_fill():
            self._add_fill_group(layout)
        if self._has_line_width():
            self._add_line_group(layout)

        self._add_text_group(layout)
        self._add_author_group(layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _has_stroke(self):
        return self._annot_type not in (
            AnnotationType.HIGHLIGHT, AnnotationType.UNDERLINE,
            AnnotationType.STRIKEOUT, AnnotationType.SQUIGGLY,
            AnnotationType.REDACTION,
        )

    def _has_fill(self):
        return self._annot_type in (
            AnnotationType.RECTANGLE, AnnotationType.ELLIPSE,
            AnnotationType.POLYGON, AnnotationType.FREETEXT,
            AnnotationType.STAMP,
        )

    def _has_line_width(self):
        return self._annot_type not in (
            AnnotationType.HIGHLIGHT, AnnotationType.UNDERLINE,
            AnnotationType.STRIKEOUT, AnnotationType.SQUIGGLY,
            AnnotationType.TEXT, AnnotationType.FILE_ATTACHMENT,
            AnnotationType.CARET, AnnotationType.REDACTION,
        )

    def _add_color_group(self, layout):
        group = QGroupBox("Stroke")
        gl = QFormLayout(group)
        self._stroke_color_btn = ColorButton()
        gl.addRow("Color:", self._stroke_color_btn)

        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(100)
        self._opacity_label = QLabel("100%")
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v}%")
        )
        hl = QHBoxLayout()
        hl.addWidget(self._opacity_slider)
        hl.addWidget(self._opacity_label)
        gl.addRow("Opacity:", hl)
        layout.addWidget(group)

    def _add_fill_group(self, layout):
        group = QGroupBox("Fill")
        gl = QFormLayout(group)
        self._fill_color_btn = ColorButton()
        gl.addRow("Color:", self._fill_color_btn)
        layout.addWidget(group)

    def _add_line_group(self, layout):
        group = QGroupBox("Line")
        gl = QFormLayout(group)
        self._line_width_spin = QDoubleSpinBox()
        self._line_width_spin.setRange(0.5, 50.0)
        self._line_width_spin.setSingleStep(0.5)
        self._line_width_spin.setValue(1.0)
        gl.addRow("Width:", self._line_width_spin)

        if self._annot_type in (AnnotationType.LINE, AnnotationType.ARROW):
            self._line_style_combo = QComboBox()
            self._line_style_combo.addItems(["Solid", "Dashed", "Dotted"])
            gl.addRow("Style:", self._line_style_combo)
        layout.addWidget(group)

    def _add_text_group(self, layout):
        if self._annot_type in (AnnotationType.TEXT, AnnotationType.FREETEXT,
                                AnnotationType.STAMP, AnnotationType.FILE_ATTACHMENT,
                                AnnotationType.REDACTION):
            group = QGroupBox("Text")
            gl = QFormLayout(group)
            self._text_edit = QTextEdit()
            self._text_edit.setMaximumHeight(100)
            gl.addRow("Content:", self._text_edit)

            if self._annot_type == AnnotationType.FREETEXT:
                self._font_combo = QComboBox()
                self._font_combo.addItems(["Helv", "Courier", "Times", "Symbol", "ZapfDingbats"])
                gl.addRow("Font:", self._font_combo)

                self._font_size_spin = QSpinBox()
                self._font_size_spin.setRange(4, 144)
                self._font_size_spin.setValue(12)
                gl.addRow("Size:", self._font_size_spin)
            layout.addWidget(group)

    def _add_author_group(self, layout):
        group = QGroupBox("Author")
        gl = QFormLayout(group)
        self._author_edit = QLineEdit()
        gl.addRow("Author:", self._author_edit)
        self._subject_edit = QLineEdit()
        gl.addRow("Subject:", self._subject_edit)
        layout.addWidget(group)

    def _load_properties(self):
        p = self._properties

        if hasattr(self, '_stroke_color_btn'):
            sc = p.get('stroke_color')
            if sc and len(sc) == 3:
                self._stroke_color_btn.set_cursor_color(QColor(*sc))

        if hasattr(self, '_fill_color_btn'):
            fc = p.get('fill_color')
            if fc and len(fc) == 3:
                self._fill_color_btn.set_cursor_color(QColor(*fc))

        if hasattr(self, '_opacity_slider'):
            opacity = p.get('opacity', 1.0)
            self._opacity_slider.setValue(int(opacity * 100))

        if hasattr(self, '_line_width_spin'):
            self._line_width_spin.setValue(p.get('line_width', 1.0))

        if hasattr(self, '_text_edit'):
            self._text_edit.setText(p.get('text', p.get('content', p.get('subject', ''))))

        if hasattr(self, '_font_combo'):
            font_name = p.get('font_name', 'Helv')
            idx = self._font_combo.findText(font_name)
            if idx >= 0:
                self._font_combo.setCurrentIndex(idx)

        if hasattr(self, '_font_size_spin'):
            self._font_size_spin.setValue(p.get('font_size', 12))

        if hasattr(self, '_author_edit'):
            self._author_edit.setText(p.get('author', ''))

        if hasattr(self, '_subject_edit'):
            self._subject_edit.setText(p.get('subject', ''))

    def get_properties(self):
        result = {}

        if hasattr(self, '_stroke_color_btn'):
            c = self._stroke_color_btn.color()
            result['stroke_color'] = (c.red(), c.green(), c.blue())

        if hasattr(self, '_fill_color_btn'):
            c = self._fill_color_btn.color()
            result['fill_color'] = (c.red(), c.green(), c.blue())

        if hasattr(self, '_opacity_slider'):
            result['opacity'] = self._opacity_slider.value() / 100.0

        if hasattr(self, '_line_width_spin'):
            result['line_width'] = self._line_width_spin.value()

        if hasattr(self, '_text_edit'):
            text = self._text_edit.toPlainText()
            result['text'] = text
            result['content'] = text

        if hasattr(self, '_font_combo'):
            result['font_name'] = self._font_combo.currentText()

        if hasattr(self, '_font_size_spin'):
            result['font_size'] = self._font_size_spin.value()

        if hasattr(self, '_author_edit'):
            result['author'] = self._author_edit.text()

        if hasattr(self, '_subject_edit'):
            result['subject'] = self._subject_edit.text()

        return result
