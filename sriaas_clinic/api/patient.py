# sriaas_clinic/api/patient.py
import re
import frappe
from frappe.model.naming import make_autoname

# --------------------------------
# A) Set naming_series for patient
# --------------------------------
def set_patient_series(doc, method=None):
    series = doc.get("naming_series") or "HLC-PAT-.YYYY.-"
    prefix = series.replace(".YYYY.-", "")

    # keep if already correct
    if doc.name and doc.name.startswith(prefix):
        return
    
    doc.name = make_autoname(series)


# ------------------------------------------
# B) Phone-like fields whitespace normalizer
# ------------------------------------------
def normalize_indian_mobile(value: str | None) -> str | None:
    if not value:
        return None

    # keep digits only
    digits = "".join(ch for ch in value if ch.isdigit())

    # take last 10 digits
    if len(digits) < 10:
        return None

    return digits[-10:]


def normalize_patient_contact_numbers(doc, method=None):
    FIELDS = (
        "mobile", "mobile_no", "phone",
        "whatsapp_no", "alternate_phone",
        "sr_mobile_no", "sr_whatsapp_no",
    )

    for field in FIELDS:
        raw = doc.get(field)
        normalized = normalize_indian_mobile(raw)

        if normalized:
            doc.set(field, normalized)
        elif raw:
            # invalid number entered
            frappe.throw(f"Invalid phone number entered in {field}")


# ----------------------------------
# C) Unique mobile / phone validator
# ----------------------------------
def validate_unique_contact_mobile(doc, method):
    fields = ("mobile", "mobile_no", "phone")

    numbers = {
        normalize_indian_mobile(doc.get(f))
        for f in fields
        if doc.get(f)
    }

    numbers.discard(None)

    for num in numbers:
        # Check Patient
        if frappe.db.get_value("Patient", {"mobile": num}, "name"):
            frappe.throw(f"Patient already exists with mobile number {num}")

        # Check Contact
        if frappe.db.sql("""
            SELECT 1 FROM `tabContact`
            WHERE REPLACE(mobile_no, ' ', '') LIKE %s
               OR REPLACE(phone, ' ', '') LIKE %s
            LIMIT 1
        """, (f"%{num}", f"%{num}")):
            frappe.throw(
                f"Contact already exists with mobile number {num}"
            )


# ----------------------------
# D) Patient ID auto-generator
# ----------------------------
def set_patient_id(doc, method=None):
    """
    Auto-generate Patient ID using Company.abbr as prefix.
    Example:
      If Company.abbr = 'SR' -> SR1000, SR1001, ...
      If Company.abbr = 'BHPL' -> BHPL1000, BHPL1001, ...
    """

    if doc.get("sr_patient_id"):
        return
    
    # Patient has NO company field → use default
    company = frappe.defaults.get_global_default("company")

    if not company:
        frappe.throw("Company is required to generate Patient ID")

    company_abbr = frappe.db.get_value("Company", company, "abbr")

    if not company_abbr:
        frappe.throw(f"Company Abbr not found for {company}")

    prefix = company_abbr.upper()
    start_number = 1000

    prefix_like = f"{prefix}%"
    numeric_start_pos = len(prefix) + 1

    max_row = frappe.db.sql(
        """
        SELECT COALESCE(MAX(CAST(SUBSTRING(sr_patient_id, %s) AS UNSIGNED)), 0) AS max_n
        FROM `tabPatient`
        WHERE sr_patient_id LIKE %s
        """,
        (numeric_start_pos, prefix_like),
        as_dict=True,
    )

    last_num = int(max_row[0].max_n or 0)
    if last_num < start_number:
        last_num = start_number - 1

    while True:
        last_num += 1
        candidate = f"{prefix}{last_num}"
        if not frappe.db.exists("Patient", {"sr_patient_id": candidate}):
            doc.sr_patient_id = candidate
            break


# -----------------------
# E) Set created_by_agent
# -----------------------
def set_patient_creator(doc, method):
    """Populate created_by_agent on insert only."""
    if not getattr(doc, "created_by_agent", None):
        doc.created_by_agent = frappe.session.user or "Administrator"


# -----------------------------------------------------------------
# F) Follow-up fields: followup id + followup day cycler assignment
# -----------------------------------------------------------------
def set_followup_id(doc, method=None):
    source = (
        doc.get("sr_practo_id")
        or doc.get("sr_patient_id")
    )

    if not source:
        # Explicitly clear the field if nothing is available
        if doc.get("sr_followup_id"):
            doc.db_set("sr_followup_id", None, update_modified=False)
        return

    source = source.strip()

    last_digit = None
    for ch in source:
        if ch.isdigit():
            last_digit = ch

    if doc.get("sr_followup_id") != last_digit:
        doc.db_set("sr_followup_id", last_digit, update_modified=False)


DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat")

def set_followup_day(doc, method=None):
    if not doc.get("sr_followup_id") or doc.get("sr_followup_day"):
        return

    digit = int(doc.sr_followup_id)
    day = DAYS[digit % len(DAYS)]
    doc.db_set("sr_followup_day", day, update_modified=False)
