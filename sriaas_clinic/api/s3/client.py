# sriaas_clinic/api/s3/client.py
import frappe
import boto3
from .utils import is_s3_enabled


def get_s3_client():
    if not is_s3_enabled():
        return None

    try:
        return boto3.client(
            "s3",
            aws_access_key_id=frappe.conf.get("aws_access_key_id"),
            aws_secret_access_key=frappe.conf.get("aws_secret_access_key"),
            region_name=frappe.conf.get("aws_region"),
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "S3_CLIENT_INIT_FAILED")
        return None


def get_bucket():
    if not is_s3_enabled():
        return None

    bucket = frappe.conf.get("aws_bucket")

    if not bucket:
        frappe.log_error("Missing aws_bucket", "S3_CONFIG_ERROR")
        return None

    return bucket