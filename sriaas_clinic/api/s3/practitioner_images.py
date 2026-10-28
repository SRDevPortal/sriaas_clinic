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
    """Accept site-prefixed portraits and legacy unprefixed portraits."""
    parsed = urlparse(url or "")
    host = f"{image_bucket()}.s3.{image_region()}.amazonaws.com"
    if parsed.scheme != "https" or parsed.netloc != host or parsed.query or parsed.fragment:
        return None
    key = unquote(parsed.path.lstrip("/"))
    # Import lazily: upload imports this module for portrait routing.
    from .upload import normalize_part

    prefix = frappe.conf.get("aws_s3_prefix")
    if not prefix:
        company = frappe.defaults.get_user_default("Company")
        prefix = frappe.get_cached_value("Company", company, "abbr") if company else "MISC"
    prefixes = (f"{normalize_part(prefix)}/doctor/", "doctor/")
    if any(p in (".", "..") for p in key.split("/")):
        return None
    if not any(key.startswith(path) and len(key) > len(path) for path in prefixes):
        return None
    return key
