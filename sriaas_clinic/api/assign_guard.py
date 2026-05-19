# apps/sriaas_clinic/sriaas_clinic/api/assign_guard.py

from __future__ import annotations
import frappe
from frappe.utils import cstr

from sriaas_clinic.api.crm_lead.config import REF_DOCTYPE, get_config


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------

def _is_team_leader(user: str) -> bool:
    from sriaas_role_permissions.api.roles import has_team_leader_role, is_privileged

    config = get_config()
    if is_privileged(user, REF_DOCTYPE):
        return True
    if not has_team_leader_role(user, REF_DOCTYPE):
        return False
    if config.team_leader_fieldname and frappe.db.has_column("User", config.team_leader_fieldname):
        return not frappe.db.get_value("User", user, config.team_leader_fieldname)
    return True


# ---------------------------------------------------------------------------
# CRM Lead assignment guard
# ---------------------------------------------------------------------------

def _ensure_can_assign_for_lead(docname: str, doctype: str) -> None:
    """
    Only Team Leader / System Manager can assign or unassign CRM Leads
    """
    config = get_config()
    if doctype != config.ref_doctype:
        return

    if not _is_team_leader(frappe.session.user):
        frappe.throw(
            f"Only configured {config.team_leader_label} users can assign or unassign {config.ref_doctype} records.",
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

    config = get_config()
    if doc.reference_type != config.ref_doctype:
        return

    if not doc.reference_name:
        return
    
    # 🚫 Skip preservation if explicitly clearing assignment
    if getattr(frappe.flags, "_sr_skip_owner_restore", False):
        return

    # Capture lead_owner BEFORE assignment removal
    owner = frappe.db.get_value(
        config.ref_doctype,
        doc.reference_name,
        config.owner_fieldname
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
