from __future__ import annotations

import frappe


TEAM_LEADER_FIELD = "sr_reports_to_team_leader"


def sync_user_team_leaders(doc=None, method=None):
    """Keep User.Reports To Team Leader in sync with active Team membership."""
    if not _can_sync():
        return

    assignments = _active_team_assignments()

    users = set(assignments)
    users.update(
        frappe.get_all(
            "User",
            filters={TEAM_LEADER_FIELD: ["is", "set"]},
            pluck="name",
        )
        or []
    )

    for user in users:
        if not frappe.db.exists("User", user):
            continue

        frappe.db.set_value(
            "User",
            user,
            TEAM_LEADER_FIELD,
            assignments.get(user),
            update_modified=False,
        )

    frappe.clear_cache(doctype="User")


def _can_sync() -> bool:
    return bool(
        frappe.db.exists("DocType", "Team")
        and frappe.db.exists("DocType", "Team User")
        and frappe.db.has_column("User", TEAM_LEADER_FIELD)
    )


def _active_team_assignments() -> dict[str, str]:
    rows = frappe.db.sql(
        """
        SELECT tu.user, t.team_lead
        FROM `tabTeam User` tu
        INNER JOIN `tabTeam` t ON t.name = tu.parent
        WHERE tu.parenttype = 'Team'
          AND t.is_active = 1
          AND tu.is_active = 1
          AND tu.user IS NOT NULL
          AND tu.user != ''
          AND t.team_lead IS NOT NULL
          AND t.team_lead != ''
          AND tu.user != t.team_lead
        """,
        as_dict=True,
    )

    return {row.user: row.team_lead for row in rows}
