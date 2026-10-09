"""Public storage routing for practitioner profile images."""
from urllib.parse import quote, unquote, urlparse
import frappe

def is_practitioner_image(doc):
    return doc.attached_to_doctype == "Healthcare Practitioner" and doc.attached_to_field == "image"

def image_bucket():
    return frappe.conf.get("aws_s3_bucket")

def image_region():
    return frappe.conf.get("aws_s3_region")

def image_url(key):
    return f"https://{image_bucket()}.s3.{image_region()}.amazonaws.com/{quote(key, safe='/')}"

def public_image_key(url):
    """Accept only the configured endpoint and doctor prefix."""
    parsed = urlparse(url or "")
    host = f"{image_bucket()}.s3.{image_region()}.amazonaws.com"
    if parsed.scheme != "https" or parsed.netloc != host or parsed.query or parsed.fragment:
        return None
    key = unquote(parsed.path.lstrip("/"))
    if not key.startswith("doctor/") or key == "doctor/" or any(p in (".", "..") for p in key.split("/")):
        return None
    return key
