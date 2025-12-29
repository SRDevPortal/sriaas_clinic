# sriaas_clinic/api/s3/utils.py
from urllib.parse import urlparse, unquote

def extract_key(file_url: str) -> str | None:
    if not file_url:
        return None

    if file_url.startswith("s3://"):
        key = file_url.replace("s3://", "", 1)
    elif "amazonaws.com" in file_url:
        parsed = urlparse(file_url)
        key = parsed.path.lstrip("/")
    else:
        return None

    return unquote(key)
