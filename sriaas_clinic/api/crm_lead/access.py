# sriaas_clinic/api/crm_lead/access.py
# Visibility + Permissions + Owner-restore for CRM Lead

from __future__ import annotations
import frappe

from sriaas_clinic.api.crm_lead.config import REF_DOCTYPE, get_config, sql_column


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_privileged(user: str) -> bool:
    from sriaas_role_permissions.api.roles import is_privileged

    return is_privileged(user, REF_DOCTYPE)


def _has_team_leader_role(user: str) -> bool:
    from sriaas_role_permissions.api.roles import has_team_leader_role

    return has_team_leader_role(user, REF_DOCTYPE)


def _has_agent_role(user: str) -> bool:
    from sriaas_role_permissions.api.roles import has_agent_role

    return has_agent_role(user, REF_DOCTYPE)


def _reports_to_team_leader(user: str) -> str | None:
    if _has_team_doctype():
        rows = frappe.db.sql(
            """
            SELECT t.team_lead
            FROM `tabTeam User` tu
            INNER JOIN `tabTeam` t ON t.name = tu.parent
            WHERE tu.parenttype = 'Team'
              AND tu.user = %s
              AND tu.is_active = 1
              AND t.is_active = 1
              AND t.team_lead IS NOT NULL
              AND t.team_lead != ''
              AND t.team_lead != %s
            LIMIT 1
            """,
            (user, user),
            as_dict=True,
        )
        if rows:
            return rows[0].team_lead

    return None


def _is_effective_team_leader(user: str) -> bool:
    if not _has_team_leader_role(user):
        return False

    if _has_team_doctype():
        return bool(_managed_team_names(user))

    return not _reports_to_team_leader(user)


def _is_main_team_lead(user: str) -> bool:
    return bool(_teams_led_by(user))


def _is_assistant_team_lead(user: str) -> bool:
    if not _has_team_leader_role(user) or not _has_team_doctype():
        return False
    return bool(_teams_where_user_is_active_member(user) - _teams_led_by(user))


def _teams_led_by(user: str) -> set[str]:
    if not _has_team_doctype():
        return set()

    rows = frappe.get_all(
        "Team",
        filters={"team_lead": user, "is_active": 1},
        pluck="name",
    )
    return set(rows or [])


def _teams_where_user_is_active_member(user: str) -> set[str]:
    if not _has_team_doctype():
        return set()

    rows = frappe.db.sql(
        """
        SELECT DISTINCT t.name
        FROM `tabTeam User` tu
        INNER JOIN `tabTeam` t ON t.name = tu.parent
        WHERE tu.parenttype = 'Team'
          AND tu.user = %s
          AND tu.is_active = 1
          AND t.is_active = 1
        """,
        user,
        as_dict=True,
    )
    return {row.name for row in rows}


def _managed_team_names(user: str) -> set[str]:
    if not _has_team_doctype() or not _has_team_leader_role(user):
        return set()

    return _teams_led_by(user) | _teams_where_user_is_active_member(user)


def get_managed_team_users(user: str | None = None) -> list[str]:
    user = user or frappe.session.user
    if _is_privileged(user):
        return []
    if not _is_effective_team_leader(user):
        return []

    return sorted(_team_owner_values(user))


def _lead_owner_sql_for_team(user: str) -> str:
    config = get_config()
    owners = _team_owner_values(user)

    owners = sorted(set(owner for owner in owners if owner))
    if not owners:
        return "1=0"

    esc = ", ".join(frappe.db.escape(owner) for owner in owners)
    return f"{sql_column(config.owner_fieldname)} IN ({esc})"


def _blank_lead_owner_sql() -> str:
    owner_col = sql_column(get_config().owner_fieldname)
    return f"({owner_col} IS NULL OR {owner_col} = '')"


