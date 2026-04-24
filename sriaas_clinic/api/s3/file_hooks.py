# sriaas_clinic/api/s3/file_hooks.py

import os
import frappe
from frappe.core.doctype.file.file import File
from frappe.core.doctype.file import file as file_module
from frappe.utils.file_manager import get_file_path

from .utils import extract_key, is_s3_enabled
from .client import get_s3_client, get_bucket
from .upload import upload_file_to_s3
from .delete import delete_file_from_s3


# ==================================================
# 🔧 PATCH 1: Make File.exists_on_disk S3-safe
# ==================================================

_original_exists_on_disk = File.exists_on_disk

if "s3://" not in file_module.URL_PREFIXES:
    file_module.URL_PREFIXES = (*file_module.URL_PREFIXES, "s3://")


def s3_safe_exists_on_disk(self):
    """
    Prevent Frappe from checking os.path.exists() for s3:// URLs
    """
    if self.file_url and str(self.file_url).startswith("s3://"):
        return False
    return _original_exists_on_disk(self)


File.exists_on_disk = s3_safe_exists_on_disk


# ==================================================
# 🔧 PATCH 2: Allow s3:// in validate_file_url
# ==================================================

_original_validate_file_url = File.validate_file_url


def s3_safe_validate_file_url(self):
    """
    Allow s3:// URLs without raising validation errors
    """
    if self.file_url and str(self.file_url).startswith("s3://"):
        return
    return _original_validate_file_url(self)


File.validate_file_url = s3_safe_validate_file_url


# ==================================================
# 🔧 PATCH 3: STOP core File.validate() error popup
# ==================================================

_original_file_validate = File.validate


def s3_safe_file_validate(self):
    """
    Fully bypass File validation for s3:// URLs
    """
    if self.file_url and str(self.file_url).startswith("s3://"):
        return
    return _original_file_validate(self)


File.validate = s3_safe_file_validate


# ==================================================
# PATCH 4: Read S3 files as remote content
# ==================================================

_original_get_full_path = File.get_full_path
_original_get_content = File.get_content


def s3_safe_get_full_path(self):
    """
    Keep S3 URLs out of local path validation.
    """
    if self.file_url and str(self.file_url).startswith("s3://"):
        return self.file_url
    return _original_get_full_path(self)


def s3_safe_get_content(self):
    """
    Download bytes from S3 when Frappe asks for file content.
    """
    if self.file_url and str(self.file_url).startswith("s3://"):
        key = extract_key(self.file_url)
        s3 = get_s3_client()
        bucket = get_bucket()

        if not key or not s3 or not bucket:
            frappe.throw(f"Cannot read S3 file: {self.file_url}")

        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            self._content = response["Body"].read()
            return self._content
        except Exception:
            frappe.log_error(frappe.get_traceback(), "S3_READ_FAILED")
            frappe.throw(f"Cannot read S3 file: {self.file_url}")

    return _original_get_content(self)


File.get_full_path = s3_safe_get_full_path
File.get_content = s3_safe_get_content


# ==================================================
# Logger
# ==================================================

logger = frappe.logger("sriaas_s3")

PAYMENT_PROOF_PARENT_DOCTYPE = "Patient Encounter"
PAYMENT_PROOF_FIELD = "mmp_payment_proof"


def _skip_s3_delete_file_names():
    skip_names = getattr(frappe.flags, "sriaas_skip_s3_delete_file_names", None)
    if skip_names is None:
        skip_names = set()
        frappe.flags.sriaas_skip_s3_delete_file_names = skip_names
    return skip_names


def _is_payment_proof_file(doc):
    return (
        doc.attached_to_doctype == PAYMENT_PROOF_PARENT_DOCTYPE
        and doc.attached_to_field == PAYMENT_PROOF_FIELD
    )


def _delete_file_doc_only(file_name):
    if not file_name:
        return

    skip_names = _skip_s3_delete_file_names()
    skip_names.add(file_name)
    try:
        frappe.delete_doc("File", file_name, ignore_permissions=True)
    except frappe.DoesNotExistError:
        pass
    finally:
        skip_names.discard(file_name)


