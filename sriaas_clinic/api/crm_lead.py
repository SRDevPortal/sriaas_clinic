# sriaas_clinic/api/crm_lead.py
import frappe

def _clean_spaces(s: str) -> str:
    return ''.join(s.split()) if isinstance(s, str) else s

def normalize_phoneish_fields(doc, method=None):
    """
    Strip whitespace from phone-like fields on CRM Lead.
    Runs on CRM Lead.before_save. Idempotent.
    """
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
