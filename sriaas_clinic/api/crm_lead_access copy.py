# apps/sriaas_clinic/sriaas_clinic/api/crm_lead_access.py
from __future__ import annotations
import frappe

AGENT_ROLE   = "Agent"
TL_ROLE      = "Team Leader"
LEAD_DOCTYPE = "CRM Lead"


# ------------------------------ helpers ---------------------------------

def _has_role(user: str, role: str) -> bool:
    return role in frappe.get_roles(user)

def _current_assignees(lead_name: str) -> set[str]:
    """Return users with an OPEN ToDo assignment on this lead."""
    rows = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": LEAD_DOCTYPE,
            "reference_name": lead_name,
            "status": "Open",
        },
        pluck="allocated_to",
    )
    return set(rows or [])

def _allowed_pipelines_sql(user: str) -> str:
    """
    Build a SQL clause restricting to pipelines the user is allowed via
    User Permission (Allow = 'SR Lead Pipeline').
    Handles both legacy (list[str]) and new (list[dict]) shapes.
    """
    from frappe.core.doctype.user_permission.user_permission import get_user_permissions
    perms = get_user_permissions(user) or {}
    raw_vals = perms.get("SR Lead Pipeline") or []

    # Normalize to list[str]
    values: list[str] = []
    for v in raw_vals:
        if isinstance(v, str):
            values.append(v)
        elif isinstance(v, dict):
            # common keys seen across versions
            values.append(v.get("doc") or v.get("value") or v.get("name") or "")
    values = [x for x in values if x]

    if not values:
        return "1=0"  # no permission rows → see nothing

    esc_list = ", ".join(frappe.db.escape(v) for v in values)
    return f"`tabCRM Lead`.`sr_lead_pipeline` in ({esc_list})"


# ---------------------- permission query condition ----------------------

def crm_lead_pqc(user: str) -> str:
    """
    TL: no restriction.
    Agent: MUST be assigned (open ToDo) AND pipeline must be allowed by User Permission.
    Others: block.
    """
    user = user or frappe.session.user

    if _has_role(user, TL_ROLE):
        return ""

    if _has_role(user, AGENT_ROLE):
        assignment_cond = (
            "exists (select 1 from `tabToDo` t "
            "where t.reference_type='CRM Lead' "
            "and t.reference_name=`tabCRM Lead`.name "
            "and t.status='Open' "
            f"and t.allocated_to={frappe.db.escape(user)})"
        )
        return f"({assignment_cond}) and ({_allowed_pipelines_sql(user)})"

    return "1=0"


# --------------------------- has_permission -----------------------------

def crm_lead_has_permission(doc, user: str) -> bool:
    """
    Team Leader: always True.
    Agent: True only when:
      1) user is currently assigned (open ToDo), and
      2) lead's pipeline is allowed by User Permission (Allow = 'SR Lead Pipeline').
         If the agent has no 'SR Lead Pipeline' permissions at all, deny.
    Others: False.
    """
    if _has_role(user, TL_ROLE):
        return True

    if _has_role(user, AGENT_ROLE):
        # must be assigned
        if user not in _current_assignees(doc.name):
            return False

        # must have pipeline permission AND doc pipeline must be in the allowed set
        from frappe.core.doctype.user_permission.user_permission import get_user_permissions
        perms = get_user_permissions(user) or {}
        raw_vals = perms.get("SR Lead Pipeline") or []

        # normalize to a clean set[str]
        allowed: set[str] = set()
        for v in raw_vals:
            if isinstance(v, str):
                allowed.add(v)
            elif isinstance(v, dict):
                # different frappe versions/shapes
                allowed.add(v.get("doc") or v.get("value") or v.get("name") or "")

        allowed.discard("")

        # no user-permission rows -> deny
        if not allowed:
            return False

        pipeline = getattr(doc, "sr_lead_pipeline", None) or getattr(doc, "pipeline", None)
        return pipeline in allowed

    return False


# ----------------------- safe assign / unassign -------------------------

@frappe.whitelist()
def assign_lead(lead: str, user: str):
    """
    Assign a lead to a user via ToDo only (no DocShare).
    Use from a button or API. Honors ignore_permissions to let TL assign.
    """
    from frappe.desk.form.assign_to import add as assign_add
    assign_add(
        dict(assign_to=[user], doctype=LEAD_DOCTYPE, name=lead, description=""),
        ignore_permissions=True,
    )
    return {"status": "ok"}

@frappe.whitelist()
def unassign_lead(lead: str, user: str):
    """
    Remove an assignment (closes the ToDo). No shares involved.
    """
    from frappe.desk.form.assign_to import clear as assign_clear
    assign_clear(LEAD_DOCTYPE, lead, user=user)  # closes the ToDo for that user
    return {"status": "ok"}
