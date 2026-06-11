import copy
from collections import defaultdict
from datetime import datetime

import fitz
from PySide6.QtCore import QObject, Signal, QRectF

from linpdf.constants import AnnotationType
from linpdf.annotations.annotation_item import AnnotationItem


class AnnotationCommand:
    def __init__(self, manager, annotation_data):
        self._manager = manager
        self._annotation_data = annotation_data

    def do(self):
        raise NotImplementedError

    def undo(self):
        raise NotImplementedError


class AddAnnotationCommand(AnnotationCommand):
    def __init__(self, manager, annotation_data, zoom):
        super().__init__(manager, annotation_data)
        self._zoom = zoom
        self._page_index = annotation_data['page_index']
        self._item = None

    def do(self):
        data = self._annotation_data
        page = self._manager._get_fitz_page(self._page_index)
        if page is None:
            return None
        fitz_annot = self._create_fitz_annotation(page, data)
        if fitz_annot:
            data['_fitz_annot'] = fitz_annot
            data['_fitz_page_num'] = self._page_index
        self._item = self._manager._create_item(data, self._zoom)
        if self._item:
            self._manager._items_by_page[self._page_index].append(self._item)
            self._manager._scene.addItem(self._item)
        self._manager._on_modified()
        return self._item

    def undo(self):
        if self._item and self._item.scene():
            self._manager._scene.removeItem(self._item)
        items = self._manager._items_by_page.get(self._page_index, [])
        if self._item in items:
            items.remove(self._item)
        fitz_annot = self._annotation_data.get('_fitz_annot')
        if fitz_annot:
            try:
                page = self._manager._get_fitz_page(self._page_index)
                if page:
                    page.delete_annot(fitz_annot)
            except Exception:
                pass
        self._manager._on_modified()

    def _create_fitz_annotation(self, page, data):
        annot_type = data['type']
        rect = data.get('rect')
        if not rect:
            return None

        fitz_rect = fitz.Rect(rect[0], rect[1], rect[2], rect[3])

        if annot_type in (AnnotationType.HIGHLIGHT, AnnotationType.UNDERLINE,
                          AnnotationType.STRIKEOUT, AnnotationType.SQUIGGLY):
            quads = data.get('quads')
            if quads:
                fitz_quads = [fitz.Quad(q) for q in quads]
            else:
                fitz_quads = [fitz.Quad(fitz_rect)]
            method_map = {
                AnnotationType.HIGHLIGHT: page.add_highlight_annot,
                AnnotationType.UNDERLINE: page.add_underline_annot,
                AnnotationType.STRIKEOUT: page.add_strikeout_annot,
                AnnotationType.SQUIGGLY: page.add_squiggly_annot,
            }
            method = method_map[annot_type]
            annot = method(fitz_quads)

        elif annot_type == AnnotationType.TEXT:
            point = fitz_rect.tl
            icon = data.get('icon', 'Note')
            annot = page.add_text_annot(point, icon=icon)
            if data.get('content'):
                annot.set_info(content=data['content'])
            if data.get('author'):
                annot.set_info(title=data['author'])

        elif annot_type == AnnotationType.FREETEXT:
            font_size = data.get('font_size', 12)
            font_name = data.get('font_name', 'Helv')
            text = data.get('text', '')
            annot = page.add_freetext_annot(fitz_rect, text=text)
            annot.update(fontname=font_name, fontsize=font_size)

        elif annot_type == AnnotationType.STAMP:
            stamp_id = data.get('icon', 0)
            if isinstance(stamp_id, str):
                stamp_id = 0
            annot = page.add_stamp_annot(fitz_rect, stamp_id=stamp_id)
            if data.get('text'):
                annot.set_info(content=data['text'])

        elif annot_type in (AnnotationType.LINE, AnnotationType.ARROW):
            p1 = fitz_rect.tl
            p2 = fitz_rect.br
            annot = page.add_line_annot(p1, p2)
            if annot_type == AnnotationType.ARROW:
                annot.set_line_ends(fitz.PDF_ANNOT_LE_OPEN_ARROW, fitz.PDF_ANNOT_LE_NONE)

        elif annot_type == AnnotationType.RECTANGLE:
            annot = page.add_rect_annot(fitz_rect)

        elif annot_type == AnnotationType.ELLIPSE:
            annot = page.add_circle_annot(fitz_rect)

        elif annot_type in (AnnotationType.POLYGON, AnnotationType.POLYLINE):
            pts = data.get('points', [])
            if not pts:
                pts = self._rect_to_points(rect)
            fitz_pts = [(p[0], p[1]) for p in pts]
            method = page.add_polygon_annot if annot_type == AnnotationType.POLYGON else page.add_polyline_annot
            annot = method(fitz_pts)

        elif annot_type == AnnotationType.INK:
            strokes = data.get('points', [[(rect[0], rect[1]), (rect[2], rect[3])]])
            annot = page.add_ink_annot(strokes)

        elif annot_type == AnnotationType.FILE_ATTACHMENT:
            point = fitz_rect.tl
            annot = page.add_file_annot(point)

        elif annot_type == AnnotationType.CARET:
            annot = page.add_caret_annot(fitz_rect)

        elif annot_type == AnnotationType.REDACTION:
            annot = page.add_redact_annot(fitz_rect)
            if data.get('text'):
                annot.set_info(content=data['text'])

        else:
            return None

        self._apply_annot_properties(annot, data)
        return annot

    def _apply_annot_properties(self, annot, data):
        stroke = data.get('stroke_color')
        if stroke and len(stroke) == 3:
            annot.set_colors(stroke=[s / 255.0 for s in stroke])
        fill = data.get('fill_color')
        if fill and len(fill) == 3:
            annot.set_colors(fill=[f / 255.0 for f in fill])
        opacity = data.get('opacity')
        if opacity is not None:
            annot.set_opacity(opacity)
        line_width = data.get('line_width')
        if line_width is not None:
            annot.set_border(width=line_width)
        author = data.get('author')
        subject = data.get('subject')
        content = data.get('content')
        info = {}
        if author:
            info['title'] = author
        if subject:
            info['subject'] = subject
        if content:
            info['content'] = content
        if info:
            annot.set_info(**info)
        annot.update()

    def _rect_to_points(self, rect):
        return [
            (rect[0], rect[1]),
            (rect[2], rect[1]),
            (rect[2], rect[3]),
            (rect[0], rect[3]),
        ]

    def item(self):
        return self._item


