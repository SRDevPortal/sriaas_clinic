# sriaas_clinic/api/s3/delete.py

import frappe
from urllib.parse import unquote

from .client import get_s3_client, get_bucket

logger = frappe.logger("sriaas_s3")


def delete_file_from_s3(file_url: str):
    """
    Delete a file from S3 using s3://<key> format.

    Safe:
    - Supports old & new URLs
    - Never raises exception
    """

    if not file_url or not str(file_url).startswith("s3://"):
        return

    try:
        s3 = get_s3_client()
        bucket = get_bucket()

        # Extract key
        raw_key = file_url.replace("s3://", "", 1)
        key = unquote(raw_key)

        logger.info(
            f"S3_DELETE_ATTEMPT | bucket={bucket} | key={key}"
        )

        s3.delete_object(
            Bucket=bucket,
            Key=key
        )

        logger.info(
            f"S3_FILE_DELETED | bucket={bucket} | key={key}"
        )

    except Exception:
        logger.error(
            f"S3_DELETE_FAILED | url={file_url}\n{frappe.get_traceback()}"
        )


@frappe.whitelist()
def delete_s3_by_url(file_url: str):
    """
    Whitelisted API to delete S3 file by URL.
    Used when Attach field is cleared from UI.
    """

    if not file_url:
        return {"status": "no_file_url"}

    delete_file_from_s3(file_url)
    return {"status": "deleted"}
