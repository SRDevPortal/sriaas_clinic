# apps/sriaas_clinic/sriaas_clinic/api/payment_entry.py
import frappe

def set_created_by_agent(doc, method):
    # populate only if empty so edits won't overwrite original creator
    if not getattr(doc, "created_by_agent", None):
        doc.created_by_agent = frappe.session.user
