from linpdf.constants import AnnotationType
from linpdf.annotations.annotation_manager import AnnotationManager
from linpdf.annotations.annotation_item import AnnotationItem
from linpdf.annotations.properties_dialog import PropertiesDialog

ANNOTATION_TYPES = {
    AnnotationType.HIGHLIGHT: "Highlight Text",
    AnnotationType.UNDERLINE: "Underline Text",
    AnnotationType.STRIKEOUT: "Strikeout Text",
    AnnotationType.SQUIGGLY: "Squiggly Underline",
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

__all__ = [
    "AnnotationManager",
    "AnnotationItem",
    "PropertiesDialog",
    "AnnotationType",
    "ANNOTATION_TYPES",
]
