# sriaas_clinic/api/s3/utils.py
import frappe
from urllib.parse import urlparse, unquote


def extract_key(file_url: str) -> str | None:
    if not file_url:
        return None

    try:
        # ✅ Case 1: s3://bucket/key
        if file_url.startswith("s3://"):
            return unquote(file_url.replace("s3://", "", 1))

        # ✅ Case 2: Any HTTP/HTTPS URL (S3, CDN, custom domain)
        parsed = urlparse(file_url)

        if parsed.scheme in ("http", "https"):
            return unquote(parsed.path.lstrip("/"))

        return None

    except Exception:
        frappe.log_error(frappe.get_traceback(), "S3_EXTRACT_KEY_FAILED")
        return None


def is_s3_enabled():
    return all([
        frappe.conf.get("aws_access_key_id"),
        frappe.conf.get("aws_secret_access_key"),
        frappe.conf.get("aws_region"),
        frappe.conf.get("aws_bucket"),
    ])