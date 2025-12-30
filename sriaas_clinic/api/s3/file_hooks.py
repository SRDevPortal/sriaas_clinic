# sriaas_clinic/api/s3/file_hooks.py

import os
import frappe
from frappe.core.doctype.file.file import File
from frappe.utils.file_manager import get_file_path

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
    This prevents:
    'There is some problem with the file url: s3://...'
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
# Hook: after_insert on File (Upload → S3)
# ==================================================

def handle_file_after_insert(doc, method=None):
    """
    After a File is saved locally by Frappe,
    upload it to S3, update file_url, and
    delete the local file immediately.
    """

    logger.info(
        f"FILE_HOOK_STAGE | name={doc.name} | url={doc.file_url}"
    )

    # Skip folders
    if doc.is_folder:
        return

    # Skip if already migrated
    if doc.file_url and str(doc.file_url).startswith("s3://"):
        return

    try:
        # --------------------------------------------------
        # 1️⃣ Capture local file path BEFORE upload
        # --------------------------------------------------
        local_path = get_file_path(doc.file_url)

        # --------------------------------------------------
        # 2️⃣ Upload to S3
        # --------------------------------------------------
        key = upload_file_to_s3(doc)
        if not key:
            logger.error(f"S3_UPLOAD_FAILED | file={doc.name}")
            return

        s3_url = f"s3://{key}"

        # --------------------------------------------------
        # 3️⃣ Update file_url in DB
        # --------------------------------------------------
        doc.db_set("file_url", s3_url, update_modified=False)

        logger.info(
            f"S3_FILE_MIGRATED | file={doc.name} | url={s3_url}"
        )

        # --------------------------------------------------
        # 4️⃣ DELETE LOCAL FILE (🔥 THIS IS THE FIX)
        # --------------------------------------------------
        try:
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
                logger.info(
                    f"LOCAL_FILE_REMOVED_AFTER_S3_UPLOAD | "
                    f"file={doc.name} | path={local_path}"
                )
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "LOCAL_FILE_DELETE_AFTER_UPLOAD_FAILED"
            )

    except Exception:
        logger.error(
            f"S3_UPLOAD_EXCEPTION | file={doc.name}\n{frappe.get_traceback()}"
        )


#==================================================
# Hook: on_trash on File (Delete → S3 + Local)
# ==================================================

def handle_file_on_trash(doc, method=None):
    """
    When a File is deleted from Frappe:
    - delete from S3 (if s3://)
    """

    if not doc.file_url:
        return

    if not str(doc.file_url).startswith("s3://"):
        return

    try:
        delete_file_from_s3(doc.file_url)

        logger.info(
            f"S3_FILE_DELETED | file={doc.name} | url={doc.file_url}"
        )

    except Exception:
        # Never block File deletion
        frappe.log_error(
            frappe.get_traceback(),
            "S3_DELETE_FAILED"
        )
