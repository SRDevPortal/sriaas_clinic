# apps/sriaas_clinic/sriaas_clinic/api/crm_lead_field_guard.py
from __future__ import annotations
import frappe

TL = "Team Leader"
AG = "Agent"

# These 3 become read-only after the first save for normal users
ALWAYS_LOCK = {"source", "sr_lead_pipeline", "mobile_no"}
# Agents can never change this
AGENT_LOCK  = {"lead_owner"}

PRIVILEGED_USERS = {"Administrator"}
PRIVILEGED_ROLES = {"System Manager"}

def _has_role(user: str, role: str) -> bool:
    return role in frappe.get_roles(user)

def _is_privileged(user: str) -> bool:
    if user in PRIVILEGED_USERS:
        return True
    roles = set(frappe.get_roles(user))
    return bool(roles & PRIVILEGED_ROLES)

def _changed(doc, field: str) -> bool:
    """Did this field actually change? (on insert: treat non-empty as change)"""
    if doc.is_new():
        val = doc.get(field)
        return val not in (None, "", [])  # treat set values as 'changed' on insert
    prev = frappe.db.get_value(doc.doctype, doc.name, field)
    return (doc.get(field) or "") != (prev or "")

def guard_restricted_fields(doc, method=None):
    # Only protect CRM Lead
    if doc.doctype != "CRM Lead":
        return

    # Allow programmatic bypass (patches, data loads, etc.)
    if getattr(frappe.flags, "sr_bypass_field_guard", False):
        return

    user = frappe.session.user

    # ---- BYPASS for Admin / System Manager ----
    if _is_privileged(user):
        return

    is_tl = _has_role(user, TL)
    is_agent = _has_role(user, AG)

    blocked = set()

    # 1) For the 3 locked fields:
    #    - Team Leader can set them only on INSERT
    #    - Everyone else blocked on INSERT
    #    - After first save, blocked for everyone (except privileged bypass above)
    for f in ALWAYS_LOCK:
        if _changed(doc, f):
            if doc.is_new():
                if not is_tl:
                    blocked.add(f)
            else:
                blocked.add(f)

    # 2) Agents cannot change lead_owner ever
    if is_agent and _changed(doc, "lead_owner"):
        blocked.add("lead_owner")

    if blocked:
        frappe.throw(
            "You are not allowed to change: " + ", ".join(sorted(blocked)),
            title="Not permitted",
        )
