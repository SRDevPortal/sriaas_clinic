# sriaas_clinic/api/patient.py
import frappe
import re

# ----------------------------
# A) Patient ID auto-generator
# ----------------------------
def _dept_prefix(doc) -> str:
    """
    Use first 4 uppercase chars of sr_medical_department as prefix.
    e.g., "Cardiology" -> "CARD", "Dermatology" -> "DERM"
    """
    md = (doc.get("sr_medical_department") or "").strip()
    return md[:4].upper()

def set_sr_patient_id(doc, method=None):
    # Respect manual entry (e.g., data import)
    if doc.get("sr_patient_id"):
        return

    # Require department (adjust/remove if optional)
    if not doc.get("sr_medical_department"):
        frappe.throw("Please select a Medical Department to auto-generate Patient ID.")

    prefix = _dept_prefix(doc)         # e.g., "CARD"
    start_idx = len(prefix) + 1        # numeric part right after the prefix

    # Find largest existing number for this prefix (no padding)
    max_row = frappe.db.sql(
        """
        SELECT COALESCE(MAX(CAST(SUBSTRING(sr_patient_id, %s) AS SIGNED)), 0) AS max_n
        FROM `tabPatient`
        WHERE sr_patient_id LIKE %s
        """,
        (start_idx, f"{prefix}%"),
        as_dict=True,
    )
    last_num = int(max_row[0].max_n if max_row else 0)

    # Increment until free (handles rare races)
    while True:
        last_num += 1
        candidate = f"{prefix}{last_num}"   # CARD1, DERM5, ...
        if not frappe.db.exists("Patient", {"sr_patient_id": candidate}):
            doc.sr_patient_id = candidate
            break

# -------------------------------------------
# B) Phone-like fields whitespace normalizer
# -------------------------------------------
def _clean_spaces(s: str) -> str:
    # remove all whitespace (space/tab/newline)
    return ''.join(s.split())

def normalize_phoneish_fields(doc, method=None):
    CANDIDATE_FIELDS = (
        "mobile", "mobile_no", "phone", "phone_no",
        "whatsapp_no", "alternate_phone",
        "sr_mobile_no", "sr_whatsapp_no",
    )
    for field in CANDIDATE_FIELDS:
        val = doc.get(field)
        if isinstance(val, str):
            cleaned = _clean_spaces(val)
            if cleaned != val:
                doc.set(field, cleaned)  # in before_save, no extra DB hit

# -------------------------------------------------------
# C) Follow-up fields: day cycler + last-digit assignment
# -------------------------------------------------------
# We’re cycling Monday through Saturday (no Sunday)
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat")

def assign_followup_day(doc, method=None):
    if doc.get("sr_followup_day"):
        return
    total = frappe.db.count("Patient")   # includes this new row
    idx = (total - 1) % len(DAYS)
    doc.db_set("sr_followup_day", DAYS[idx], update_modified=False)

def set_followup_last_digit(doc, method=None):
    text = (doc.get("sr_patient_id") or doc.name or "").strip()
    last_digit = "0"
    for ch in text:
        if "0" <= ch <= "9":
            last_digit = ch
    if doc.get("sr_followup_id") != last_digit:
        doc.db_set("sr_followup_id", last_digit, update_modified=False)
