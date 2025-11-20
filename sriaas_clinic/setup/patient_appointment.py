# apps/sriaas_clinic/sriaas_clinic/setup/appointment.py

import frappe
from .utils import create_cf_with_module, upsert_property_setter, ensure_field_before, ensure_field_after

DT = "Patient Appointment"

def apply():
    _make_appointment_fields()
    _hide_payment_child_fields()
    _customize_appointment_doctype()

def _make_appointment_fields():
    """Add custom fields to Patient Appointment (safe to run multiple times)."""
    if not frappe.db.exists("DocType", DT):
        return

    create_cf_with_module({
        DT: [
            {
                "fieldname": "apt_patient_id",
                "label": "Patient ID",
                "fieldtype": "Data",
                "read_only": 1,
                "depends_on": "eval:doc.patient",
                "fetch_from": "patient.sr_patient_id",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "patient_name"
            },
            {
                "fieldname": "apt_mobile_number",
                "label": "Mobile Number",
                "fieldtype": "Data",
                "read_only": 1,
                "depends_on": "eval:doc.patient",
                "fetch_from": "patient.mobile",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "apt_patient_id"
            },
            {
                "fieldname": "apt_patient_age",
                "label": "Patient Age",
                "fieldtype": "Data",
                "read_only": 1,
                "depends_on": "eval:doc.patient",
                "fetch_from": "patient.sr_patient_age",
                "insert_after": "patient_sex"
            },
            {
                "fieldname": "apt_department",
                "label": "Patient Department",
                "fieldtype": "Link",
                "options": "Medical Department",
                "read_only": 1,
                "depends_on": "eval:doc.patient",
                "fetch_from": "patient.sr_medical_department",
                "in_list_view": 0,
                "in_standard_filter": 1,
                "insert_after": "apt_patient_age"
            },
            {
                "fieldname": "created_by_agent",
                "label": "Created By",
                "fieldtype": "Link",
                "options": "User",
                "read_only": 1,
                # do NOT set default here – we populate per-doc in before_insert
                "insert_after": "appointment_date"
            },
            # --- Payments (Table) field to hold multiple payments ---
            {
                "fieldname": "apt_payments_sb",
                "label": "Payments",
                "fieldtype": "Section Break",
                "collapsible": 0,
                "insert_after": "ref_sales_invoice"
            },
            {
                "fieldname": "apt_payments",
                "label": "Payments (Multiple)",
                "fieldtype": "Table",
                "options": "SR Patient Payment View",
                "insert_after": "apt_payments_sb",
                "in_list_view": 0
            },
        ]
    })

# hide child table fields in SR Patient Payment View so they are not shown while booking
def _hide_payment_child_fields():
    # hide columns on the child doctype
    upsert_property_setter("SR Patient Payment View", "sr_payment_entry", "hidden", "1", "Check")
    upsert_property_setter("SR Patient Payment View", "sr_posting_date", "hidden", "1", "Check")

    # ensure they are not required and not shown in list view
    upsert_property_setter("SR Patient Payment View", "sr_payment_entry", "reqd", "0", "Check")
    upsert_property_setter("SR Patient Payment View", "sr_posting_date", "reqd", "0", "Check")
    upsert_property_setter("SR Patient Payment View", "sr_payment_entry", "in_list_view", "0", "Check")
    upsert_property_setter("SR Patient Payment View", "sr_posting_date", "in_list_view", "0", "Check")

def _customize_appointment_doctype():
    """Move a few fields to sit nicely with your new fields"""
    ensure_field_after(DT, "mode_of_payment", "column_break_2")
    ensure_field_before(DT, "paid_amount", "billing_item")

    """Set properties on Patient Appointment fields."""
    targets = (
        "service_unit",
        "event",
        "patient_age",
        "therapy_plan",
        "get_procedure_from_encounter",
        "procedure_template",
        "invoiced"
    )
    for f in targets:
        cfname = frappe.db.get_value("Custom Field", {"dt": DT, "fieldname": f}, "name")
        if cfname:
            cf = frappe.get_doc("Custom Field", cfname)
            cf.hidden = 1
            cf.in_list_view = 0
            cf.in_standard_filter = 0
            cf.save(ignore_permissions=True)
        else:
            upsert_property_setter(DT, f, "hidden", "1", "Check")
            upsert_property_setter(DT, f, "in_list_view", "0", "Check")
            upsert_property_setter(DT, f, "in_standard_filter", "0", "Check")
    
    # Ensure created_by_agent is hidden in the form by property setter
    upsert_property_setter(DT, "created_by_agent", "hidden", "0", "Check")
    upsert_property_setter(DT, "created_by_agent", "in_list_view", "0", "Check")
    upsert_property_setter(DT, "created_by_agent", "in_standard_filter", "0", "Check")
    upsert_property_setter(DT, "created_by_agent", "print_hide", "1", "Check")
