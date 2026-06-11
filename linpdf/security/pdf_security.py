import fitz
import os
import tempfile
from datetime import datetime


class PDFSecurity:
    PERMISSION_FLAGS = {
        "printing": fitz.PDF_PERM_PRINT,
        "modifying": fitz.PDF_PERM_MODIFY,
        "copying": fitz.PDF_PERM_COPY,
        "annotating": fitz.PDF_PERM_ANNOTATE,
        "filling_forms": fitz.PDF_PERM_FORM,
        "accessibility": fitz.PDF_PERM_ACCESSIBILITY,
        "assembling": fitz.PDF_PERM_ASSEMBLE,
    }

    def encrypt(self, doc, password, owner_password=None, permissions=None):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}

            perm = 0
            if permissions:
                for flag in permissions:
                    f = self.PERMISSION_FLAGS.get(flag)
                    if f is not None:
                        perm |= f
            if perm == 0:
                perm = 4095

            owner_pw = owner_password if owner_password else password

            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp_path = tmp.name
            tmp.close()

            try:
                doc._doc.save(
                    tmp_path,
                    encryption=fitz.PDF_ENCRYPT_AES_256,
                    user_pw=password,
                    owner_pw=owner_pw,
                    permissions=perm,
                    deflate=True,
                    clean=True,
                )

                original_path = doc._path
                doc._doc.close()
                doc._doc = fitz.open(tmp_path)
                doc._path = original_path
                doc._modified = True

                return True, "Document encrypted successfully", {
                    "permissions": permissions or ["all"],
                    "has_owner_password": owner_password is not None,
                }
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            return False, str(e), {}

    def decrypt(self, doc, password):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}

            if doc._doc.is_encrypted:
                auth = doc._doc.authenticate(password)
                if auth == 0:
                    return False, "Incorrect password", {}
            elif not doc._doc.is_encrypted:
                return False, "Document is not encrypted", {}

            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp_path = tmp.name
            tmp.close()

            try:
                doc._doc.save(
                    tmp_path,
                    encryption=fitz.PDF_ENCRYPT_NONE,
                    deflate=True,
                    clean=True,
                )

                original_path = doc._path
                doc._doc.close()
                doc._doc = fitz.open(tmp_path)
                doc._path = original_path
                doc._modified = True

                return True, "Document decrypted successfully", {}
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            return False, str(e), {}

    def change_password(self, doc, old_password, new_password):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}

            if doc._doc.is_encrypted:
                auth = doc._doc.authenticate(old_password)
                if auth == 0:
                    return False, "Incorrect current password", {}

            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp_path = tmp.name
            tmp.close()

            try:
                current_encryption = not doc._doc.is_encrypted
                if current_encryption:
                    enc = fitz.PDF_ENCRYPT_NONE
                else:
                    enc = fitz.PDF_ENCRYPT_AES_256

                doc._doc.save(
                    tmp_path,
                    encryption=enc,
                    user_pw=new_password,
                    owner_pw=new_password,
                    deflate=True,
                    clean=True,
                )

                original_path = doc._path
                doc._doc.close()
                doc._doc = fitz.open(tmp_path)
                doc._path = original_path
                doc._modified = True

                return True, "Password changed successfully", {}
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            return False, str(e), {}

    def add_signature_field(self, doc, page_index, rect, field_name):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}
            if page_index < 0 or page_index >= doc.page_count:
                return False, "Invalid page index", {}

            page = doc._doc[page_index]
            widget = fitz.Widget()
            widget.rect = fitz.Rect(rect)
            widget.field_type = fitz.PDF_WIDGET_TYPE_SIGNATURE
            widget.field_name = field_name
            page.add_widget(widget)
            widget.update()

            doc._modified = True

            return True, f"Signature field '{field_name}' added", {
                "field_name": field_name,
                "page": page_index,
            }
        except Exception as e:
            return False, str(e), {}

    def sign_page(self, doc, page_index, rect, cert_path, password, reason="", location=""):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}
            if page_index < 0 or page_index >= doc.page_count:
                return False, "Invalid page index", {}

            if not os.path.exists(cert_path):
                return False, f"Certificate file not found: {cert_path}", {}

            if not cert_path.lower().endswith((".pfx", ".p12")):
                return False, "Unsupported certificate format. Use .pfx or .p12", {}

            page = doc._doc[page_index]
            field_name = f"Signature_{page_index}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            widget = fitz.Widget()
            widget.rect = fitz.Rect(rect)
            widget.field_type = fitz.PDF_WIDGET_TYPE_SIGNATURE
            widget.field_name = field_name
            page.add_widget(widget)
            widget.update()

            doc._modified = True

            return True, f"Signature field '{field_name}' added (cryptographic signing requires external tooling)", {
                "field_name": field_name,
                "page": page_index,
                "reason": reason,
                "location": location,
                "certificate": os.path.basename(cert_path),
            }
        except Exception as e:
            return False, str(e), {}

    def verify_signatures(self, doc):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", []

            results = []

            if hasattr(doc._doc, "get_sig_fields"):
                sig_fields = doc._doc.get_sig_fields()
                for sig in sig_fields:
                    valid = doc._doc.validate_signature(sig)
                    results.append({
                        "field": sig,
                        "valid": valid == fitz.PDF_SIGNATURE_ERROR_OKAY,
                        "status_code": valid,
                    })
            else:
                for page_num in range(doc.page_count):
                    page = doc._doc[page_num]
                    for widget in page.widgets():
                        if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                            results.append({
                                "field": widget.field_name,
                                "is_signed": widget.is_signed,
                                "page": page_num,
                                "rect": (
                                    widget.rect.x0,
                                    widget.rect.y0,
                                    widget.rect.x1,
                                    widget.rect.y1,
                                ),
                            })

            return True, f"Found {len(results)} signature(s)", {
                "signatures": results,
                "sig_flags": doc._doc.get_sigflags(),
            }
        except Exception as e:
            return False, str(e), []

    def redact_text(self, doc, search_text, replace_with=""):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}

            total = 0
            for page_num in range(doc.page_count):
                page = doc._doc[page_num]
                areas = page.search_for(search_text)
                for rect in areas:
                    kwargs = {}
                    if replace_with:
                        kwargs["text"] = replace_with
                    page.add_redact_annot(rect, **kwargs)
                    total += 1

            doc._modified = True

            return True, f"Redaction annotations added for {total} occurrence(s)", {
                "occurrences": total,
                "search_text": search_text,
            }
        except Exception as e:
            return False, str(e), {}

    def redact_area(self, doc, page_index, rect):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}
            if page_index < 0 or page_index >= doc.page_count:
                return False, "Invalid page index", {}

            page = doc._doc[page_index]
            page.add_redact_annot(fitz.Rect(rect))
            doc._modified = True

            return True, "Redaction annotation added", {
                "page": page_index,
                "rect": (rect.x0, rect.y0, rect.x1, rect.y1)
                if hasattr(rect, "x0")
                else rect,
            }
        except Exception as e:
            return False, str(e), {}

    def apply_redactions(self, doc):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}

            total = 0
            for page_num in range(doc.page_count):
                page = doc._doc[page_num]
                page.apply_redactions()
                total += 1

            doc._modified = True

            return True, f"Redactions applied to {total} page(s)", {
                "pages": total,
            }
        except Exception as e:
            return False, str(e), {}

    def redact_all(self, doc):
        try:
            if not doc.is_loaded:
                return False, "No document loaded", {}

            total = 0
            for page_num in range(doc.page_count):
                page = doc._doc[page_num]
                rect = page.rect
                page.add_redact_annot(rect)
                page.apply_redactions()
                total += 1

            doc._modified = True

            return True, f"Full document redacted ({total} page(s))", {
                "pages": total,
            }
        except Exception as e:
            return False, str(e), {}
