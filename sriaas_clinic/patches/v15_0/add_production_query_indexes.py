from __future__ import annotations

import frappe


INDEX_DEFINITIONS = (
    (
        "Patient Encounter",
        ("sr_source_crm_lead", "modified"),
        "idx_pe_source_lead_modified",
    ),
    ("Patient Encounter", ("owner", "modified"), "idx_pe_owner_modified"),
    ("CRM Lead", ("mobile_no", "modified"), "idx_crm_mobile_modified"),
    ("CRM Lead", ("phone", "modified"), "idx_crm_phone_modified"),
    (
        "CRM Lead",
        ("vobiz_mobile_last10", "modified"),
        "idx_crm_vobiz_mobile_modified",
    ),
    (
        "CRM Lead",
        ("vobiz_phone_last10", "modified"),
        "idx_crm_vobiz_phone_modified",
    ),
    (
        "CRM Lead",
        ("vobiz_whatsapp_last10", "modified"),
        "idx_crm_vobiz_whatsapp_modified",
    ),
    ("Route History", ("user", "route"), "idx_route_user_route"),
    (
        "Notification Log",
        ("for_user", "modified"),
        "idx_notification_user_modified",
    ),
    (
        "Sales Invoice",
        ("patient", "docstatus", "posting_date"),
        "idx_si_patient_status_posting",
    ),
)


def execute() -> None:
    """Persist the composite indexes validated against the production slow log."""
    previous = getattr(frappe.flags, "in_migrate", False)
    frappe.flags.in_migrate = True
    try:
        for doctype, fields, index_name in INDEX_DEFINITIONS:
            if not _has_doctype_and_columns(doctype, fields):
                continue
            frappe.db.add_index(
                doctype,
                list(fields),
                index_name=index_name,
            )
    finally:
        frappe.flags.in_migrate = previous


def _has_doctype_and_columns(doctype: str, fields: tuple[str, ...]) -> bool:
    if not frappe.db.exists("DocType", doctype):
        return False
    return all(frappe.db.has_column(doctype, fieldname) for fieldname in fields)
