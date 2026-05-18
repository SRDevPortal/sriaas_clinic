import frappe


def execute():
    """Repair CRM Lead assignment helpers after moving visibility to lead_owner."""
    _remove_invalid_assignment_rows()
    _sync_open_todos_from_lead_owner()
    frappe.db.commit()


def _remove_invalid_assignment_rows():
    frappe.db.sql(
        """
        DELETE FROM `tabToDo`
        WHERE reference_type = 'CRM Lead'
          AND (reference_name IS NULL OR reference_name = '')
        """
    )
    frappe.db.sql(
        """
        DELETE FROM `tabDocShare`
        WHERE share_doctype = 'CRM Lead'
          AND (share_name IS NULL OR share_name = '')
        """
    )


def _sync_open_todos_from_lead_owner():
    leads = frappe.get_all(
        "CRM Lead",
        filters={"lead_owner": ["is", "set"]},
        fields=["name", "lead_owner"],
    )

    for lead in leads:
        if not frappe.db.exists("User", {"name": lead.lead_owner, "enabled": 1}):
            continue

        frappe.db.sql(
            """
            UPDATE `tabToDo`
            SET status = 'Closed'
            WHERE reference_type = 'CRM Lead'
              AND reference_name = %s
              AND status = 'Open'
              AND allocated_to != %s
            """,
            (lead.name, lead.lead_owner),
        )

        if frappe.db.exists(
            "ToDo",
            {
                "reference_type": "CRM Lead",
                "reference_name": lead.name,
                "allocated_to": lead.lead_owner,
                "status": "Open",
            },
        ):
            continue

        frappe.get_doc(
            {
                "doctype": "ToDo",
                "allocated_to": lead.lead_owner,
                "reference_type": "CRM Lead",
                "reference_name": lead.name,
                "description": f"Assignment for CRM Lead {lead.name}",
                "priority": "Medium",
                "status": "Open",
                "assigned_by": frappe.session.user,
            }
        ).insert(ignore_permissions=True)
        frappe.db.sql(
            """
            UPDATE `tabToDo`
            SET reference_name = %s
            WHERE reference_type = 'CRM Lead'
              AND allocated_to = %s
              AND status = 'Open'
              AND (reference_name IS NULL OR reference_name = '')
              AND description LIKE %s
            """,
            (lead.name, lead.lead_owner, f"%{lead.name}%"),
        )
