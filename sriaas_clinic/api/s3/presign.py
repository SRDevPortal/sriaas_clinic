"""Permission-checked S3 attachment links; no raw-URL fallback on failure."""
import frappe
from botocore.exceptions import ClientError
from .client import get_s3_client, get_bucket
from .access import source_key, authorize_source


@frappe.whitelist()
def get_presigned_url(file_url, expires=900, doctype=None, docname=None):
    if not file_url:
        return None
    bucket = get_bucket()
    key = source_key(file_url, bucket, frappe.conf.get("aws_s3_region"))
    authorize_source(file_url, key, bucket, frappe.conf.get("aws_s3_region"), doctype, docname)
    try:
        expires = int(expires)
    except (TypeError, ValueError):
        raise frappe.ValidationError("Expiry must be between 1 and 900 seconds.")
    if not 1 <= expires <= 900:
        raise frappe.ValidationError("Expiry must be between 1 and 900 seconds.")
    s3 = get_s3_client()
    if not s3 or not bucket:
        raise frappe.ValidationError("Attachment storage is unavailable.")
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return s3.generate_presigned_url(
            ClientMethod="get_object", Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires,
        )
    except ClientError as exc:
        code = (exc.response.get("Error") or {}).get("Code")
        if code in ("404", "NoSuchKey", "NotFound"):
            raise frappe.ValidationError("The attachment is missing from storage.") from None
        raise frappe.ValidationError("Attachment storage could not provide a download link.") from None
