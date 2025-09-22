# sriaas_clinic/api/contact.py
import frappe

def _clean_spaces(s: str) -> str:
    # remove all whitespace (space, tab, newline)
    return ''.join(s.split()) if isinstance(s, str) else s

def normalize_phoneish_fields(doc, method=None):
    """
    Strip whitespace from phone-like fields on Contact.
    Runs on Contact.before_save. Safe & idempotent.
    """
    # Top-level fields commonly present on Contact
    CANDIDATE_FIELDS = (
        "mobile", "mobile_no",
        "phone", "phone_no",
        "whatsapp_no",
        "alternate_phone",
        "sr_mobile_no", "sr_whatsapp_no",
    )

    for field in CANDIDATE_FIELDS:
        val = doc.get(field)
        cleaned = _clean_spaces(val)
        if cleaned != val:
            doc.set(field, cleaned)

    # Optional: also normalize the child table "Contact Phone" if it exists
    # (standard childtable name: phone_nos with field 'phone')
    if hasattr(doc, "phone_nos") and isinstance(doc.phone_nos, (list, tuple)):
        for row in doc.phone_nos:
            if hasattr(row, "phone"):
                c = _clean_spaces(row.phone)
                if c != row.phone:
                    row.phone = c
            if hasattr(row, "whatsapp"):
                c = _clean_spaces(row.whatsapp)
                if c != getattr(row, "whatsapp"):
                    row.whatsapp = c
