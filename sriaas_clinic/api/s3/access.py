"""Authorize attachment signing before contacting storage."""
from urllib.parse import urlsplit, unquote, quote
import frappe


def source_key(file_url, bucket, region):
    if not isinstance(file_url, str) or not file_url or not bucket:
        raise frappe.PermissionError("Invalid attachment source.")
    parsed = urlsplit(file_url)
    if parsed.query or parsed.fragment:
        raise frappe.PermissionError("Use the stored attachment URL.")
    if file_url.startswith("s3://"):
        key = unquote(file_url[5:])
    elif parsed.scheme == "https" and parsed.netloc in {
        f"{bucket}.s3.amazonaws.com", f"{bucket}.s3.{region}.amazonaws.com",
    }:
        key = unquote(parsed.path.lstrip("/"))
    else:
        raise frappe.PermissionError("Unsupported attachment source.")
    if not key or key.startswith("/") or any(p in (".", "..") for p in key.split("/")):
        raise frappe.PermissionError("Invalid attachment source.")
    return key


def source_aliases(file_url, key, bucket, region):
    encoded = quote(key, safe="/")
    return list(dict.fromkeys([file_url, "s3://" + key, "s3://" + encoded,
        f"https://{bucket}.s3.amazonaws.com/{encoded}",
        f"https://{bucket}.s3.{region}.amazonaws.com/{encoded}"]))


def references_attachment(doc, aliases):
    """Only readable Attach fields, including readable child tables, establish ownership."""
    for field in frappe.get_meta(doc.doctype).fields:
        if field.fieldtype in ("Attach", "Attach Image") and doc.get(field.fieldname) in aliases:
            return True
        if field.fieldtype in ("Table", "Table MultiSelect"):
            if any(references_attachment(row, aliases) for row in doc.get(field.fieldname) or []):
                return True
    return False


def authorize_source(file_url, key, bucket, region, doctype=None, docname=None):
    if frappe.session.user == "Guest":
        raise frappe.PermissionError("Login is required.")
    aliases = source_aliases(file_url, key, bucket, region)
    pilot = bool(frappe.conf.get("privacy_shield_desk_enabled", False))
    restricted = False
    if pilot:
        from privacy_shield.import_access import restricted as is_restricted, check_import_urls
        from privacy_shield.report_outputs import check_attachment_urls
        restricted = is_restricted()
        if restricted:
            check_import_urls(aliases)
            check_attachment_urls(aliases)
    rows = frappe.get_all("File", filters={"file_url": ["in", aliases]},
        fields=["name", "attached_to_doctype"], limit_page_length=101)
    if len(rows) > 100:
        raise frappe.PermissionError("Attachment references require review.")
    if restricted:
        from privacy_shield.desk import SCOPE
        if any(row.attached_to_doctype in SCOPE for row in rows) or doctype in SCOPE:
            raise frappe.PermissionError("Attachments for this record require privacy review.")
    for row in rows:
        if frappe.get_doc("File", row.name).has_permission("read"):
            return
    if doctype and docname:
        meta = frappe.get_meta(doctype)
        if meta.istable:
            raise frappe.PermissionError("Use the parent record for attachment access.")
        doc = frappe.get_doc(doctype, docname)
        doc.check_permission("read")
        doc.apply_fieldlevel_read_permissions()
        if references_attachment(doc, aliases):
            return
    raise frappe.PermissionError("You cannot access this attachment.")
