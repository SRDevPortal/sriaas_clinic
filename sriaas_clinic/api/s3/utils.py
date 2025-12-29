# sriaas_clinic/api/s3/utils.py
from urllib.parse import urlparse

def extract_key(file_url: str) -> str | None:
    """
    Extract exact S3 object key from:
    - s3://bucket/key
    - https://bucket.s3.region.amazonaws.com/key

    IMPORTANT:
    - Do NOT decode (%20 must remain %20)
    - Key must match EXACT bytes stored in S3
    """
    if not file_url:
        return None

    if file_url.startswith("s3://"):
        return file_url.replace("s3://", "", 1)

    if "amazonaws.com" in file_url:
        parsed = urlparse(file_url)
        return parsed.path.lstrip("/")  # ❌ no unquote

    return None