def _team_owner_values(user: str) -> set[str]:
    config = get_config()
    owners = {user}

    if _has_team_doctype():
        teams = _managed_team_names(user)
        if not teams:
            return owners

        esc_teams = ", ".join(frappe.db.escape(team) for team in sorted(teams))
        rows = frappe.db.sql(
            f"""
            SELECT DISTINCT tu.user
            FROM `tabTeam User` tu
            INNER JOIN `tabTeam` t ON t.name = tu.parent
            WHERE tu.parenttype = 'Team'
              AND t.name IN ({esc_teams})
              AND t.is_active = 1
              AND tu.is_active = 1
              AND tu.user IS NOT NULL
              AND tu.user != ''
            """,
            as_dict=True,
        )
        owners.update(row.user for row in rows)
        owners.update(
            frappe.get_all(
                "Team",
                filters={"name": ["in", list(teams)], "is_active": 1},
                pluck="team_lead",
            )
            or []
        )
    elif config.team_leader_fieldname and frappe.db.has_column("User", config.team_leader_fieldname):
        owners.update(
            frappe.get_all(
                "User",
                filters={config.team_leader_fieldname: user, "enabled": 1},
                pluck="name",
            )
            or []
        )

    return {owner for owner in owners if owner}


def _has_team_doctype() -> bool:
    return bool(
        frappe.db.exists("DocType", "Team")
        and frappe.db.exists("DocType", "Team User")
    )


def _allowed_pipelines(user: str) -> set[str]:
    from frappe.core.doctype.user_permission.user_permission import get_user_permissions

    pipeline_doctype = get_config().pipeline_doctype
    if not pipeline_doctype:
        return set()

    perms = get_user_permissions(user) or {}
    raw = perms.get(pipeline_doctype) or []

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
    return f"{sql_column(get_config().pipeline_fieldname)} IN ({esc})"


# ---------------------------------------------------------------------------
# Permission Query Condition (LIST / SEARCH / EXPORT)
# ---------------------------------------------------------------------------

def crm_lead_pqc(user: str) -> str:
    user = user or frappe.session.user

    # Admin / System Manager → everything
    if _is_privileged(user):
        return ""

    # Team managers see all leads owned by active users in their managed team.
    # Blank-owner leads stay limited to explicitly allowed pipelines.
    if _is_effective_team_leader(user):
        owner_cond = _lead_owner_sql_for_team(user)
        allowed = _allowed_pipelines(user)

        if not allowed:
            return owner_cond

        pipeline_cond = _allowed_pipelines_sql(user)
        blank_owner_cond = _blank_lead_owner_sql()
        return f"({owner_cond}) OR (({blank_owner_cond}) AND ({pipeline_cond}))"

    # Agent: only lead_owner + allowed pipeline
    if _has_agent_role(user) or _reports_to_team_leader(user):
        # lead_owner is the authoritative visibility field. ToDo assignments
        # are UI/task helpers and can drift independently.
        owner_cond = f"{sql_column(get_config().owner_fieldname)}={frappe.db.escape(user)}"
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
    if _is_privileged(user):
        return True

    # Team managers can open all leads owned by their active team users.
    # Blank-owner leads require an explicitly allowed pipeline.
    if _is_effective_team_leader(user):
        config = get_config()
        allowed = _allowed_pipelines(user)
        pipeline = getattr(doc, config.pipeline_fieldname, None)
        lead_owner = getattr(doc, config.owner_fieldname, None)

        if lead_owner in _team_owner_values(user):
            return True

        if not lead_owner and allowed:
            return pipeline in allowed

        return False

    # Agent: must be lead_owner + pipeline allowed
    if _has_agent_role(user) or _reports_to_team_leader(user):
        config = get_config()
        if getattr(doc, config.owner_fieldname, None) != user:
            return False

        allowed = _allowed_pipelines(user)
        if not allowed:
            return False

        pipeline = getattr(doc, config.pipeline_fieldname, None)
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

    config = get_config()
    if doc.doctype != config.ref_doctype:
        return

    if doc.name != data.get("lead"):
        return

    if not doc.get(config.owner_fieldname):
        doc.db_set(
            config.owner_fieldname,
            data.get("owner"),
            update_modified=False,
        )

    frappe.flags._sr_preserve_lead_owner = None
