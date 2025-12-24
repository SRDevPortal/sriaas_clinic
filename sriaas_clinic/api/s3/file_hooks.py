# sriaas_clinic/api/s3/hooks.py
import frappe
from .upload import upload_file_to_s3

def after_file_insert(doc, method):
    if not doc.file_url or doc.file_url.startswith(("http", "s3://")):
        return

    old_url = doc.file_url

    try:
        key = upload_file_to_s3(doc)
        new_url = f"s3://{key}"

        doc.db_set("file_url", new_url)
        update_file_references(old_url, new_url)
        frappe.delete_file(old_url, is_private=doc.is_private)

    except Exception:
        frappe.log_error(frappe.get_traceback(), "SRIAAS S3 Upload Failed")

def update_file_references(old_url, new_url):
    for doctype, fieldname in frappe.db.get_all(
        "DocField",
        filters={"fieldtype": "Attach"},
        fields=["parent as doctype", "fieldname"],
    ):
        frappe.db.sql(
            f"UPDATE `tab{doctype}` SET `{fieldname}`=%s WHERE `{fieldname}`=%s",
            (new_url, old_url),
        )
    frappe.db.commit()