def _delete_payment_proof_file_docs(attached_to_name=None, file_url=None):
    filters = {
        "attached_to_doctype": PAYMENT_PROOF_PARENT_DOCTYPE,
        "attached_to_field": PAYMENT_PROOF_FIELD,
    }

    if attached_to_name:
        filters["attached_to_name"] = attached_to_name
    if file_url:
        filters["file_url"] = file_url

    for file_name in frappe.get_all("File", filters=filters, pluck="name"):
        _delete_file_doc_only(file_name)


# ==================================================
# Hook: after_insert on File (Upload → S3 OR Local)
# ==================================================

def handle_file_after_insert(doc, method=None):

    # --------------------------------------------------
    # 🚨 HARD SKIP: SYSTEM FILES (STAY LOCAL)
    # --------------------------------------------------

    # 1. Prepared Reports
    if doc.attached_to_doctype == "Prepared Report":
        return

    # 2. Report file formats
    if doc.file_name and doc.file_name.endswith((".json.gz", ".csv", ".xlsx")):
        return

    # 3. System-generated (no parent)
    if not doc.attached_to_doctype:
        return

    # 4. Skip internal/private system files
    # if doc.is_private:
    #     return

    # --------------------------------------------------
    # 🚨 Skip folders
    # --------------------------------------------------
    if doc.is_folder:
        return

    # --------------------------------------------------
    # 🚨 Skip if already S3
    # --------------------------------------------------
    if doc.file_url and str(doc.file_url).startswith("s3://"):
        return
    
    # --------------------------------------------------
    # ✅ S3 CONFIG CHECK (IMPORTANT)
    # --------------------------------------------------
    if not is_s3_enabled():
        return

    try:
        # --------------------------------------------------
        # 1️⃣ Local file path
        # --------------------------------------------------
        local_path = get_file_path(doc.file_url)

        # --------------------------------------------------
        # 2️⃣ Upload to S3
        # --------------------------------------------------
        key = upload_file_to_s3(doc)
        if not key:
            return
        
        # --------------------------------------------------
        # 3️⃣ Save S3 URL
        # --------------------------------------------------
        s3_url = f"s3://{key}"
        doc.db_set("file_url", s3_url, update_modified=False)

        if _is_payment_proof_file(doc):
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
            _delete_file_doc_only(doc.name)
            return

        # --------------------------------------------------
        # 4️⃣ Delete local file
        # --------------------------------------------------
        if local_path and os.path.exists(local_path):
            os.remove(local_path)

    except Exception:
        frappe.log_error(frappe.get_traceback(), "S3_UPLOAD_FAILED")


# ==================================================
# Hook: on_trash on File (Delete → S3)
# ==================================================

def handle_file_on_trash(doc, method=None):
    if doc.name in _skip_s3_delete_file_names():
        return

    if not doc.file_url:
        return
    
    key = extract_key(doc.file_url)
    if not key:
        return

    try:
        s3_url = f"s3://{key}"
        delete_file_from_s3(s3_url)

    except Exception:
        frappe.log_error(frappe.get_traceback(), "S3_DELETE_FAILED")


def cleanup_payment_proof_removals(doc, method=None):
    previous_doc = doc.get_doc_before_save()
    if not previous_doc:
        return

    previous_rows = {
        row.name: (row.mmp_payment_proof or "").strip()
        for row in (previous_doc.get("enc_multi_payments") or [])
        if getattr(row, "name", None)
    }
    current_rows = {
        row.name: (row.mmp_payment_proof or "").strip()
        for row in (doc.get("enc_multi_payments") or [])
        if getattr(row, "name", None)
    }
    current_urls = {url for url in current_rows.values() if url}
    deleted_urls = set()

    for row_name, old_url in previous_rows.items():
        if not old_url:
            continue

        if current_rows.get(row_name) == old_url:
            continue

        if old_url in current_urls or old_url in deleted_urls:
            continue

        _delete_payment_proof_file_docs(attached_to_name=doc.name, file_url=old_url)
        delete_file_from_s3(old_url)
        deleted_urls.add(old_url)
