from PySide6.QtGui import QPixmap
from PySide6.QtCore import QSize


class Renderer:
    def __init__(self, max_cache_size=50):
        self._cache = {}
        self._max_cache_size = max_cache_size

    def render_page(self, page, zoom=1.0):
        cache_key = (page.index, round(zoom, 2))
        if cache_key in self._cache:
            return self._cache[cache_key]

        pixmap = page.render(zoom)

        if len(self._cache) >= self._max_cache_size:
            oldest = next(iter(self._cache))
            del self._cache[oldest]

        self._cache[cache_key] = pixmap
        return pixmap

    def render_thumbnail(self, page, max_width=200):
        page_width = page.width
        zoom = max_width / page_width if page_width > 0 else 0.1
        cache_key = ("thumb", page.index, max_width)
        if cache_key in self._cache:
            return self._cache[cache_key]

        pixmap = page.render(zoom)

        if len(self._cache) >= self._max_cache_size:
            oldest = next(iter(self._cache))
            del self._cache[oldest]

        self._cache[cache_key] = pixmap
        return pixmap

    def clear_cache(self):
        self._cache.clear()

    def invalidate_page(self, page_index):
        keys_to_delete = [
            k for k in self._cache if (isinstance(k, tuple) and k[0] == "thumb" and k[1] == page_index) or
            (isinstance(k, tuple) and k[0] == page_index)
        ]
        for key in keys_to_delete:
            del self._cache[key]

    def set_cache_size(self, size):
        self._max_cache_size = size
        while len(self._cache) > size:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
