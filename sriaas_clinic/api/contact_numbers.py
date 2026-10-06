"""Clinic entry points for masked Contact maintenance."""
import frappe

@frappe.whitelist()
def get_context(doctype, name):
    from privacy_shield.contact_numbers import context
    return context(doctype, name)

@frappe.whitelist(methods=["POST"])
def update_numbers(doctype, name, modified, additions=None, primary_mobile=None, primary_phone=None):
    from privacy_shield.contact_numbers import update
    return update(doctype, name, modified, additions, primary_mobile, primary_phone)

@frappe.whitelist()
def get_actions(doctype, name):
    """Button visibility uses the same effective access as the save endpoint."""
    from privacy_shield.contact_numbers import context
    try:
        state = context(doctype, name)
        return {"can_add": state["can_add"], "can_primary": state["can_primary"]}
    except (frappe.PermissionError, frappe.DoesNotExistError, frappe.ValidationError):
        return {"can_add": False, "can_primary": False}