class DeleteAnnotationCommand(AnnotationCommand):
    def __init__(self, manager, annotation_item, annotation_data, zoom):
        super().__init__(manager, annotation_data)
        self._item = annotation_item
        self._zoom = zoom
        self._page_index = annotation_data['page_index']

    def do(self):
        if self._item and self._item.scene():
            self._manager._scene.removeItem(self._item)
        items = self._manager._items_by_page.get(self._page_index, [])
        if self._item in items:
            items.remove(self._item)
        fitz_annot = self._annotation_data.get('_fitz_annot')
        if fitz_annot:
            try:
                page = self._manager._get_fitz_page(self._page_index)
                if page:
                    page.delete_annot(fitz_annot)
            except Exception:
                pass
        self._manager._on_modified()

    def undo(self):
        new_item = self._manager._create_item(self._annotation_data, self._zoom)
        if new_item:
            self._manager._items_by_page[self._page_index].append(new_item)
            self._manager._scene.addItem(new_item)
            self._item = new_item
        fitz_annot = self._annotation_data.get('_fitz_annot')
        if fitz_annot is None:
            page = self._manager._get_fitz_page(self._page_index)
            if page:
                data = self._annotation_data
                cmd = AddAnnotationCommand(self._manager, data, self._zoom)
                cmd.do()
                self._annotation_data['_fitz_annot'] = data.get('_fitz_annot')
        self._manager._on_modified()

    def item(self):
        return self._item


class ModifyAnnotationCommand(AnnotationCommand):
    def __init__(self, manager, annotation_item, old_data, new_data, zoom):
        super().__init__(manager, new_data)
        self._item = annotation_item
        self._old_data = copy.deepcopy(old_data)
        self._new_data = copy.deepcopy(new_data)
        self._zoom = zoom

    def do(self):
        self._item.properties = self._new_data.copy()
        self._apply_to_item(self._new_data)
        self._update_fitz(self._new_data)

    def undo(self):
        self._item.properties = self._old_data.copy()
        self._apply_to_item(self._old_data)
        self._update_fitz(self._old_data)

    def _apply_to_item(self, data):
        rect = data.get('rect')
        if rect:
            self._item.set_rect(QRectF(rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]))
        self._item.update()

    def _update_fitz(self, data):
        fitz_annot = data.get('_fitz_annot')
        if fitz_annot:
            try:
                AddAnnotationCommand(self._manager, data, self._zoom)._apply_annot_properties(fitz_annot, data)
                rect = data.get('rect')
                if rect:
                    fitz_annot.set_rect(fitz.Rect(rect[0], rect[1], rect[2], rect[3]))
                fitz_annot.update()
            except Exception:
                pass

    def item(self):
        return self._item


