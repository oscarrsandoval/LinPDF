import fitz
import xml.etree.ElementTree as ET


class FormManager:
    WIDGET_TYPE_NAMES = {
        fitz.PDF_WIDGET_TYPE_TEXT: "text",
        fitz.PDF_WIDGET_TYPE_CHECKBOX: "checkbox",
        fitz.PDF_WIDGET_TYPE_RADIOBUTTON: "radio",
        fitz.PDF_WIDGET_TYPE_COMBOBOX: "combobox",
        fitz.PDF_WIDGET_TYPE_LISTBOX: "listbox",
        fitz.PDF_WIDGET_TYPE_BUTTON: "button",
        fitz.PDF_WIDGET_TYPE_SIGNATURE: "signature",
    }

    def get_form_fields(self, doc):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", []

            fields = []
            for page_num in range(doc.page_count):
                page = doc._doc[page_num]
                for widget in page.widgets():
                    field_type = widget.field_type
                    fields.append({
                        "name": widget.field_name,
                        "type": self.WIDGET_TYPE_NAMES.get(
                            field_type, f"unknown({field_type})"
                        ),
                        "type_id": field_type,
                        "value": widget.field_value,
                        "rect": (
                            widget.rect.x0,
                            widget.rect.y0,
                            widget.rect.x1,
                            widget.rect.y1,
                        ),
                        "page": page_num,
                        "flags": widget.field_flags,
                        "label": widget.field_label,
                    })

            return True, f"Found {len(fields)} form field(s)", {
                "fields": fields,
            }
        except Exception as e:
            return False, str(e), []

    def set_field_value(self, doc, field_name, value):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}

            found = False
            for page_num in range(doc.page_count):
                page = doc._doc[page_num]
                for widget in page.widgets():
                    if widget.field_name == field_name:
                        if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                            widget.field_value = "Yes" if value else "Off"
                        else:
                            widget.field_value = value
                        widget.update()
                        found = True
                        break
                if found:
                    break

            if not found:
                return False, f"Field '{field_name}' not found", {}

            doc._modified = True

            return True, f"Field '{field_name}' set", {
                "field_name": field_name,
                "value": value,
            }
        except Exception as e:
            return False, str(e), {}

    def fill_form(self, doc, data_dict):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}

            filled = 0
            not_found = list(data_dict.keys())

            for page_num in range(doc.page_count):
                page = doc._doc[page_num]
                for widget in page.widgets():
                    if widget.field_name in data_dict:
                        value = data_dict[widget.field_name]
                        if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                            widget.field_value = "Yes" if value else "Off"
                        else:
                            widget.field_value = value
                        widget.update()
                        filled += 1
                        if widget.field_name in not_found:
                            not_found.remove(widget.field_name)

            if filled == 0:
                return False, "No fields matched the provided data", {
                    "filled": 0,
                    "not_found": not_found,
                }

            doc._modified = True

            return True, f"Filled {filled} field(s)", {
                "filled": filled,
                "not_found": not_found if not_found else None,
            }
        except Exception as e:
            return False, str(e), {}

    def flatten_form(self, doc):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}

            total = 0
            for page_num in range(doc.page_count):
                page = doc._doc[page_num]
                for widget in page.widgets():
                    widget.field_flags |= fitz.PDF_FIELD_IS_READ_ONLY
                    widget.update()
                    total += 1

            doc._modified = True

            return True, f"Form flattened ({total} field(s) set to read-only)", {
                "fields_flattened": total,
            }
        except Exception as e:
            return False, str(e), {}

    def export_form_data(self, doc, output_path):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}

            fields = []
            for page_num in range(doc.page_count):
                page = doc._doc[page_num]
                for widget in page.widgets():
                    fields.append({
                        "name": widget.field_name,
                        "value": widget.field_value,
                    })

            root = ET.Element(
                "xfdf",
                {"xmlns": "http://ns.adobe.com/xfdf/", "xml:space": "preserve"},
            )
            fields_elem = ET.SubElement(root, "fields")
            for f in fields:
                if f["name"]:
                    field_elem = ET.SubElement(fields_elem, "field", name=f["name"])
                    value_elem = ET.SubElement(field_elem, "value")
                    value_elem.text = str(f["value"]) if f["value"] is not None else ""

            tree = ET.ElementTree(root)
            tree.write(output_path, encoding="UTF-8", xml_declaration=True)

            return True, f"Exported {len(fields)} field(s) to {output_path}", {
                "fields_count": len(fields),
                "path": output_path,
            }
        except Exception as e:
            return False, str(e), {}

    def import_form_data(self, doc, input_path):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}

            tree = ET.parse(input_path)
            root = tree.getroot()

            ns = {"xfdf": "http://ns.adobe.com/xfdf/"}
            fields_data = {}
            for field_elem in root.iter("{http://ns.adobe.com/xfdf/}field"):
                name = field_elem.get("name")
                value_elem = field_elem.find("{http://ns.adobe.com/xfdf/}value")
                value = value_elem.text if value_elem is not None else None
                if name:
                    fields_data[name] = value

            if not fields_data:
                return False, "No form data found in file", {}

            result = self.fill_form(doc, fields_data)
            return result
        except ET.ParseError as e:
            return False, f"Invalid XML file: {e}", {}
        except Exception as e:
            return False, str(e), {}

    def add_text_field(self, doc, page_index, rect, field_name, default_value=""):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}
            if page_index < 0 or page_index >= doc.page_count:
                return False, "Invalid page index", {}

            page = doc._doc[page_index]
            widget = fitz.Widget()
            widget.rect = fitz.Rect(rect)
            widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
            widget.field_name = field_name
            widget.field_value = default_value
            page.add_widget(widget)
            widget.update()

            doc._modified = True

            return True, f"Text field '{field_name}' added", {
                "field_name": field_name,
                "page": page_index,
            }
        except Exception as e:
            return False, str(e), {}

    def add_checkbox(self, doc, page_index, rect, field_name):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}
            if page_index < 0 or page_index >= doc.page_count:
                return False, "Invalid page index", {}

            page = doc._doc[page_index]
            widget = fitz.Widget()
            widget.rect = fitz.Rect(rect)
            widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
            widget.field_name = field_name
            widget.field_value = "Off"
            page.add_widget(widget)
            widget.update()

            doc._modified = True

            return True, f"Checkbox '{field_name}' added", {
                "field_name": field_name,
                "page": page_index,
            }
        except Exception as e:
            return False, str(e), {}

    def add_radio_button(self, doc, page_index, rects, field_name):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}
            if page_index < 0 or page_index >= doc.page_count:
                return False, "Invalid page index", {}
            if not rects:
                return False, "No rectangles provided for radio buttons", {}

            page = doc._doc[page_index]
            for i, rect in enumerate(rects):
                widget = fitz.Widget()
                widget.rect = fitz.Rect(rect)
                widget.field_type = fitz.PDF_WIDGET_TYPE_RADIOBUTTON
                widget.field_name = field_name
                widget.field_value = str(i)
                page.add_widget(widget)
                widget.update()

            doc._modified = True

            return True, f"Radio button group '{field_name}' added ({len(rects)} option(s))", {
                "field_name": field_name,
                "page": page_index,
                "options_count": len(rects),
            }
        except ValueError:
            return False, (
                "Radio button creation is not supported in this PyMuPDF version. "
                "Use checkboxes as an alternative."
            ), {}
        except Exception as e:
            return False, str(e), {}

    def add_dropdown(self, doc, page_index, rect, field_name, options):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}
            if page_index < 0 or page_index >= doc.page_count:
                return False, "Invalid page index", {}
            if not options:
                return False, "No options provided for dropdown", {}

            page = doc._doc[page_index]
            widget = fitz.Widget()
            widget.rect = fitz.Rect(rect)
            widget.field_type = fitz.PDF_WIDGET_TYPE_COMBOBOX
            widget.field_name = field_name
            widget.choice_values = options
            widget.field_value = options[0]
            page.add_widget(widget)
            widget.update()

            doc._modified = True

            return True, f"Dropdown '{field_name}' added ({len(options)} option(s))", {
                "field_name": field_name,
                "page": page_index,
                "options_count": len(options),
            }
        except Exception as e:
            return False, str(e), {}
