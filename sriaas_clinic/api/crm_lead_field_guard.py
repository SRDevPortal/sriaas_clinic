# apps/sriaas_clinic/sriaas_clinic/api/crm_lead_field_guard.py
from __future__ import annotations
import frappe

TL_ROLE = "Team Leader"
AGENT_ROLE = "Agent"

# never editable by anyone (by requirement)
RESTRICTED_ALWAYS = {"source", "sr_lead_pipeline", "mobile_no"}
# additional fields agents can't change
RESTRICTED_FOR_AGENT = {"lead_owner"}

def _has_role(user: str, role: str) -> bool:
    return role in frappe.get_roles(user)

def _changed(doc, field: str) -> bool:
    if doc.is_new():
        return False
    old = frappe.db.get_value(doc.doctype, doc.name, field)
    return (doc.get(field) or "") != (old or "")

def guard_restricted_fields(doc, method=None):
    """Block edits to specific fields based on role (runs on validate)."""
    if doc.doctype != "CRM Lead":
        return

    user = frappe.session.user
    blocked = set(RESTRICTED_ALWAYS)
    if _has_role(user, AGENT_ROLE):
        blocked |= RESTRICTED_FOR_AGENT

    touched = [f for f in blocked if _changed(doc, f)]
    if touched:
        frappe.throw(
            "You are not allowed to change: " + ", ".join(sorted(touched)),
            title="Not permitted",
        )
