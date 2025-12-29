# sriaas_clinic/api/s3/delete.py

import frappe
from .client import get_s3_client, get_bucket

logger = frappe.logger("sriaas_s3")


def delete_file_from_s3(file_url: str):
    """
    Delete a file from S3 using an s3://bucket/key URL.
    Safe: does not raise exception to avoid breaking Frappe flow.
    """

    if not file_url or not str(file_url).startswith("s3://"):
        return

    try:
        s3 = get_s3_client()
        bucket = get_bucket()

        # file_url format: s3://bucket/key
        s3_path = file_url.replace("s3://", "", 1)

        if s3_path.startswith(bucket + "/"):
            key = s3_path[len(bucket) + 1:]
        else:
            key = s3_path

        logger.info(
            f"S3_DELETE_ATTEMPT | url={file_url} | key={key}"
        )

        s3.delete_object(Bucket=bucket, Key=key)

        logger.info(
            f"S3_FILE_DELETED | key={key}"
        )

    except Exception:
        logger.error(
            f"S3_DELETE_FAILED | url={file_url}\n{frappe.get_traceback()}"
        )
        # Do NOT raise → keep UI delete safe


@frappe.whitelist()
def delete_s3_by_url(file_url: str):
    """
    Whitelisted API to delete S3 file by URL.
    Used when Attach field is cleared from UI.
    """
    if not file_url:
        return

    delete_file_from_s3(file_url)
    return {"status": "deleted"}
