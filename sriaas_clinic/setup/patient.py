# sriaas_clinic/setup/patient.py
from .utils import create_cf_with_module, upsert_property_setter, ensure_field_after

DT = "Patient"

def apply():
    _make_patient_fields()
    _apply_patient_ui_customizations()

def _make_patient_fields():
    """Add custom fields to Patient"""
    create_cf_with_module({
        DT: [
            {"fieldname": "sr_medical_department","label": "Department","fieldtype": "Link","options": "Medical Department","insert_after": "patient_name","reqd": 1,"in_list_view": 1,"in_standard_filter": 1,"allow_in_quick_entry": 1},
            
            {"fieldname": "sr_patient_id","label": "Patient ID","fieldtype": "Data","insert_after": "sr_medical_department","read_only": 1,"unique": 1,"in_list_view": 1,"in_standard_filter": 1,"search_index": 1},
            
            {"fieldname": "sr_practo_id","label": "Practo ID","fieldtype": "Data","in_standard_filter": 0, "insert_after": "sr_patient_id"},
            
            {"fieldname": "sr_patient_age","label":"Patient Age","fieldtype":"Data","allow_in_quick_entry":1,"insert_after":"age_html"},

            {"fieldname": "sr_dpt_disease",
             "label":"Disease",
             "fieldtype":"Link",
             "options":"DPT Disease",
             "depends_on": 'eval:doc.sr_medical_department=="Regional"',
             "mandatory_depends_on": 'eval:doc.sr_medical_department=="Regional"',
             "in_list_view":1,
             "in_standard_filter":1,
             "allow_in_quick_entry":1,
             "insert_after":"sr_patient_age"},

            {"fieldname": "sr_dpt_language",
             "label":"Language",
             "fieldtype":"Link",
             "options":"DPT Language",
             "depends_on": 'eval:doc.sr_medical_department=="Regional"',
             "mandatory_depends_on": 'eval:doc.sr_medical_department=="Regional"',
             "in_list_view":1,
             "in_standard_filter":1,
             "allow_in_quick_entry":1,
             "insert_after":"sr_dpt_disease"},

            {"fieldname": "sr_followup_disable_reason","label":"Followup Disable Reason","fieldtype":"Link","options":"SR Patient Disable Reason","insert_after":"status","depends_on":'eval:doc.status=="Disabled"',"mandatory_depends_on":'eval:doc.status=="Disabled"'},
            {"fieldname": "sr_followup_status","label":"Followup Status","fieldtype":"Select","options":"\nPending\nDone","insert_after":"user_id","in_list_view":1,"in_standard_filter":1},

            {"fieldname": "sr_invoices_tab","label":"Invoices","fieldtype":"Tab Break","insert_after":"other_risk_factors"},
            {"fieldname": "sr_sales_invoice_list","label":"Sales Invoices","fieldtype":"Table","options":"SR Patient Invoice View","read_only":1,"insert_after":"sr_invoices_tab"},

            {"fieldname": "sr_payments_tab","label":"Payments","fieldtype":"Tab Break","insert_after":"sr_sales_invoice_list"},
            {"fieldname": "sr_payment_entry_list","label":"Payment Entries","fieldtype":"Table","options":"SR Patient Payment View","read_only":1,"insert_after":"sr_payments_tab"},

            {"fieldname": "sr_pex_tab","label":"PEX","fieldtype":"Tab Break","insert_after":"sr_payment_entry_list"},
            {"fieldname": "sr_pex_launcher_html","label":"PE Launcher","fieldtype":"HTML","read_only":1,"insert_after":"sr_pex_tab"},

            {"fieldname": "sr_followup_marker_tab","label":"Follow-up Marker","fieldtype":"Tab Break","insert_after":"sr_pex_launcher_html"},
            {"fieldname": "sr_followup_day","label": "Follow-up Day","fieldtype": "Select","options": "\nMon\nTue\nWed\nThu\nFri\nSat","insert_after": "sr_followup_marker_tab","read_only": 1,"in_list_view": 1,"in_standard_filter": 1},
            {"fieldname": "sr_followup_id","label": "Follow-up ID","fieldtype": "Select","options": "\n0\n1\n2\n3\n4\n5\n6\n7\n8\n9","insert_after": "sr_followup_day","read_only": 1,"in_list_view": 1,"in_standard_filter": 1},

            {
                "fieldname": "created_by_agent",
                "label": "Created By",
                "fieldtype": "Link",
                "options": "User",
                "read_only": 1,
                # do NOT set default here — we populate per-doc in before_insert
                "insert_after": "sr_followup_status",
            },
        ]
    })

def _apply_patient_ui_customizations():
    """Apply various UI customizations to Patient"""

    # Make Patient Status editable
    upsert_property_setter(DT, "status", "read_only", "0", "Check")
    upsert_property_setter(DT, "status", "read_only_depends_on", "", "Text")
    upsert_property_setter(DT, "status", "in_standard_filter", "1", "Select")

    upsert_property_setter(DT, "mobile", "read_only", "0", "Check")
    upsert_property_setter(DT, "mobile", "reqd", "1", "Check")

    upsert_property_setter(DT, "invite_user", "default", "0", "Check")
    upsert_property_setter(DT, "invite_user", "hidden", "1", "Check")
    upsert_property_setter(DT, "age", "hidden", "1", "Check")
    upsert_property_setter(DT, "age", "in_list_view", "0", "Check")
    upsert_property_setter(DT, "age", "in_standard_filter", "0", "Check")
    upsert_property_setter(DT, "uid", "in_standard_filter", "0", "Check")

    ensure_field_after(DT, "sr_dpt_disease", "sr_medical_department")
    ensure_field_after(DT, "sr_dpt_language", "sr_dpt_disease")

    # Disable Allow Rename on Patient DocType
    upsert_property_setter(DT, "allow_rename", "default", "0", "Check")
