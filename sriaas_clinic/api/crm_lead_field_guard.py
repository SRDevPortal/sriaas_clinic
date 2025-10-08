# apps/sriaas_clinic/sriaas_clinic/api/crm_lead_field_guard.py
from __future__ import annotations
import frappe

TL = "Team Leader"
AG = "Agent"

ALWAYS_LOCK = {"source", "sr_lead_pipeline", "mobile_no"}  # locked after first save
AGENT_LOCK  = {"lead_owner"}                                # agents never change

def _has_role(user, role): return role in frappe.get_roles(user)

def _changed(doc, field):
    if doc.is_new():   # let "create" path be decided below
        return field in doc.as_dict()  # any value present is considered a change on insert
    prev = frappe.db.get_value(doc.doctype, doc.name, field)
    return (doc.get(field) or "") != (prev or "")

def guard_restricted_fields(doc, method=None):
    if doc.doctype != "CRM Lead":
        return

    user = frappe.session.user
    is_tl = _has_role(user, TL)
    is_agent = _has_role(user, AG)

    blocked = set()

    # 1) For the three locked fields:
    #    - allow TL ONLY on insert
    #    - block everyone else or any later edits
    for f in ALWAYS_LOCK:
        if _changed(doc, f):
            if doc.is_new():
                if not is_tl:
                    blocked.add(f)       # agent or others cannot set on create
            else:
                blocked.add(f)           # no one edits after first save

    # 2) Agents cannot change lead_owner ever
    if is_agent and _changed(doc, "lead_owner"):
        blocked.add("lead_owner")

    if blocked:
        frappe.throw(
            "You are not allowed to change: " + ", ".join(sorted(blocked)),
            title="Not permitted",
        )
