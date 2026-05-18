import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


TEAM_LEADER_FIELD = "sr_reports_to_team_leader"


def execute():
    _create_user_team_leader_field()
    _seed_current_team_members()
    frappe.clear_cache(doctype="User")
    frappe.db.commit()


def _create_user_team_leader_field():
    create_custom_fields(
        {
            "User": [
                {
                    "fieldname": TEAM_LEADER_FIELD,
                    "label": "Reports To Team Leader",
                    "fieldtype": "Link",
                    "options": "User",
                    "insert_after": "role_profile_name",
                    "in_standard_filter": 1,
                    "description": "Restricts CRM Lead visibility for Team Leaders to their direct team.",
                }
            ]
        },
        update=True,
    )


def _seed_current_team_members():
    mappings = {
        "paraagent1@gmail.com": "tlpara@gmail.com",
        "paraagent2@gmail.com": "tlpara@gmail.com",
        "kidneyagent1@gmail.com": "tlkidney@gmail.com",
    }

    for agent, team_leader in mappings.items():
        if not frappe.db.exists("User", agent) or not frappe.db.exists("User", team_leader):
            continue

        frappe.db.set_value(
            "User",
            agent,
            TEAM_LEADER_FIELD,
            team_leader,
            update_modified=False,
        )
        _set_agent_role_profile(agent)


def _set_agent_role_profile(user):
    if not frappe.db.exists("Role Profile", "Agent"):
        return

    doc = frappe.get_doc("User", user)
    if doc.role_profile_name == "Agent":
        return

    doc.role_profile_name = "Agent"
    doc.save(ignore_permissions=True)