class AnnotationManager(QObject):
    annotation_added = Signal(object)
    annotation_removed = Signal(object)
    annotation_modified = Signal(object)
    annotation_selected = Signal(object)
    undo_stack_changed = Signal()

    def __init__(self, document, scene, parent=None):
        super().__init__(parent)
        self._document = document
        self._scene = scene
        self._items_by_page = defaultdict(list)
        self._undo_stack = []
        self._redo_stack = []
        self._max_undo = 50
        self._selected_item = None
        self._current_zoom = 1.0
        self._default_author = 'LinPDF User'

    @property
    def document(self):
        return self._document

    @property
    def scene(self):
        return self._scene

    @property
    def selected_item(self):
        return self._selected_item

    @selected_item.setter
    def selected_item(self, item):
        self._selected_item = item
        self.annotation_selected.emit(item)

    @property
    def current_zoom(self):
        return self._current_zoom

    @current_zoom.setter
    def current_zoom(self, zoom):
        self._current_zoom = zoom

    def set_default_author(self, author):
        self._default_author = author

    def _get_fitz_page(self, page_index):
        if not self._document or not self._document.is_loaded:
            return None
        try:
            return self._document._doc[page_index]
        except (IndexError, AttributeError):
            return None

    def _create_item(self, data, zoom):
        annot_type = data['type']
        rect = data.get('rect')
        if not rect:
            return None
        qrect = QRectF(rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
        props = data.copy()
        props.pop('type', None)
        props.pop('page_index', None)
        props.pop('_fitz_annot', None)
        props.pop('_fitz_page_num', None)
        return AnnotationItem(annot_type, qrect, props, zoom)

    def _build_data_from_item(self, item, page_index):
        r = item.rect_pdf()
        return {
            'type': item.annot_type,
            'page_index': page_index,
            'rect': (r.x(), r.y(), r.x() + r.width(), r.y() + r.height()),
            'stroke_color': item.properties.get('stroke_color', (0, 0, 0)),
            'fill_color': item.properties.get('fill_color'),
            'opacity': item.properties.get('opacity', 1.0),
            'line_width': item.properties.get('line_width', 1.0),
            'text': item.properties.get('text', ''),
            'author': item.properties.get('author', ''),
            'subject': item.properties.get('subject', ''),
            'content': item.properties.get('content', ''),
            'font_size': item.properties.get('font_size', 12),
            'font_name': item.properties.get('font_name', 'Helv'),
            'icon': item.properties.get('icon'),
            'points': item.properties.get('points'),
            'quads': item.properties.get('quads'),
        }

    def _on_modified(self):
        if self._document:
            self._document.mark_modified()

    def _push_undo(self, command):
        self._undo_stack.append(command)
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self.undo_stack_changed.emit()

    def create_annotation(self, annot_type, page_index, rect, zoom=None, **kwargs):
        if zoom is None:
            zoom = self._current_zoom

        rect_pdf = (
            rect.x() / zoom if hasattr(rect, 'x') else rect[0],
            rect.y() / zoom if hasattr(rect, 'y') else rect[1],
            (rect.x() + rect.width()) / zoom if hasattr(rect, 'x') else rect[2],
            (rect.y() + rect.height()) / zoom if hasattr(rect, 'y') else rect[3],
        ) if hasattr(rect, 'x') else (
            rect[0] / zoom,
            rect[1] / zoom,
            rect[2] / zoom,
            rect[3] / zoom,
        )

        now = datetime.now().isoformat()
        data = {
            'type': annot_type,
            'page_index': page_index,
            'rect': rect_pdf,
            'stroke_color': kwargs.get('stroke_color', (0, 0, 0)),
            'fill_color': kwargs.get('fill_color'),
            'opacity': kwargs.get('opacity', 1.0),
            'line_width': kwargs.get('line_width', 1.0),
            'text': kwargs.get('text', ''),
            'author': kwargs.get('author', self._default_author),
            'subject': kwargs.get('subject', ''),
            'content': kwargs.get('content', ''),
            'font_size': kwargs.get('font_size', 12),
            'font_name': kwargs.get('font_name', 'Helv'),
            'icon': kwargs.get('icon'),
            'points': kwargs.get('points'),
            'quads': kwargs.get('quads'),
            'date': now,
        }

        cmd = AddAnnotationCommand(self, data, zoom)
        cmd.do()
        self._push_undo(cmd)
        item = cmd.item()
        if item:
            self.annotation_added.emit(item)
        return item

    def delete_annotation(self, item):
        for page_index, items in self._items_by_page.items():
            if item in items:
                data = self._build_data_from_item(item, page_index)
                cmd = DeleteAnnotationCommand(self, item, data, self._current_zoom)
                cmd.do()
                self._push_undo(cmd)
                self.annotation_removed.emit(item)
                if self._selected_item == item:
                    self._selected_item = None
                return True
        return False

    def modify_annotation(self, item, new_properties):
        for page_index, items in self._items_by_page.items():
            if item in items:
                old_data = self._build_data_from_item(item, page_index)
                new_data = copy.deepcopy(old_data)
                for k, v in new_properties.items():
                    if k == 'rect':
                        r = v
                        new_data['rect'] = (r.x(), r.y(), r.x() + r.width(), r.y() + r.height())
                    elif k in new_data:
                        new_data[k] = v
                cmd = ModifyAnnotationCommand(self, item, old_data, new_data, self._current_zoom)
                cmd.do()
                self._push_undo(cmd)
                self.annotation_modified.emit(item)
                return True
        return False

    def undo(self):
        if not self._undo_stack:
            return False
        cmd = self._undo_stack.pop()
        cmd.undo()
        self._redo_stack.append(cmd)
        self.undo_stack_changed.emit()
        return True

    def redo(self):
        if not self._redo_stack:
            return False
        cmd = self._redo_stack.pop()
        cmd.do()
        self._undo_stack.append(cmd)
        self.undo_stack_changed.emit()
        return True

    def can_undo(self):
        return len(self._undo_stack) > 0

    def can_redo(self):
        return len(self._redo_stack) > 0

    def clear_undo_redo(self):
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.undo_stack_changed.emit()

    def get_annotations_for_page(self, page_index):
        return list(self._items_by_page.get(page_index, []))

    def get_all_annotations(self):
        result = []
        for items in self._items_by_page.values():
            result.extend(items)
        return result

    def clear_page(self, page_index, remove_from_fitz=False):
        items = self._items_by_page.get(page_index, [])
        for item in items:
            if item.scene():
                self._scene.removeItem(item)
        if remove_from_fitz:
            page = self._get_fitz_page(page_index)
            if page:
                annots = list(page.annots())
                for a in annots:
                    page.delete_annot(a)
        self._items_by_page[page_index] = []
        self._on_modified()

    def clear_all(self, remove_from_fitz=False):
        for page_index in list(self._items_by_page.keys()):
            self.clear_page(page_index, remove_from_fitz)
        self.clear_undo_redo()
        self._selected_item = None

    def load_annotations_from_page(self, page_index, zoom=None):
        if zoom is None:
            zoom = self._current_zoom
        self.clear_page(page_index)
        page = self._get_fitz_page(page_index)
        if page is None:
            return []
        items = []
        for fitz_annot in page.annots():
            data = self._fitz_annot_to_data(fitz_annot, page_index)
            if data is None:
                continue
            data['_fitz_annot'] = fitz_annot
            data['_fitz_page_num'] = page_index
            item = self._create_item(data, zoom)
            if item:
                self._items_by_page[page_index].append(item)
                self._scene.addItem(item)
                items.append(item)
        return items

    def load_all_annotations(self, zoom=None):
        if zoom is None:
            zoom = self._current_zoom
        self.clear_all()
        if not self._document or not self._document.is_loaded:
            return
        for i in range(self._document.page_count):
            self.load_annotations_from_page(i, zoom)

    def _fitz_annot_to_data(self, annot, page_index):
        annot_type_str = annot.type
        type_map = {
            'Highlight': AnnotationType.HIGHLIGHT,
            'Underline': AnnotationType.UNDERLINE,
            'StrikeOut': AnnotationType.STRIKEOUT,
            'Squiggly': AnnotationType.SQUIGGLY,
            'Text': AnnotationType.TEXT,
            'FreeText': AnnotationType.FREETEXT,
            'Stamp': AnnotationType.STAMP,
            'Line': AnnotationType.LINE,
            'Square': AnnotationType.RECTANGLE,
            'Circle': AnnotationType.ELLIPSE,
            'Polygon': AnnotationType.POLYGON,
            'PolyLine': AnnotationType.POLYLINE,
            'Ink': AnnotationType.INK,
            'FileAttachment': AnnotationType.FILE_ATTACHMENT,
            'Caret': AnnotationType.CARET,
            'Redact': AnnotationType.REDACTION,
        }
        atype = type_map.get(annot_type_str)
        if atype is None:
            return None

        rect = annot.rect
        if rect is None:
            return None

        stroke_colors = annot.colors.get('stroke')
        fill_colors = annot.colors.get('fill')
        stroke_color = (
            tuple(int(c * 255) for c in stroke_colors)
            if stroke_colors and len(stroke_colors) >= 3
            else (0, 0, 0)
        )
        fill_color = (
            tuple(int(c * 255) for c in fill_colors)
            if fill_colors and len(fill_colors) >= 3
            else None
        )

        info = annot.info or {}
        border = annot.border or {}
        line_width = border.get('width', 1.0) if isinstance(border, dict) else 1.0

        data = {
            'type': atype,
            'page_index': page_index,
            'rect': (rect.x0, rect.y0, rect.x1, rect.y1),
            'stroke_color': stroke_color,
            'fill_color': fill_color,
            'opacity': annot.opacity if annot.opacity is not None else 1.0,
            'line_width': line_width,
            'text': annot.info.get('content', '') if hasattr(annot, 'info') else '',
            'author': info.get('title', ''),
            'subject': info.get('subject', ''),
            'content': info.get('content', ''),
            'font_size': 12,
            'font_name': 'Helv',
            'icon': None,
            'points': None,
            'quads': None,
        }

        if atype in (AnnotationType.LINE, AnnotationType.ARROW):
            line_ends = annot.line_ends
            if line_ends and (line_ends[0] != fitz.PDF_ANNOT_LE_NONE or line_ends[1] != fitz.PDF_ANNOT_LE_NONE):
                data['type'] = AnnotationType.ARROW

        if atype in (AnnotationType.POLYGON, AnnotationType.POLYLINE):
            verts = annot.vertices
            if verts:
                pts = [(v.x, v.y) for v in verts]
                data['points'] = pts

        if atype == AnnotationType.INK:
            ink_list = annot.strokes
            if ink_list:
                data['points'] = [[(p.x, p.y) for p in stroke] for stroke in ink_list]

        if atype in self._text_markup_types():
            quads_obj = annot.quads
            if quads_obj:
                data['quads'] = [[(q.ll.x, q.ll.y), (q.lr.x, q.lr.y),
                                  (q.ul.x, q.ul.y), (q.ur.x, q.ur.y)] for q in quads_obj]

        if atype == AnnotationType.STAMP:
            data['icon'] = str(annot.stamp)

        if atype == AnnotationType.TEXT:
            data['icon'] = annot.icon

        if atype == AnnotationType.FREETEXT:
            data['text'] = annot.info.get('content', '') if hasattr(annot, 'info') else ''

        return data

    def _text_markup_types(self):
        return {AnnotationType.HIGHLIGHT, AnnotationType.UNDERLINE,
                AnnotationType.STRIKEOUT, AnnotationType.SQUIGGLY}

    def rebuild_page_annotations(self, page_index, zoom=None):
        if zoom is None:
            zoom = self._current_zoom
        items = self._items_by_page.get(page_index, [])
        for item in items:
            if item.scene():
                self._scene.removeItem(item)
        self._items_by_page[page_index] = []
        return self.load_annotations_from_page(page_index, zoom)

    def rebuild_all(self, zoom=None):
        if zoom is None:
            zoom = self._current_zoom
        self._current_zoom = zoom
        for page_index in list(self._items_by_page.keys()):
            for item in self._items_by_page[page_index]:
                if item.scene():
                    self._scene.removeItem(item)
        self._items_by_page.clear()
        self.load_all_annotations(zoom)
