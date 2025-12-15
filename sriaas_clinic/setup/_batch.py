# app/sriaas_clinic/setup/batch.py
import frappe

DT = "Batch"

def apply():
    _modify_batch_id_field()

def _modify_batch_id_field():
    # Update the batch_id field in the Batch DocType to make it non-unique and no_copy=0
    frappe.db.sql("""
        UPDATE `tabDocField`
        SET
            unique = 0,
            no_copy = 0
        WHERE
            parent = 'Batch' AND
            fieldname = 'batch_id'
    """)

    # Clear cache to ensure the change takes effect immediately
    frappe.clear_cache(doctype='Batch')

    print("Batch ID field updated successfully: unique=False, no_copy=0")
