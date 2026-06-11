from PySide6.QtCore import QSettings


class Config:
    def __init__(self):
        self._settings = QSettings("LinPDF", "LinPDF")

    def get(self, key, default=None):
        return self._settings.value(key, default)

    def set(self, key, value):
        self._settings.setValue(key, value)

    @property
    def last_directory(self):
        return self.get("last_directory", "")

    @last_directory.setter
    def last_directory(self, path):
        self.set("last_directory", path)

    @property
    def recent_files(self):
        raw = self.get("recent_files", [])
        if raw is None:
            return []
        if isinstance(raw, str):
            return [raw]
        return list(raw)

    @recent_files.setter
    def recent_files(self, files):
        self.set("recent_files", files[:10])

    @property
    def window_geometry(self):
        return self.get("window_geometry")

    @window_geometry.setter
    def window_geometry(self, geometry):
        self.set("window_geometry", geometry)

    @property
    def window_state(self):
        return self.get("window_state")

    @window_state.setter
    def window_state(self, state):
        self.set("window_state", state)

    @property
    def show_thumbnail_panel(self):
        val = self.get("show_thumbnail_panel", "true")
        return str(val).lower() == "true"

    @show_thumbnail_panel.setter
    def show_thumbnail_panel(self, show):
        self.set("show_thumbnail_panel", "true" if show else "false")

    @property
    def default_zoom(self):
        return float(self.get("default_zoom", 1.0))

    @default_zoom.setter
    def default_zoom(self, zoom):
        self.set("default_zoom", zoom)

    def add_recent_file(self, path):
        files = self.recent_files
        if path in files:
            files.remove(path)
        files.insert(0, path)
        self.recent_files = files
