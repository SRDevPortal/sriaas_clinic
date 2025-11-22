# sriaas_clinic/api/patient.py
import re
import frappe
from frappe.model.naming import make_autoname

# Match series: HLC-PAT-2025-000001
_SERIES_RX = re.compile(r"^HLC-PAT-\d{4}-\d+$")

# ----------------------------------
# small helper: set_created_by_agent
# ----------------------------------
def set_created_by_agent(doc, method):
    """Populate created_by_agent on insert only (so edits don't override)."""
    if not getattr(doc, "created_by_agent", None):
        doc.created_by_agent = frappe.session.user

# ----------------------------
# A) Patient ID auto-generator
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


# def set_sr_patient_id(doc, method=None):
#     """
#     Auto-generate Patient ID in the format:
#     SR1000, SR1001, SR1002, ...
#     Always prefix with 'SR', start numbering from 1000.
#     """

#     # If user manually set it, do not override
#     if doc.get("sr_patient_id"):
#         return

#     prefix = "SR"
#     start_number = 1000
#     prefix_like = f"{prefix}%"

#     # Numeric part begins after "SR" → which is index 3 in SQL (1-based)
#     numeric_start_pos = len(prefix) + 1   # = 3

#     # Find the highest existing numeric part for IDs starting with "SR"
#     max_row = frappe.db.sql(
#         """
#         SELECT COALESCE(MAX(CAST(SUBSTRING(sr_patient_id, %s) AS SIGNED)), 0) AS max_n
#         FROM `tabPatient`
#         WHERE sr_patient_id LIKE %s
#         """,
#         (numeric_start_pos, prefix_like),
#         as_dict=True,
#     )

#     last_num = int(max_row[0].max_n or 0)

#     # If no record exists, begin from 999 so next becomes 1000
#     if last_num < start_number:
#         last_num = start_number - 1

#     # Generate next available number
#     while True:
#         last_num += 1
#         candidate = f"{prefix}{last_num}"
#         if not frappe.db.exists("Patient", {"sr_patient_id": candidate}):
#             doc.sr_patient_id = candidate
#             break


def set_sr_patient_id(doc, method=None):
    """
    Auto-generate Patient ID using Company.abbr as prefix.
    Example:
      If Company.abbr = 'SR' -> SR1000, SR1001, ...
      If Company.abbr = 'HC' -> HC1000, HC1001, ...
    """

    # Do not override manual entry
    if doc.get("sr_patient_id"):
        return

    # Get company abbr safely
    company_abbr = None
    if doc.get("company"):
        try:
            company_abbr = frappe.db.get_value("Company", doc.company, "abbr")
        except Exception:
            company_abbr = None

    prefix = (company_abbr or "SR").strip().upper()

    # Starting number
    start_number = 1000

    prefix_like = f"{prefix}%"
    numeric_start_pos = len(prefix) + 1  # numeric part starts after prefix

    # Get highest existing number under this prefix
    max_row = frappe.db.sql(
        """
        SELECT COALESCE(MAX(CAST(SUBSTRING(sr_patient_id, %s) AS SIGNED)), 0) AS max_n
        FROM `tabPatient`
        WHERE sr_patient_id LIKE %s
        """,
        (numeric_start_pos, prefix_like),
        as_dict=True,
    )

    last_num = int(max_row[0].max_n or 0)

    # ensure at least starting number
    if last_num < start_number:
        last_num = start_number - 1

    # Find next free ID
    while True:
        last_num += 1
        candidate = f"{prefix}{last_num}"
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

def force_patient_series(doc, method=None):
    """
    Runs during set_new_name(). Ensure Patient uses naming_series.
    If a name was passed (via API/import) and it doesn't match our series,
    overwrite it with the correct series-based name.
    """
    # keep if already correct
    if doc.name and _SERIES_RX.match(doc.name):
        return

    series = getattr(doc, "naming_series", None) or "HLC-PAT-.YYYY.-"
    doc.name = make_autoname(series)

    # optional: log once to confirm it ran
    frappe.logger().info(f"[Patient] series name -> {doc.name}")

# ---------------------------------
# D) Unique mobile number validator
# ---------------------------------
def validate_unique_contact_mobile(doc, method):
    mobile = (doc.mobile or "").strip()

    if not mobile:
        return

    # Search in Contact table
    existing = frappe.db.sql("""
        SELECT name 
        FROM `tabContact`
        WHERE mobile_no = %s
        OR name IN (
            SELECT parent FROM `tabContact Phone`
            WHERE phone = %s
        )
        LIMIT 1
    """, (mobile, mobile), as_dict=True)

    if existing:
        frappe.throw(
            f"A Contact with this mobile number already exists ({mobile}). "
            f"Patient creation is not allowed for duplicate mobile numbers."
        )
