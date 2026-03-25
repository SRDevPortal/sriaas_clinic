# sriaas_clinic/api/s3/presign.py
import frappe
from .client import get_s3_client, get_bucket
from .utils import extract_key

logger = frappe.logger("sriaas_s3")


@frappe.whitelist()
def get_presigned_url(file_url, expires=900):
    """
    Generate a presigned URL for S3 file access.

    Features:
    - Supports s3:// and HTTP URLs
    - Safe fallback if config missing
    - Optional expiry control
    """

    if not file_url:
        return None

    try:
        # --------------------------------------------------
        # Extract S3 key
        # --------------------------------------------------
        key = extract_key(file_url)

        if not key:
            logger.info(f"PRESIGN_SKIPPED | invalid_url={file_url}")
            return file_url

        # --------------------------------------------------
        # Get S3 client
        # --------------------------------------------------
        s3 = get_s3_client()
        bucket = get_bucket()

        if not s3 or not bucket:
            logger.info("S3_DISABLED → returning original URL")
            return file_url
        
        # --------------------------------------------------
        # Validate expiry
        # --------------------------------------------------
        try:
            expires = int(expires)
        except Exception:
            expires = 900  # default 15 min

        # --------------------------------------------------
        # Generate presigned URL
        # --------------------------------------------------
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": bucket,
                "Key": key,

                # 🔥 Optional: force download name
                # "ResponseContentDisposition": f'attachment; filename="{key.split("/")[-1]}"'
            },
            ExpiresIn=expires
        )

        logger.info(f"PRESIGN_SUCCESS | key={key}")

        return url

    except Exception:
        logger.error(
            f"PRESIGN_FAILED | url={file_url}\n{frappe.get_traceback()}"
        )
        return file_url