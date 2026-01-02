# sriaas_clinic/api/crm_lead/access.py
# Visibility + Permissions + Owner-restore for CRM Lead

from __future__ import annotations
import frappe

AGENT_ROLE = "Agent"
TL_ROLE = "Team Leader"
LEAD_DOCTYPE = "CRM Lead"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_role(user: str, role: str) -> bool:
    return role in frappe.get_roles(user)


def _is_super(user: str) -> bool:
    return user == "Administrator" or _has_role(user, "System Manager")


def _current_assignees(lead_name: str) -> set[str]:
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
    Restrict pipelines using User Permission (Allow = 'SR Lead Pipeline')
    Used ONLY for permission_query_conditions (SQL context)
    """
    from frappe.core.doctype.user_permission.user_permission import get_user_permissions

    perms = get_user_permissions(user) or {}
    raw = perms.get("SR Lead Pipeline") or []

    values: list[str] = []
    for v in raw:
        if isinstance(v, str):
            values.append(v)
        elif isinstance(v, dict):
            values.append(v.get("doc") or v.get("value") or v.get("name") or "")

    values = [v for v in values if v]
    if not values:
        return "1=0"  # deny all

    esc = ", ".join(frappe.db.escape(v) for v in values)
    return f"`tabCRM Lead`.`sr_lead_pipeline` IN ({esc})"


# ---------------------------------------------------------------------------
# Permission Query Condition (LIST / SEARCH / EXPORT)
# ---------------------------------------------------------------------------

def crm_lead_pqc(user: str) -> str:
    user = user or frappe.session.user

    # Admin / System Manager → everything
    if _is_super(user):
        return ""

    # Team Leader → everything
    if _has_role(user, TL_ROLE):
        return ""

    # Agent → ONLY assigned (open ToDo) + allowed pipeline
    if _has_role(user, AGENT_ROLE):
        assignment_cond = (
            "EXISTS ("
            "SELECT 1 FROM `tabToDo` t "
            "WHERE t.reference_type='CRM Lead' "
            "AND t.reference_name=`tabCRM Lead`.name "
            "AND t.status='Open' "
            f"AND t.allocated_to={frappe.db.escape(user)}"
            ")"
        )

        pipeline_cond = _allowed_pipelines_sql(user)
        return f"({assignment_cond}) AND ({pipeline_cond})"

    # Everyone else → nothing
    return "1=0"


# ---------------------------------------------------------------------------
# has_permission (OPEN / READ / WRITE)
# ---------------------------------------------------------------------------

def crm_lead_has_permission(doc, user: str | None = None, ptype: str | None = None) -> bool:
    user = user or frappe.session.user

    # Admin / System Manager
    if _is_super(user):
        return True

    # Team Leader
    if _has_role(user, TL_ROLE):
        return True

    # Agent → MUST be assigned + pipeline allowed
    if _has_role(user, AGENT_ROLE):
        if user not in _current_assignees(doc.name):
            return False

        from frappe.core.doctype.user_permission.user_permission import get_user_permissions
        raw = (get_user_permissions(user) or {}).get("SR Lead Pipeline") or []

        allowed = {
            v if isinstance(v, str)
            else (v.get("doc") or v.get("value") or v.get("name") or "")
            for v in raw
        }
        allowed.discard("")
        allowed.discard(None)

        if not allowed:
            return False

        pipeline = getattr(doc, "sr_lead_pipeline", None)
        if not pipeline:
            return False

        return pipeline in allowed

    return False


# ---------------------------------------------------------------------------
# Restore owner after unassign (conditional)
# ---------------------------------------------------------------------------

def restore_lead_owner_after_unassign(doc, method=None):
    """
    Restore lead_owner ONLY for system-driven unassigns.
    Explicit clears from controller set _sr_skip_owner_restore.
    """

    # 🚫 Explicit clear → do NOT restore owner
    if getattr(frappe.flags, "_sr_skip_owner_restore", False):
        frappe.flags._sr_skip_owner_restore = False
        frappe.flags._sr_preserve_lead_owner = None
        return

    data = getattr(frappe.flags, "_sr_preserve_lead_owner", None)
    if not data:
        return

    if doc.doctype != LEAD_DOCTYPE:
        return

    if doc.name != data.get("lead"):
        return

    if not doc.lead_owner:
        doc.db_set(
            "lead_owner",
            data.get("owner"),
            update_modified=False,
        )

    frappe.flags._sr_preserve_lead_owner = None
