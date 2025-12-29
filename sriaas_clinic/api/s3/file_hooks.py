# sriaas_clinic/api/s3/file_hooks.py

import frappe
from frappe.core.doctype.file.file import File
from .upload import upload_file_to_s3
from .delete import delete_file_from_s3

# --------------------------------------------------
# 🔧 Make File.exists_on_disk S3-safe
# --------------------------------------------------

_original_exists_on_disk = File.exists_on_disk


def s3_safe_exists_on_disk(self):
    """
    Prevent Frappe from checking os.path.exists() for S3 URLs.
    Fixes: Cannot access file path s3://...
    """
    if self.file_url and str(self.file_url).startswith("s3://"):
        return False
    return _original_exists_on_disk(self)


# Apply patch immediately when module loads
File.exists_on_disk = s3_safe_exists_on_disk

# --------------------------------------------------
# Logger
# --------------------------------------------------

logger = frappe.logger("sriaas_s3")


# --------------------------------------------------
# Hook: after_insert on File
# --------------------------------------------------
def handle_file_after_insert(doc, method=None):
    """
    After a File is saved locally by Frappe,
    upload it to S3 and replace file_url with s3://...
    """

    # 🔍 Debug: log current stage
    logger.info(
        f"FILE_HOOK_STAGE | name={doc.name} | url={doc.file_url}"
    )

    # Skip folders
    if doc.is_folder:
        return

    # If already migrated to S3, skip
    if doc.file_url and str(doc.file_url).startswith("s3://"):
        return

    try:
        key = upload_file_to_s3(doc)
        if not key:
            logger.error(f"S3_UPLOAD_FAILED | file={doc.name}")
            return

        s3_url = f"s3://{key}"

        # Update directly in DB to avoid recursion
        doc.db_set("file_url", s3_url, update_modified=False)

        # ✅ Success log
        logger.info(
            f"S3_FILE_MIGRATED | file={doc.name} | url={s3_url}"
        )

    except Exception:
        logger.error(
            f"S3_UPLOAD_EXCEPTION | file={doc.name}\n{frappe.get_traceback()}"
        )


def handle_file_on_trash(doc, method=None):
    """
    When a File is deleted from Frappe, also delete from S3.
    """
    if not doc.file_url:
        return

    # Only S3 files
    if str(doc.file_url).startswith("s3://"):
        delete_file_from_s3(doc.file_url)


# def after_file_insert(doc, method):
#     if not doc.file_url or doc.file_url.startswith(("http", "s3://")):
#         return

#     old_url = doc.file_url

#     try:
#         key = upload_file_to_s3(doc)
#         new_url = f"s3://{key}"

#         doc.db_set("file_url", new_url)
#         update_file_references(old_url, new_url)
#         frappe.delete_file(old_url, is_private=doc.is_private)

#     except Exception:
#         frappe.log_error(frappe.get_traceback(), "SRIAAS S3 Upload Failed")


# def update_file_references(old_url, new_url):
#     for doctype, fieldname in frappe.db.get_all(
#         "DocField",
#         filters={"fieldtype": "Attach"},
#         fields=["parent as doctype", "fieldname"],
#     ):
#         frappe.db.sql(
#             f"UPDATE `tab{doctype}` SET `{fieldname}`=%s WHERE `{fieldname}`=%s",
#             (new_url, old_url),
#         )
#     frappe.db.commit()
