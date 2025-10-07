# apps/sriaas_clinic/sriaas_clinic/api/crm_lead_visibility.py
from __future__ import annotations
import frappe
from typing import Optional

LEAD_DT = "CRM Lead"
BYPASS_ROLES = {"System Manager", "Team Leader"}  # these can see everything

def _user_bypasses(user: str) -> bool:
    if (user or "").lower() == "administrator":
        return True
    roles = set(frappe.get_roles(user))
    return bool(BYPASS_ROLES & roles)

def get_permission_query_conditions(user: Optional[str] = None) -> str:
    """
    Agents: only leads that are assigned to them (via ToDo assignment).
    Team Leaders/System Managers: unrestricted.
    """
    user = user or frappe.session.user
    if _user_bypasses(user):
        return ""

    # Assigned means there's a ToDo row pointing to this Lead
    # Note: we intentionally do NOT also allow owner=user
    # to strictly match "Agent can only view the assigned lead".
    return f"""
        exists (
          select 1 from `tabToDo` t
          where t.reference_type = '{LEAD_DT}'
            and t.reference_name = `tab{LEAD_DT}`.`name`
            and t.allocated_to = {frappe.db.escape(user)}
            and ifnull(t.status, '') != 'Cancelled'
        )
    """

def has_permission(doc, user: Optional[str] = None) -> bool:
    user = user or frappe.session.user
    if _user_bypasses(user):
        return True

    # Allow if there is a live assignment for this user on this Lead
    exists = frappe.db.exists(
        "ToDo",
        {
            "reference_type": LEAD_DT,
            "reference_name": doc.name,
            "allocated_to": user,
        },
    )
    return bool(exists)
