# sriaas_clinic/api/practitioner.py
import frappe

def compose_full_name(doc, method=None):
    if doc.get("practitioner_name"):
        return
    parts = [doc.get("first_name"), doc.get("middle_name"), doc.get("last_name")]
    full = " ".join([p.strip() for p in parts if p]).strip()
    if full:
        doc.practitioner_name = full
