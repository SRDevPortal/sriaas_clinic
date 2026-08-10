import frappe


REQUIRED_ROLES = (
    "Agent",
    "Team Leader",
)


def ensure_required_roles():
    """Create roles required by clinic permissions and workflows."""
    for role_name in REQUIRED_ROLES:
        if frappe.db.exists("Role", role_name):
            continue

        frappe.get_doc(
            {
                "doctype": "Role",
                "role_name": role_name,
            }
        ).insert(ignore_permissions=True)
