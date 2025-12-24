# sriaas_clinic/api/s3/upload.py
import mimetypes
from datetime import datetime
import frappe
from frappe.utils.file_manager import get_file_path

from .client import get_s3_client, get_bucket

def get_logger():
    logger = frappe.logger("sriaas_s3", allow_site=True)
    logger.setLevel("INFO")
    return logger

def _get_company_abbr(file_doc):
    company = None
    if file_doc.attached_to_doctype and file_doc.attached_to_name:
        try:
            parent = frappe.get_doc(
                file_doc.attached_to_doctype,
                file_doc.attached_to_name
            )
            company = getattr(parent, "company", None)
        except Exception:
            pass

    if not company:
        company = frappe.defaults.get_user_default("Company")

    if company:
        return frappe.get_cached_value("Company", company, "abbr")
    return "MISC"

def upload_file_to_s3(file_doc):
    logger = get_logger()
    s3 = get_s3_client()
    bucket = get_bucket()

    # company_abbr = _get_company_abbr(file_doc)
    # Use configured prefix if available or fallback to company abbr
    company_abbr = frappe.conf.get("aws_s3_prefix") or _get_company_abbr(file_doc)
    local_path = get_file_path(file_doc.file_url)

    content_type, _ = mimetypes.guess_type(local_path)
    content_type = content_type or "application/octet-stream"
    date = datetime.utcnow().strftime("%Y%m%d")

    key = (
        f"{company_abbr}/"
        f"{file_doc.attached_to_doctype or 'misc'}/"
        f"{date}/"
        f"{file_doc.name}_{file_doc.file_name}"
    )

    try:
        with open(local_path, "rb") as f:
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=f,
                ContentType=content_type,
                Metadata={
                    "company_abbr": company_abbr,
                    "doctype": file_doc.attached_to_doctype or "",
                    "docname": file_doc.attached_to_name or "",
                }
            )

        # ✅ Success log
        logger.info(
            f"S3_UPLOAD_SUCCESS | file={file_doc.name} | "
            f"filename={file_doc.file_name} | "
            f"company={company_abbr} | "
            f"doctype={file_doc.attached_to_doctype} | "
            f"docname={file_doc.attached_to_name} | "
            f"key={key} | user={frappe.session.user}"
        )

        return key

    except Exception as e:
        # ❌ Failure log (string)
        logger.error(
            f"S3_UPLOAD_FAILED | file={getattr(file_doc, 'name', None)} | "
            f"error={str(e)}\n{frappe.get_traceback()}"
        )

        raise
