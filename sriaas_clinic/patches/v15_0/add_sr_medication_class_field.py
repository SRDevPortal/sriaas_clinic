import frappe

def execute():
    doctype = "SR Medication Template Item"

    # Ensure DocType exists
    if not frappe.db.exists("DocType", doctype):
        return

    # Avoid duplicate field
    if frappe.db.exists("DocField", {
        "parent": doctype,
        "fieldname": "sr_medication_class"
    }):
        return

    # Create field safely
    frappe.get_doc({
        "doctype": "DocField",
        "parent": doctype,
        "parenttype": "DocType",
        "parentfield": "fields",
        "fieldname": "sr_medication_class",
        "label": "Medication Class",
        "fieldtype": "Link",
        "options": "Medication Class",
        "reqd": 1,
        "fetch_from": "sr_medication.medication_class",
        "in_list_view": 1,
        "read_only": 1,
        "columns": 2,
    }).insert(ignore_permissions=True)

    frappe.clear_cache()
