# sriaas_clinic/api/s3/presign.py
import frappe
from .client import get_s3_client, get_bucket
from .utils import extract_key

@frappe.whitelist()
def get_presigned_url(file_url, expires=900):
    key = extract_key(file_url)
    if not key:
        return file_url

    s3 = get_s3_client()
    bucket = get_bucket()

    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=int(expires)
    )
