from enum import Enum, auto


class ViewMode(Enum):
    SINGLE_PAGE = auto()
    CONTINUOUS = auto()
    FACING = auto()
    CONTINUOUS_FACING = auto()


class ZoomMode(Enum):
    FIT_WIDTH = auto()
    FIT_PAGE = auto()
    CUSTOM = auto()


class AnnotationType(Enum):
    HIGHLIGHT = "Highlight"
    UNDERLINE = "Underline"
    STRIKEOUT = "StrikeOut"
    SQUIGGLY = "Squiggly"
    TEXT = "Text"
    FREETEXT = "FreeText"
    STAMP = "Stamp"
    LINE = "Line"
    ARROW = "Arrow"
    RECTANGLE = "Square"
    ELLIPSE = "Circle"
    POLYGON = "Polygon"
    POLYLINE = "PolyLine"
    INK = "Ink"
    FILE_ATTACHMENT = "FileAttachment"
    CARET = "Caret"
    REDACTION = "Redaction"


class ToolMode(Enum):
    SELECT = auto()
    PAN = auto()
    TEXT_SELECT = auto()
    HIGHLIGHT = auto()
    UNDERLINE = auto()
    STRIKEOUT = auto()
    NOTE = auto()
    TEXT_BOX = auto()
    IMAGE = auto()
    LINE = auto()
    ARROW = auto()
    RECTANGLE = auto()
    ELLIPSE = auto()
    FREEHAND = auto()
    STAMP = auto()
    ERASER = auto()
    EDIT_TEXT = auto()
    CROP = auto()
    SIGNATURE = auto()


FILE_EXTENSIONS_PDF = ["pdf"]
FILE_EXTENSIONS_IMAGES = ["png", "jpg", "jpeg", "tiff", "tif", "bmp", "gif", "webp"]
FILE_EXTENSIONS_OFFICE = ["docx", "xlsx", "pptx"]

DEFAULT_ZOOM = 1.0
MIN_ZOOM = 0.1
MAX_ZOOM = 10.0
ZOOM_STEP = 0.1
ZOOM_PRESETS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]

APP_NAME = "LinPDF"
APP_VERSION = "0.1.0"
APP_ORG = "LinPDF"
