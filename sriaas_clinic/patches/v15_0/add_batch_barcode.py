import frappe

def execute():
    """Add 'sr_barcode' custom field to 'Batch' DocType."""
    if not frappe.db.exists("Custom Field", {
        "dt": "Batch",
        "fieldname": "sr_barcode"
    }):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Batch",
            "label": "Barcode",
            "fieldname": "sr_barcode",
            "fieldtype": "Data",
            "insert_after": "batch_id",
            "unique": 1,
            "in_list_view": 1,
            "insert_after": "item_name",
        }).insert(ignore_permissions=True)

    frappe.db.commit()
