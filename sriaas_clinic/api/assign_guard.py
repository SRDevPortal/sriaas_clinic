# apps/sriaas_clinic/sriaas_clinic/api/assign_guard.py

from __future__ import annotations
import frappe
from frappe.utils import cstr

LEAD_DT = "CRM Lead"


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------

def _is_team_leader(user: str) -> bool:
    if (user or "").lower() == "administrator":
        return True
    roles = set(frappe.get_roles(user))
    return "Team Leader" in roles or "System Manager" in roles


# ---------------------------------------------------------------------------
# CRM Lead assignment guard
# ---------------------------------------------------------------------------

def _ensure_can_assign_for_lead(docname: str, doctype: str) -> None:
    """
    Only Team Leader / System Manager can assign or unassign CRM Leads
    """
    if doctype != LEAD_DT:
        return

    if not _is_team_leader(frappe.session.user):
        frappe.throw(
            "Only Team Leaders can assign or unassign CRM Leads.",
            frappe.PermissionError
        )


# ---------------------------------------------------------------------------
# ToDo delete hook (CRITICAL)
# Preserve lead_owner when assignment is cleared
# ---------------------------------------------------------------------------

def todo_on_trash(doc, method=None):
    """
    When a CRM Lead assignment (ToDo) is removed,
    preserve lead_owner UNLESS this is an intentional clear.
    """

    if doc.reference_type != LEAD_DT:
        return

    if not doc.reference_name:
        return
    
    # 🚫 Skip preservation if explicitly clearing assignment
    if getattr(frappe.flags, "_sr_skip_owner_restore", False):
        return

    # Capture lead_owner BEFORE assignment removal
    owner = frappe.db.get_value(
        LEAD_DT,
        doc.reference_name,
        "lead_owner"
    )

    if owner:
        frappe.flags._sr_preserve_lead_owner = {
            "lead": doc.reference_name,
            "owner": owner,
        }

    # Clean up DocShare safely
    if doc.allocated_to:
        try:
            frappe.share.remove(
                doc.reference_type,
                doc.reference_name,
                user=doc.allocated_to,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Assign wrappers (override core assign_to)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def add(args=None):
    """
    Wrapper over frappe.desk.form.assign_to.add
    Adds guard for CRM Lead
    """
    args = args or frappe.local.form_dict.get("args")
    data = frappe.parse_json(args) if args else {}

    ref_type = (
        frappe.form_dict.get("reference_type")
        or data.get("doctype")
    )
    ref_name = (
        frappe.form_dict.get("reference_name")
        or data.get("name")
    )

    # CRM Lead guard
    _ensure_can_assign_for_lead(cstr(ref_name), cstr(ref_type))

    from frappe.desk.form import assign_to as core
    return core.add(args=args)


@frappe.whitelist()
def remove(doctype, name, assign_to):
    """
    Remove single assignment safely (CRM Lead)
    """
    _ensure_can_assign_for_lead(cstr(name), cstr(doctype))

    from frappe.desk.form import assign_to as core
    out = core.remove(doctype, name, assign_to)

    # Remove share if any
    try:
        frappe.share.remove(doctype, name, user=assign_to)
    except Exception:
        pass

    return out


@frappe.whitelist()
def clear(doctype, name):
    """
    Clear all assignments safely (CRM Lead)
    """
    _ensure_can_assign_for_lead(cstr(name), cstr(doctype))

    from frappe.desk.form import assign_to as core
    out = core.clear(doctype, name)

    # Remove all shares
    try:
        for user in frappe.get_all(
            "DocShare",
            filters={
                "share_doctype": doctype,
                "share_name": name,
            },
            pluck="user",
        ):
            frappe.share.remove(doctype, name, user=user)
    except Exception:
        pass

    return out
