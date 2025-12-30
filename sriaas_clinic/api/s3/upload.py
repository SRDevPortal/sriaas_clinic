# sriaas_clinic/api/s3/upload.py
import mimetypes
import re, os
from datetime import datetime

import frappe
from frappe.utils.file_manager import get_file_path

from .client import get_s3_client, get_bucket


# --------------------------------------------------
# Logger
# --------------------------------------------------
def get_logger():
    logger = frappe.logger("sriaas_s3", allow_site=True)
    logger.setLevel("INFO")
    return logger


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def normalize_part(value: str) -> str:
    """
    Convert strings to lowercase kebab-case for S3 keys
    Example:
        "Patient Encounter" -> "patient-encounter"
    """
    if not value:
        return "misc"

    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)   # remove special chars
    value = re.sub(r"[\s_]+", "-", value)    # space/_ → hyphen
    return value


def normalize_filename(filename: str) -> str:
    """
    Normalize filename but preserve extension
    Example:
      male Patient.JPG → male-patient.jpg
    """
    if not filename:
        return "file"

    name, ext = os.path.splitext(filename)

    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name)

    ext = ext.lower()  # keep .jpg, .png, etc.

    return f"{name}{ext}"


def _get_company_abbr(file_doc):
    """
    Resolve company abbreviation from parent doc or user defaults
    """
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


# --------------------------------------------------
# Core Upload Function
# --------------------------------------------------

def upload_file_to_s3(file_doc):
    """
    Upload a local Frappe File to S3 and return the S3 key.
    - Skips remote / already S3 files
    - Normalizes path for clean S3 URLs
    """

    logger = get_logger()
    s3 = get_s3_client()
    bucket = get_bucket()

    # --------------------------------------------------
    # Skip if already remote or S3
    # --------------------------------------------------
    if not file_doc.file_url or file_doc.file_url.startswith(("s3://", "http")):
        if file_doc.file_url and file_doc.file_url.startswith("s3://"):
            return file_doc.file_url.replace("s3://", "", 1)
        return None
    
    # --------------------------------------------------
    # Resolve & normalize S3 path parts
    # --------------------------------------------------
    raw_prefix = frappe.conf.get("aws_s3_prefix") or _get_company_abbr(file_doc)

    prefix = normalize_part(raw_prefix)
    doctype = normalize_part(file_doc.attached_to_doctype or "misc")
    filename = normalize_filename(file_doc.file_name)

    date = datetime.utcnow().strftime("%Y%m%d")

    try:
        # --------------------------------------------------
        # Local file path
        # --------------------------------------------------
        local_path = get_file_path(file_doc.file_url)

        content_type, _ = mimetypes.guess_type(local_path)
        content_type = content_type or "application/octet-stream"

        # --------------------------------------------------
        # Final S3 Key (🔥 CLEAN FORMAT)
        # --------------------------------------------------
        key = (
            f"{prefix}/"
            f"{doctype}/"
            f"{date}/"
            f"{file_doc.name}_{filename}"
        )

        # --------------------------------------------------
        # Upload
        # --------------------------------------------------
        with open(local_path, "rb") as f:
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=f,
                ContentType=content_type,
                Metadata={
                    "company_abbr": prefix,
                    "doctype": doctype,
                    "docname": file_doc.attached_to_name or "",
                }
            )

        # --------------------------------------------------
        # Success Log
        # --------------------------------------------------
        logger.info(
            f"S3_UPLOAD_SUCCESS | "
            f"file={file_doc.name} | "
            f"filename={file_doc.file_name} | "
            f"bucket={bucket} | "
            f"key={key} | "
            f"user={frappe.session.user}"
        )

        return key

    except Exception as e:
        logger.error(
            f"S3_UPLOAD_FAILED | "
            f"file={getattr(file_doc, 'name', None)} | "
            f"error={str(e)}\n{frappe.get_traceback()}"
        )
        raise
