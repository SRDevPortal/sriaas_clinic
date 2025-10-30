# apps/sriaas_clinic/sriaas_clinic/setup/user_fields.py
import frappe
from .utils import create_cf_with_module

DT = "User"

def apply():
    if not frappe.db.exists("DocType", DT):
        return

    create_cf_with_module({
        DT: [
            {
                "fieldname": "sr_medical_department",
                "label": "Medical Department",
                "fieldtype": "Link",
                "options": "Medical Department",
                "insert_after": "username",
                "description": "Primary department for CRM lead access (drives group mapping).",
            },
            {
                "fieldname": "sr_seg_reception",
                "label": "Reception",
                "fieldtype": "Check",
                "insert_after": "sr_medical_department",
            },
            {
                "fieldname": "sr_seg_fresh",
                "label": "Fresh",
                "fieldtype": "Check",
                "insert_after": "sr_seg_reception",
            },
            {
                "fieldname": "sr_seg_repeat",
                "label": "Repeat",
                "fieldtype": "Check",
                "insert_after": "sr_seg_fresh",
            },
        ]
    })
