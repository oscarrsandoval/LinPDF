import fitz
import os


def add_text_watermark(document, text, opacity=0.3, angle=45, font_size=60,
                       color=(0.5, 0.5, 0.5), layer="watermark"):
    doc = document._doc
    if not doc:
        return False
    try:
        for i in range(len(doc)):
            page = doc[i]
            rect = page.rect
            tw, th = fitz.get_text_length(text, fontsize=font_size), font_size
            cx, cy = rect.width / 2, rect.height / 2
            annot = page.add_freetext_annot(
                fitz.Rect(cx - tw / 2, cy - th / 2, cx + tw / 2, cy + th / 2),
                text,
                fontsize=font_size,
                fontname="helv",
                text_color=color,
                fill_color=None,
                border_width=0,
            )
            annot.set_opacity(opacity)
            annot.update()
        document.mark_modified()
        return True
    except Exception:
        return False


def add_image_watermark(document, image_path, opacity=0.3, scale=1.0, layer="watermark"):
    doc = document._doc
    if not doc or not os.path.isfile(image_path):
        return False
    try:
        for i in range(len(doc)):
            page = doc[i]
            rect = page.rect
            iw = rect.width * scale
            ih = iw
            cx, cy = rect.width / 2, rect.height / 2
            ir = fitz.Rect(cx - iw / 2, cy - ih / 2, cx + iw / 2, cy + ih / 2)
            page.insert_image(ir, filename=image_path, overlay=True, keep_proportion=True)
        document.mark_modified()
        return True
    except Exception:
        return False


def add_page_numbers(document, start=1, position="bottom_center",
                     font_size=12, color=(0, 0, 0)):
    doc = document._doc
    if not doc:
        return False
    try:
        for i in range(len(doc)):
            page = doc[i]
            rect = page.rect
            num = start + i
            text = str(num)
            tw = fitz.get_text_length(text, fontsize=font_size)
            margin = 40
            if position == "bottom_center":
                x = (rect.width - tw) / 2
                y = rect.height - margin
            elif position == "bottom_left":
                x = margin
                y = rect.height - margin
            elif position == "bottom_right":
                x = rect.width - tw - margin
                y = rect.height - margin
            elif position == "top_center":
                x = (rect.width - tw) / 2
                y = margin + font_size
            elif position == "top_left":
                x = margin
                y = margin + font_size
            elif position == "top_right":
                x = rect.width - tw - margin
                y = margin + font_size
            else:
                x = (rect.width - tw) / 2
                y = rect.height - margin
            p = fitz.Point(x, y)
            page.insert_text(p, text, fontsize=font_size, fontname="helv", color=color)
        document.mark_modified()
        return True
    except Exception:
        return False


def add_header(document, text, font_size=12, color=(0.3, 0.3, 0.3)):
    return _add_header_footer(document, text, font_size, color, header=True)


def add_footer(document, text, font_size=12, color=(0.3, 0.3, 0.3)):
    return _add_header_footer(document, text, font_size, color, header=False)


def _add_header_footer(document, text, font_size, color, header):
    doc = document._doc
    if not doc:
        return False
    try:
        for i in range(len(doc)):
            page = doc[i]
            rect = page.rect
            margin = 36
            tw = fitz.get_text_length(text, fontsize=font_size)
            x = (rect.width - tw) / 2
            if header:
                y = margin + font_size
            else:
                y = rect.height - margin
            p = fitz.Point(x, y)
            page.insert_text(p, text, fontsize=font_size, fontname="helv", color=color)
        document.mark_modified()
        return True
    except Exception:
        return False


def add_background(document, color=(1, 1, 1)):
    doc = document._doc
    if not doc:
        return False
    try:
        for i in range(len(doc)):
            page = doc[i]
            rect = page.rect
            page.draw_rect(rect, color=color, fill=color, width=0, overlay=False)
        document.mark_modified()
        return True
    except Exception:
        return False
