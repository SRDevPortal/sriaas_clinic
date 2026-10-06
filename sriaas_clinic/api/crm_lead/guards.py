# sriaas_clinic/api/crm_lead/guards.py
# Field-level protection + role helpers for CRM Lead

from __future__ import annotations
import frappe

from sriaas_clinic.api.crm_lead.config import REF_DOCTYPE, get_config, get_locked_fields

def _roles(user: str) -> set[str]:
    try:
        return set(frappe.get_roles(user) or [])
    except Exception:
        return set()


def _is_privileged(user: str) -> bool:
    from sriaas_role_permissions.api.roles import is_privileged

    return is_privileged(user, REF_DOCTYPE)


def _has_team_leader_role(user: str) -> bool:
    from sriaas_role_permissions.api.roles import has_team_leader_role

    return has_team_leader_role(user, REF_DOCTYPE)


def _has_agent_role(user: str) -> bool:
    from sriaas_role_permissions.api.roles import has_agent_role

    return has_agent_role(user, REF_DOCTYPE)


def _changed(doc, field: str) -> bool:
    """Did this field actually change? (on insert: treat non-empty as change)"""
    if doc.is_new():
        val = doc.get(field)
        return val not in (None, "", [])
    prev = frappe.db.get_value(doc.doctype, doc.name, field)
    return (doc.get(field) or "") != (prev or "")


def guard_restricted_fields(doc, method=None):
    # Only protect CRM Lead
    config = get_config()
    if doc.doctype != config.ref_doctype:
        return

    # programmatic bypass (patches, normalizers, imports)
    if getattr(frappe.flags, "sr_bypass_field_guard", False):
        return

    user = frappe.session.user or "Guest"

    # ---- Absolute bypass for Admin / System Manager ----
    # Unrestricted for Admin/System Manager
    if _is_privileged(user):
        return

    is_tl = _has_team_leader_role(user)
    is_agent = _has_agent_role(user)
    locked_fields = get_locked_fields()
    lock_after_insert = locked_fields["lock_after_insert"]
    leaders_can_change = locked_fields["leaders_can_change"]
    agent_always_lock = locked_fields["agent_always_lock"]

    blocked: set[str] = set()

    # Locked fields:
    # - TL can set lock-after-insert fields on insert.
    # - TL can edit fields explicitly marked Leaders Can Change.
    # - Agents remain blocked for lock-after-insert fields.
    for f in lock_after_insert:
        if _changed(doc, f):
            if is_tl and (doc.is_new() or f in leaders_can_change):
                continue
            blocked.add(f)

    for f in leaders_can_change - lock_after_insert:
        if _changed(doc, f):
            if not is_tl:
                blocked.add(f)

    # Agents cannot change lead_owner
    for f in agent_always_lock:
        if is_agent and _changed(doc, f):
            blocked.add(f)

    if blocked:
        frappe.throw(
            "You are not allowed to change: " + ", ".join(sorted(blocked)),
            title="Not permitted",
        )
