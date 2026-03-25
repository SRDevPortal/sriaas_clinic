# sriaas_clinic/api/s3/file_hooks.py

import os
import frappe
from frappe.core.doctype.file.file import File
from frappe.utils.file_manager import get_file_path

from .utils import extract_key, is_s3_enabled
from .upload import upload_file_to_s3
from .delete import delete_file_from_s3


# ==================================================
# 🔧 PATCH 1: Make File.exists_on_disk S3-safe
# ==================================================

_original_exists_on_disk = File.exists_on_disk


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
# Logger
# ==================================================

logger = frappe.logger("sriaas_s3")


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