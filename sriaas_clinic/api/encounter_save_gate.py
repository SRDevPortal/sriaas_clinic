import frappe


@frappe.whitelist()
def autosave_allowed(encounter):
    """Compatibility endpoint: route completion no longer blocks autosave."""
    doc = frappe.get_doc("Patient Encounter", encounter)
    doc.check_permission("write")
    return True
