# sriaas_clinic/setup/masters.py
import frappe
from .utils import MODULE_DEF_NAME

def apply():
    _ensure_sr_patient_disable_reason()
    _ensure_sr_patient_invoice_view()
    _ensure_sr_patient_payment_view()
    _ensure_sr_sales_type()
    _ensure_sr_encounter_status()
    _ensure_sr_order_item()
    _ensure_sr_instructions()
    _ensure_sr_medication_template_item()
    _ensure_sr_medication_template()
    _ensure_sr_delivery_type()
    _ensure_sr_lead_source()
    _ensure_sr_practitioner_pathy()

def _ensure_sr_patient_disable_reason():
    """Create SR Patient Disable Reason master."""
    if frappe.db.exists("DocType", "SR Patient Disable Reason"):
        return

    frappe.get_doc({
        "doctype": "DocType","name": "SR Patient Disable Reason","module": MODULE_DEF_NAME,
        "custom": 0,"istable": 0,"issingle": 0,"editable_grid": 0,"track_changes": 1,"allow_rename": 0,"allow_import": 1,
        "naming_rule": "By fieldname","autoname": "field:sr_reason_name","title_field": "sr_reason_name",
        "field_order": ["sr_reason_name", "is_active", "description"],
        "fields": [
            {"fieldname":"sr_reason_name","label":"Reason Name","fieldtype":"Data","reqd":1,"in_list_view":1,"in_standard_filter":1,"unique":1},
            {"fieldname":"is_active","label":"Is Active","fieldtype":"Check","default":"1"},
            {"fieldname":"description","label":"Description","fieldtype":"Small Text"},
        ],
        "permissions": [
            {"role":"System Manager","read":1,"write":1,"create":1,"delete":1,"print":1,"email":1,"export":1},
            {"role":"Healthcare Administrator","read":1,"write":1,"create":1,"delete":1},
        ],
    }).insert(ignore_permissions=True)

def _ensure_sr_patient_invoice_view():
    """Create SR Patient Invoice View master."""
    if frappe.db.exists("DocType", "SR Patient Invoice View"):
        return

    frappe.get_doc({
        "doctype": "DocType",
        "name": "SR Patient Invoice View",
        "module": MODULE_DEF_NAME,
        "custom": 1,
        "istable": 1,
        "editable_grid": 1,
        "field_order": [
            "sr_invoice_no", "sr_posting_date", "sr_grand_total", "sr_outstanding"
        ],
        "fields": [
            {
                "fieldname": "sr_invoice_no", "label": "Sales Invoice",
                "fieldtype": "Link", "options": "Sales Invoice",
                "in_list_view": 1, "columns": 3
            },
            {
                "fieldname": "sr_posting_date", "label": "Posting Date",
                "fieldtype": "Date",
                "in_list_view": 1, "columns": 2
            },
            {
                "fieldname": "sr_grand_total", "label": "Grand Total",
                "fieldtype": "Currency",
                "in_list_view": 1, "columns": 2
            },
            {
                "fieldname": "sr_outstanding", "label": "Outstanding",
                "fieldtype": "Currency",
                "in_list_view": 1, "columns": 2
            },
        ],
        "permissions": [] 
    }).insert(ignore_permissions=True)

def _ensure_sr_patient_payment_view():
    """Create SR Patient Payment View master."""
    if frappe.db.exists("DocType", "SR Patient Payment View"):
        return

    frappe.get_doc({
        "doctype": "DocType",
        "name": "SR Patient Payment View",
        "module": MODULE_DEF_NAME,
        "custom": 1,
        "istable": 1,
        "editable_grid": 1,
        "field_order": [
            "sr_payment_entry", "sr_posting_date", "sr_paid_amount", "sr_mode_of_payment"
        ],
        "fields": [
            {
                "fieldname":"sr_payment_entry", "label":"Payment Entry",
                "fieldtype":"Link", "options":"Payment Entry",
                "in_list_view":1, "columns":3
            },
            {
                "fieldname":"sr_posting_date", "label":"Posting Date",
                "fieldtype":"Date",
                "in_list_view":1, "columns":2
            },
            {
                "fieldname":"sr_paid_amount", "label":"Paid Amount",
                "fieldtype":"Currency",
                "in_list_view":1, "columns":2},
            {
                "fieldname":"sr_mode_of_payment","label":"Mode of Payment",
                "fieldtype":"Data",
                "in_list_view":1, "columns":3
            },
        ],
        "permissions":[]
    }).insert(ignore_permissions=True)

