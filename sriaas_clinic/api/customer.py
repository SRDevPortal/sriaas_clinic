# sriaas_clinic/api/customer.py
import frappe

PREFIX = "CUST-"

# ----------------------------
# A) Customer ID auto-generator
# ----------------------------
def set_sr_customer_id(doc, method=None):
    if doc.get("sr_customer_id"):
        return

    max_row = frappe.db.sql(
        """
        SELECT COALESCE(MAX(CAST(SUBSTRING(sr_customer_id, %s) AS SIGNED)), 0) AS max_n
        FROM `tabCustomer`
        WHERE sr_customer_id LIKE %s
        """,
        (len(PREFIX) + 1, f"{PREFIX}%"),
        as_dict=True,
    )
    last_num = int(max_row[0].max_n if max_row else 0)

    while True:
        last_num += 1
        candidate = f"{PREFIX}{last_num}"          # CUST-1, CUST-2, ...
        if not frappe.db.exists("Customer", {"sr_customer_id": candidate}):
            doc.sr_customer_id = candidate
            break

# -------------------------------------------
# B) Phone-like fields whitespace normalizer
# -------------------------------------------
def _clean_spaces(s: str) -> str:
    return ''.join(s.split()) if isinstance(s, str) else s

def normalize_phoneish_fields(doc, method=None):
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
            doc.set(field, cleaned)  # before_save: no extra DB write
