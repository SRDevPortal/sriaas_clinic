# apps/sriaas_clinic/sriaas_clinic/api/assign_guard.py
from __future__ import annotations
import frappe
from frappe.utils import cstr

LEAD_DT = "CRM Lead"
ASSIGN_PATH = "frappe.desk.form.assign_to"

def _is_team_leader(user: str) -> bool:
    if (user or "").lower() == "administrator":
        return True
    return "Team Leader" in set(frappe.get_roles(user)) or "System Manager" in set(frappe.get_roles(user))

def _ensure_can_assign_for_lead(docname: str, doctype: str) -> None:
    if doctype != LEAD_DT:
        # Only protect CRM Lead; pass through for other doctypes
        return
    if not _is_team_leader(frappe.session.user):
        frappe.throw("Only Team Leaders can assign or unassign CRM Leads.", frappe.PermissionError)

def todo_on_trash(doc, method=None):
    # Only care about CRM Lead assignments
    if doc.reference_type == "CRM Lead" and doc.allocated_to:
        try:
            frappe.share.remove(doc.reference_type, doc.reference_name, user=doc.allocated_to)
        except Exception:
            pass

# --- wrappers ---------------------------------------------------------------

@frappe.whitelist()
def add(args=None):
    """Wrap assign_to.add with Team Leader guard for CRM Lead."""
    args = args or frappe.local.form_dict.get("args")
    if isinstance(args, str):
        # args may be JSON-encoded; frappe helper handles it internally too
        pass
    ref_type = frappe.form_dict.reference_type or frappe.local.form_dict.get("reference_type") or (frappe.parse_json(args).get("doctype") if args else None)
    ref_name = frappe.form_dict.reference_name or frappe.local.form_dict.get("reference_name") or (frappe.parse_json(args).get("name") if args else None)

    _ensure_can_assign_for_lead(cstr(ref_name), cstr(ref_type))

    from frappe.desk.form import assign_to as core
    return core.add(args=args)

@frappe.whitelist()
def remove(doctype, name, assign_to):
    _ensure_can_assign_for_lead(cstr(name), cstr(doctype))
    from frappe.desk.form import assign_to as core
    out = core.remove(doctype, name, assign_to)
    # hard-remove any leftover shares for that user on this lead
    try:
        frappe.share.remove(doctype, name, user=assign_to)
    except Exception:
        pass
    return out

@frappe.whitelist()
def clear(doctype, name):
    _ensure_can_assign_for_lead(cstr(name), cstr(doctype))
    from frappe.desk.form import assign_to as core
    out = core.clear(doctype, name)
    # remove shares for ALL users that still have one
    try:
        for row in frappe.get_all("DocShare",
                                  filters={"share_doctype": doctype, "share_name": name},
                                  pluck="user"):
            frappe.share.remove(doctype, name, user=row)
    except Exception:
        pass
    return out