def _ensure_sr_sales_type():
    """Create SR Sales Type master."""
    if frappe.db.exists("DocType", "SR Sales Type"):
        return

    frappe.get_doc({
        "doctype":"DocType","name":"SR Sales Type","module":MODULE_DEF_NAME,
        "naming_rule":"By fieldname","autoname":"field:sr_sales_type_name","title_field":"sr_sales_type_name",
        "field_order":["sr_sales_type_name"],
        "fields":[{"fieldname":"sr_sales_type_name","label":"Sales Type","fieldtype":"Data","reqd":1,"in_list_view":1,"unique":1}],
        "permissions":[{"role":"System Manager","read":1,"write":1,"create":1,"delete":1,"print":1,"email":1,"export":1}],
    }).insert(ignore_permissions=True)

def _ensure_sr_encounter_status():
    """Create SR Encounter Status master."""
    if frappe.db.exists("DocType", "SR Encounter Status"):
        return

    frappe.get_doc({
        "doctype":"DocType","name":"SR Encounter Status","module":MODULE_DEF_NAME,
        "naming_rule":"By fieldname","autoname":"field:sr_status_name","title_field":"sr_status_name",
        "field_order":["sr_status_name"],
        "fields":[{"fieldname":"sr_status_name","label":"Status Name","fieldtype":"Data","unique":1}],
        "permissions":[{"role":"System Manager","read":1,"write":1,"create":1,"delete":1,"print":1,"email":1,"export":1}],
    }).insert(ignore_permissions=True)

def _ensure_sr_order_item():
    """Create SR Order Item master."""
    if frappe.db.exists("DocType", "SR Order Item"):
        return

    frappe.get_doc({
        "doctype":"DocType","name":"SR Order Item","module":MODULE_DEF_NAME,
        "custom":0,"istable":1,"editable_grid":1,"issingle":0,"track_changes":1,
        "field_order":["sr_item_code","sr_item_name","sr_item_description","sr_item_uom","sr_item_qty","sr_item_rate","sr_item_amount"],
        "fields":[
            {"fieldname":"sr_item_code","label":"Item","fieldtype":"Link","options":"Item","reqd":1,"in_list_view":1},
            {"fieldname":"sr_item_name","label":"Item Name","fieldtype":"Data","read_only":1,"fetch_from":"sr_item_code.item_name"},
            {"fieldname":"sr_item_description","label":"Description","fieldtype":"Small Text"},
            {"fieldname":"sr_item_uom","label":"UOM","fieldtype":"Link","options":"UOM","in_list_view":1},
            {"fieldname":"sr_item_qty","label":"Qty","fieldtype":"Float","in_list_view":1,"default":1},
            {"fieldname":"sr_item_rate","label":"Rate","fieldtype":"Currency","in_list_view":1},
            {"fieldname":"sr_item_amount","label":"Amount","fieldtype":"Currency","in_list_view":1,"read_only":1},
        ],
        "permissions":[]
    }).insert(ignore_permissions=True)

def _ensure_sr_instructions():
    """Create SR Instruction master."""
    if frappe.db.exists("DocType", "SR Instruction"):
        return

    frappe.get_doc({
        "doctype":"DocType","name":"SR Instruction","module":MODULE_DEF_NAME,
        "naming_rule":"By fieldname","autoname":"field:sr_title","title_field":"sr_title",
        "track_changes":1,"allow_import":1,
        "field_order":["sr_title","sr_description"],
        "fields":[
            {"fieldname":"sr_title","label":"Title","fieldtype":"Data","reqd":1,"in_list_view":1,"unique":1},
            {"fieldname":"sr_description","label":"Description","fieldtype":"Small Text"},
        ],
        "permissions":[{"role":"System Manager","read":1,"write":1,"create":1,"delete":1,"print":1,"email":1,"export":1}],
    }).insert(ignore_permissions=True)

def _ensure_sr_medication_template_item():
    """Create SR Medication Template Item master."""
    if frappe.db.exists("DocType", "SR Medication Template Item"):
        return

    frappe.get_doc({
        "doctype":"DocType","name":"SR Medication Template Item","module":MODULE_DEF_NAME,
        "istable":1,"track_changes":1,
        "field_order":["sr_medication","sr_drug_code","sr_dosage","sr_period","sr_dosage_form","sr_instruction"],
        "fields":[
            {"fieldname":"sr_medication","label":"Medication","fieldtype":"Link","options":"Medication","reqd":1,"in_list_view":1},
            {"fieldname":"sr_drug_code","label":"Drug Code","fieldtype":"Link","options":"Item"},
            {"fieldname":"sr_dosage","label":"Dosage","fieldtype":"Link","options":"Prescription Dosage","reqd":1,"in_list_view":1},
            {"fieldname":"sr_period","label":"Period","fieldtype":"Link","options":"Prescription Duration","reqd":1,"in_list_view":1},
            {"fieldname":"sr_dosage_form","label":"Dosage Form","fieldtype":"Link","options":"Dosage Form","reqd":1,"in_list_view":1},
            {"fieldname":"sr_instruction","label":"Instruction","fieldtype":"Link","options":"SR Instruction","reqd":1,"in_list_view":1},
        ],
    }).insert(ignore_permissions=True)

