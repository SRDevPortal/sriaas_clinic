# apps/sriaas_clinic/sriaas_clinic/api/crm_lead_field_guard.py
from __future__ import annotations
import frappe

TL = "Team Leader"
AG = "Agent"

# Locked after the first save for normal users
ALWAYS_LOCK = {"source", "sr_lead_pipeline", "mobile_no"}
# Agents can never change this
AGENT_LOCK = {"lead_owner"}

PRIVILEGED_USERS = {"Administrator"}
PRIVILEGED_ROLES = {"System Manager"}

def _roles(user: str) -> set[str]:
    # Normalize to a set of role names
    try:
        return set(frappe.get_roles(user) or [])
    except Exception:
        return set()

def _is_privileged(user: str) -> bool:
    # 1) explicit usernames
    if user in PRIVILEGED_USERS:
        return True
    # 2) role-based
    return bool(_roles(user) & PRIVILEGED_ROLES)

def _has_role(user: str, role: str) -> bool:
    return role in _roles(user)

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

    # Programmatic bypass for scripts/migrations
    if getattr(frappe.flags, "sr_bypass_field_guard", False):
        return

    user = frappe.session.user or "Guest"

    # ---- Absolute bypass for Admin / System Manager ----
    # Put this BEFORE any other checks.
    if _is_privileged(user):
        return

    is_tl = _has_role(user, TL)
    is_agent = _has_role(user, AG)

    blocked: set[str] = set()

    # 1) Locked fields: TL can set only on INSERT; later edits blocked for everyone
    for f in ALWAYS_LOCK:
        if _changed(doc, f):
            if doc.is_new():
                if not is_tl:
                    blocked.add(f)        # agents/others can't set on create
            else:
                blocked.add(f)            # no edits after first save

    # 2) Agents can never change lead_owner
    if is_agent and _changed(doc, "lead_owner"):
        blocked.add("lead_owner")

    if blocked:
        frappe.throw(
            "You are not allowed to change: " + ", ".join(sorted(blocked)),
            title="Not permitted",
        )
