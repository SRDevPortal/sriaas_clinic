# sriaas_clinic/api/appointment.py
import frappe

def set_created_by_agent(doc, method):
    # only set if empty (so it doesn't overwrite later edits)
    if not getattr(doc, "created_by_agent", None):
        doc.created_by_agent = frappe.session.user
