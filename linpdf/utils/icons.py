import os
from PySide6.QtGui import QIcon


_ICON_CACHE = {}
_ICON_DIR = os.path.join(os.path.dirname(__file__), "..", "resources", "icons")


def load_icon(name):
    if name in _ICON_CACHE:
        return _ICON_CACHE[name]

    path = os.path.join(_ICON_DIR, f"{name}.svg")
    if not os.path.exists(path):
        icon = QIcon()
    else:
        icon = QIcon(path)

    _ICON_CACHE[name] = icon
    return icon


def icon_path(name):
    path = os.path.join(_ICON_DIR, f"{name}.svg")
    if os.path.exists(path):
        return path
    return ""
