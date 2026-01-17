# sriaas_clinic/api/patient.py
import re
import frappe
from frappe.model.naming import make_autoname

# Match series: HLC-PAT-2025-000001
# _SERIES_RX = re.compile(r"^HLC-PAT-\d{4}-\d+$")


# ---------------------------------
# A) Unique mobile / phone validator
# ---------------------------------
# def force_patient_series(doc, method=None):
#     """
#     Runs during set_new_name(). Ensure Patient uses naming_series.
#     If a name was passed (via API/import) and it doesn't match our series,
#     overwrite it with the correct series-based name.
#     """
#     # keep if already correct
#     if doc.name and _SERIES_RX.match(doc.name):
#         return

#     series = getattr(doc, "naming_series", None) or "HLC-PAT-.YYYY.-"
#     doc.name = make_autoname(series)

#     # optional: log once to confirm it ran
#     frappe.logger().info(f"[Patient] series name -> {doc.name}")

def force_patient_series(doc, method=None):
    series = doc.get("naming_series") or "HLC-PAT-.YYYY.-"
    prefix = series.replace(".YYYY.-", "")

    # keep if already correct
    if doc.name and doc.name.startswith(prefix):
        return
    
    doc.name = make_autoname(series)


# -------------------------------------------
# B) Phone-like fields whitespace normalizer
# -------------------------------------------
# def _clean_spaces(s: str) -> str:
#     # remove all whitespace (space/tab/newline)
#     return ''.join(s.split())


# def normalize_phoneish_fields(doc, method=None):
#     CANDIDATE_FIELDS = (
#         "mobile", "mobile_no", "phone", "phone_no",
#         "whatsapp_no", "alternate_phone",
#         "sr_mobile_no", "sr_whatsapp_no",
#     )
#     for field in CANDIDATE_FIELDS:
#         val = doc.get(field)
#         if isinstance(val, str):
#             cleaned = _clean_spaces(val)
#             if cleaned != val:
#                 doc.set(field, cleaned)  # in before_save, no extra DB hit


def normalize_indian_mobile(value: str | None) -> str | None:
    if not value:
        return None

    # keep digits only
    digits = "".join(ch for ch in value if ch.isdigit())

    # take last 10 digits
    if len(digits) < 10:
        return None

    return digits[-10:]


def normalize_phoneish_fields(doc, method=None):
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



# ---------------------------------
# C) Unique mobile / phone validator
# ---------------------------------
# def validate_unique_contact_mobile(doc, method):
#     """
#     Do not allow Patient creation if any of these fields already exist in Contact or Contact Phone:
#     - mobile, phone, mobile_no
#     """
#     fields = ("mobile", "phone", "mobile_no")
#     numbers = { (doc.get(f) or "").strip() for f in fields if doc.get(f) }

#     for num in numbers:
#         # Check Patient first
#         if frappe.db.get_value("Patient", {"mobile": num}, "name"):
#             frappe.throw(f"Patient already exists with mobile number {num}")

#         # Check Contact + Contact Phone
#         if frappe.db.sql("""
#             SELECT 1 FROM `tabContact`
#             WHERE mobile_no=%s OR phone=%s
#             OR name IN (
#                 SELECT parent FROM `tabContact Phone`
#                 WHERE phone=%s
#             )
#             LIMIT 1
#         """, (num, num, num)):
#             frappe.throw(
#                 f"A Contact already exists with phone number {num}"
#             )



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
# def _dept_prefix(doc) -> str:
#     """
#     Use first 4 uppercase chars of sr_medical_department as prefix.
#     e.g., "Cardiology" -> "CARD", "Dermatology" -> "DERM"
#     """
#     md = (doc.get("sr_medical_department") or "").strip()
#     return md[:4].upper()


# def set_sr_patient_id(doc, method=None):
#     # Respect manual entry (e.g., data import)
#     if doc.get("sr_patient_id"):
#         return

#     # Require department (adjust/remove if optional)
#     if not doc.get("sr_medical_department"):
#         frappe.throw("Please select a Medical Department to auto-generate Patient ID.")

#     prefix = _dept_prefix(doc)         # e.g., "CARD"
#     start_idx = len(prefix) + 1        # numeric part right after the prefix

#     # Find largest existing number for this prefix (no padding)
#     max_row = frappe.db.sql(
#         """
#         SELECT COALESCE(MAX(CAST(SUBSTRING(sr_patient_id, %s) AS SIGNED)), 0) AS max_n
#         FROM `tabPatient`
#         WHERE sr_patient_id LIKE %s
#         """,
#         (start_idx, f"{prefix}%"),
#         as_dict=True,
#     )
#     last_num = int(max_row[0].max_n if max_row else 0)

#     # Increment until free (handles rare races)
#     while True:
#         last_num += 1
#         candidate = f"{prefix}{last_num}"   # CARD1, DERM5, ...
#         if not frappe.db.exists("Patient", {"sr_patient_id": candidate}):
#             doc.sr_patient_id = candidate
#             break


def set_sr_patient_id(doc, method=None):
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


# -------------------------------------------
# E) created_by_agent
# -------------------------------------------
def set_created_by_agent(doc, method):
    """Populate created_by_agent on insert only (so edits don't override)."""
    if not getattr(doc, "created_by_agent", None):
        doc.created_by_agent = frappe.session.user


# -------------------------------------------------------
# F) Follow-up fields: day cycler + last-digit assignment
# -------------------------------------------------------
# def set_followup_last_digit(doc, method=None):
#     text = (doc.get("sr_patient_id") or doc.name or "").strip()
#     last_digit = "0"
#     for ch in text:
#         if "0" <= ch <= "9":
#             last_digit = ch
#     if doc.get("sr_followup_id") != last_digit:
#         doc.db_set("sr_followup_id", last_digit, update_modified=False)

def set_followup_last_digit(doc, method=None):
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


# We’re cycling Monday through Saturday (no Sunday)
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat")

# def assign_followup_day(doc, method=None):
#     if doc.get("sr_followup_day"):
#         return

#     digit = int(doc.get("sr_followup_id") or 0)
#     day = DAYS[digit % len(DAYS)]
#     doc.db_set("sr_followup_day", day, update_modified=False)


def assign_followup_day(doc, method=None):
    if not doc.get("sr_followup_id") or doc.get("sr_followup_day"):
        return

    digit = int(doc.sr_followup_id)
    day = DAYS[digit % len(DAYS)]
    doc.db_set("sr_followup_day", day, update_modified=False)