def _ensure_sr_medication_template():
    """Create SR Medication Template master."""
    if frappe.db.exists("DocType", "SR Medication Template"):
        return

    frappe.get_doc({
        "doctype":"DocType","name":"SR Medication Template","module":MODULE_DEF_NAME,
        "naming_rule":"By fieldname","autoname":"field:sr_template_name","title_field":"sr_template_name",
        "track_changes":1,"allow_import":1,
        "field_order":["sr_template_name","sr_tmpl_instruction","sr_medications"],
        "fields":[
            {"fieldname":"sr_template_name","label":"Template Name","fieldtype":"Data","reqd":1,"in_list_view":1,"unique":1},
            {"fieldname":"sr_tmpl_instruction","label":"Instruction","fieldtype":"Small Text"},
            {"fieldname":"sr_medications","label":"Medications","fieldtype":"Table","options":"SR Medication Template Item"},
        ],
        "permissions":[{"role":"System Manager","read":1,"write":1,"create":1,"delete":1,"print":1,"email":1,"export":1}],
    }).insert(ignore_permissions=True)

def _ensure_sr_delivery_type():
    """Create SR Delivery Type master."""
    if frappe.db.exists("DocType", "SR Delivery Type"):
        return

    frappe.get_doc({
        "doctype":"DocType","name":"SR Delivery Type","module":MODULE_DEF_NAME,
        "naming_rule":"By fieldname","autoname":"field:sr_delivery_type_name","title_field":"sr_delivery_type_name","track_changes":1,
        "field_order":["sr_delivery_type_name"],
        "fields":[{"fieldname":"sr_delivery_type_name","label":"Delivery / Service Type","fieldtype":"Data","reqd":1,"unique":1,"in_list_view":1}],
        "permissions":[{"role":"System Manager","read":1,"write":1,"create":1,"delete":1,"print":1,"email":1,"export":1}],
    }).insert(ignore_permissions=True)

def _ensure_sr_lead_source():
    """Create SR Lead Source master."""
    if frappe.db.exists("DocType", "SR Lead Source"):
        return

    frappe.get_doc({
        "doctype":"DocType",
        "name":"SR Lead Source",
        "module":MODULE_DEF_NAME,
        "custom":0,
        "istable":0,
        "editable_grid":0,
        "issingle":0,
        "track_changes":1,
        "naming_rule":"By fieldname",
        "autoname":"field:sr_source_name",
        "title_field":"sr_source_name",
        "field_order":["sr_source_name","sr_source_details"],
        "fields": [
            {"fieldname": "sr_source_name","fieldtype": "Data","label": "Source Name","reqd": 1,"in_list_view": 1,"unique": 1},
            {"fieldname": "sr_source_details","fieldtype": "Text Editor","label": "Source Details"},
        ],
        "permissions": [
            {"role": "System Manager","read": 1, "write": 1, "create": 1, "delete": 1,"print": 1, "email": 1, "export": 1},
            {"role": "Healthcare Administrator","read": 1, "write": 1, "create": 1, "delete": 1},
        ],
    }).insert(ignore_permissions=True)

def _ensure_sr_practitioner_pathy():
    """Create SR Practitioner Pathy master."""
    if frappe.db.exists("DocType", "SR Practitioner Pathy"):
        return

    frappe.get_doc({
        "doctype": "DocType",
        "name": "SR Practitioner Pathy",
        "module": MODULE_DEF_NAME,
        "custom": 1,
        "istable": 0,
        "is_tree": 0,
        "editable_grid": 1,
        "track_changes": 1,
        "naming_rule": "By fieldname",
        "autoname": "field:sr_pathy_name",
        "title_field": "sr_pathy_name",
        "fields": [
            {
                "fieldname": "sr_pathy_name",
                "fieldtype": "Data",
                "label": "Pathy Name",
                "reqd": 1,
                "in_list_view": 1
            },
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Healthcare Administrator", "read": 1, "write": 1, "create": 1},
            {"role": "All", "read": 1},
        ],
    }).insert(ignore_permissions=True)
