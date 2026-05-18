# sriaas_clinic/api/crm_lead/access.py
# Visibility + Permissions + Owner-restore for CRM Lead

from __future__ import annotations
import frappe

AGENT_ROLE = "Agent"
TL_ROLE = "Team Leader"
LEAD_DOCTYPE = "CRM Lead"
TEAM_LEADER_FIELD = "sr_reports_to_team_leader"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_role(user: str, role: str) -> bool:
    return role in frappe.get_roles(user)


def _is_super(user: str) -> bool:
    return user == "Administrator" or _has_role(user, "System Manager")


def _reports_to_team_leader(user: str) -> str | None:
    if not frappe.db.has_column("User", TEAM_LEADER_FIELD):
        return None
    return frappe.db.get_value("User", user, TEAM_LEADER_FIELD)


def _is_effective_team_leader(user: str) -> bool:
    return _has_role(user, TL_ROLE) and not _reports_to_team_leader(user)


def _lead_owner_sql_for_team(user: str) -> str:
    owners = [user]

    if frappe.db.has_column("User", TEAM_LEADER_FIELD):
        owners.extend(
            frappe.get_all(
                "User",
                filters={TEAM_LEADER_FIELD: user, "enabled": 1},
                pluck="name",
            )
        )

    owners = sorted(set(owner for owner in owners if owner))
    if not owners:
        return "1=0"

    esc = ", ".join(frappe.db.escape(owner) for owner in owners)
    return f"`tabCRM Lead`.`lead_owner` IN ({esc})"


def _team_owner_values(user: str) -> set[str]:
    owners = {user}

    if frappe.db.has_column("User", TEAM_LEADER_FIELD):
        owners.update(
            frappe.get_all(
                "User",
                filters={TEAM_LEADER_FIELD: user, "enabled": 1},
                pluck="name",
            )
            or []
        )

    return {owner for owner in owners if owner}


def _allowed_pipelines(user: str) -> set[str]:
    from frappe.core.doctype.user_permission.user_permission import get_user_permissions

    perms = get_user_permissions(user) or {}
    raw = perms.get("SR Lead Pipeline") or []

    values = set()
    for v in raw:
        if isinstance(v, str):
            values.add(v)
        elif isinstance(v, dict):
            values.add(v.get("doc") or v.get("value") or v.get("name"))

    values.discard("")
    values.discard(None)
    return values


def _allowed_pipelines_sql(user: str, deny_if_missing: bool = True) -> str:
    """
    Restrict pipelines using User Permission (Allow = 'SR Lead Pipeline')
    Used ONLY for permission_query_conditions (SQL context)
    """
    values = sorted(_allowed_pipelines(user))
    if not values:
        return "1=0" if deny_if_missing else "1=1"

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

    # Team Leader: self + direct team members. If the TL has explicit
    # pipeline user permissions, apply those too.
    if _is_effective_team_leader(user):
        owner_cond = _lead_owner_sql_for_team(user)
        pipeline_cond = _allowed_pipelines_sql(user, deny_if_missing=False)
        return f"({owner_cond}) AND ({pipeline_cond})"

    # Agent: only lead_owner + allowed pipeline
    if _has_role(user, AGENT_ROLE) or _reports_to_team_leader(user):
        # lead_owner is the authoritative visibility field. ToDo assignments
        # are UI/task helpers and can drift independently.
        owner_cond = f"`tabCRM Lead`.`lead_owner`={frappe.db.escape(user)}"
        pipeline_cond = _allowed_pipelines_sql(user)
        return f"({owner_cond}) AND ({pipeline_cond})"

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

    # Team Leader: self + direct team members, optionally narrowed by pipeline
    if _is_effective_team_leader(user):
        if getattr(doc, "lead_owner", None) not in _team_owner_values(user):
            return False

        allowed = _allowed_pipelines(user)
        if allowed:
            return getattr(doc, "sr_lead_pipeline", None) in allowed

        return True

    # Agent: must be lead_owner + pipeline allowed
    if _has_role(user, AGENT_ROLE) or _reports_to_team_leader(user):
        if getattr(doc, "lead_owner", None) != user:
            return False

        allowed = _allowed_pipelines(user)
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
