# apps/sriaas_clinic/sriaas_clinic/setup/masters.py
import frappe
from .utils import MODULE_DEF_NAME, ensure_module_def, reload_local_json_doctypes

# List doctypes you ship as JSON here (folder names under doctype/)
JSON_DOCTYPES = [
    # "sr_patient_disable_reason","sr_patient_invoice_view" ...
]

def apply():
    # Make sure Module Def existss
    ensure_module_def()
    # ensure_module_def("SRIAAS Clinic", "sriaas_clinic")
    # Reload any JSON Doctypes you ship with the app (if changed)
    reload_local_json_doctypes(JSON_DOCTYPES)
    _ensure_sr_patient_disable_reason()
    _ensure_sr_patient_invoice_view()
    _ensure_sr_patient_payment_view()
    _ensure_sr_multi_mode_payment()
    _ensure_sr_sales_type()
    _ensure_sr_encounter_status()
    _ensure_sr_order_item()
    _ensure_sr_instruction()
    _ensure_sr_medication_template_item()
    _ensure_sr_medication_template()
    _ensure_sr_delivery_type()    
    _ensure_sr_practitioner_pathy()
    _ensure_sr_state()
    _ensure_sr_lead_pipeline()
    _ensure_sr_lead_platform()
    _ensure_sr_lead_source()
    _ensure_sr_lead_disposition()
    _ensure_dpt_disease()
    _ensure_dpt_language()
    _ensure_sr_medical_report_doctype()
    create_bulk_clearance_doctype()

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
            "sr_payment_entry", "sr_posting_date", "sr_paid_amount", "sr_mode_of_payment",
            "sr_reference_no", "sr_reference_date", "sr_payment_proof"
        ],
        "fields": [
            {
                "fieldname":"sr_payment_entry", "label":"Payment Entry",
                "fieldtype":"Link", "options":"Payment Entry",
                "in_list_view":1, "columns":2
            },
            {
                "fieldname":"sr_posting_date", "label":"Posting Date",
                "fieldtype":"Date",
                "in_list_view":1, "columns":1
            },
            {
                "fieldname":"sr_paid_amount", "label":"Paid Amount",
                "fieldtype":"Currency",
                "in_list_view":1, "columns":1
            },
            {
                "fieldname":"sr_mode_of_payment", "label":"Mode of Payment",
                "fieldtype":"Link",
                "options":"Mode of Payment",
                "in_list_view":1, "columns":1
            },
            {
                "fieldname":"sr_reference_no", "label":"Payment Reference No",
                "fieldtype":"Data",
                "in_list_view":1, "columns":1
            },
            {
                "fieldname":"sr_reference_date", "label":"Payment Reference Date",
                "fieldtype":"Date",
                "in_list_view":1, "columns":1
            },
            {
                "fieldname":"sr_payment_proof", "label":"Payment Proof",
                "fieldtype":"Attach",
                "in_list_view":1, "columns":3
            },
        ],
        "permissions":[]
    }).insert(ignore_permissions=True)

def _ensure_sr_multi_mode_payment():
    """Create SR Multi Mode Payment master."""
    if frappe.db.exists("DocType", "SR Multi Mode Payment"):
        return

    frappe.get_doc({
        "doctype": "DocType",
        "name": "SR Multi Mode Payment",
        "module": MODULE_DEF_NAME,
        "custom": 1,
        "istable": 1,
        "editable_grid": 1,
        "field_order": [
            "mmp_payment_entry", "mmp_posting_date", "mmp_paid_amount", "mmp_mode_of_payment",
            "mmp_reference_no", "mmp_reference_date", "mmp_payment_proof"
        ],
        "fields": [
            {
                "fieldname":"mmp_payment_entry", "label":"Payment Entry",
                "fieldtype":"Link", "options":"Payment Entry",
                "in_list_view":1, "columns":2
            },
            {
                "fieldname":"mmp_posting_date", "label":"Posting Date",
                "fieldtype":"Date",
                "in_list_view":1, "columns":1
            },
            {
                "fieldname":"mmp_paid_amount", "label":"Paid Amount",
                "fieldtype":"Currency",
                "in_list_view":1, "columns":1
            },
            {
                "fieldname":"mmp_mode_of_payment", "label":"Mode of Payment",
                "fieldtype":"Link",
                "options":"Mode of Payment",
                "in_list_view":1, "columns":1
            },
            {
                "fieldname":"mmp_reference_no", "label":"Reference No",
                "fieldtype":"Data",
                "in_list_view":1, "columns":1
            },
            {
                "fieldname":"mmp_reference_date", "label":"Reference Date",
                "fieldtype":"Date",
                "in_list_view":1, "columns":1
            },
            {
                "fieldname":"mmp_payment_proof", "label":"Payment Proof",
                "fieldtype":"Attach",
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

def _ensure_sr_instruction():
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

def _ensure_sr_state():
    """Ensure SR State Doctype exists and seed all Indian states + UTs"""
    if frappe.db.exists("DocType", "SR State"):
        return

    frappe.get_doc({
        "doctype":"DocType",
        "name":"SR State",
        "module":MODULE_DEF_NAME,
        "custom":1,
        "is_submittable":0,
        "track_changes":1,
        "naming_rule":"By fieldname",
        "autoname":"field:sr_state_name",
        "title_field":"sr_state_name",
        "fields": [
            {
                "fieldname": "sr_state_name",
                "label": "State Name",
                "fieldtype": "Data",
                "reqd": 1,
                "unique": 1,
                "in_list_view": 1
            },
            {
                "fieldname": "sr_country",
                "label": "Country",
                "fieldtype": "Link",
                "options": "Country",
                "default": "India",
                "in_list_view": 1
            },
            {
                "fieldname": "sr_abbr",
                "label": "Abbreviation",
                "fieldtype": "Data"
            },
            {
                "fieldname": "sr_is_union_territory",
                "label": "Union Territory",
                "fieldtype": "Check",
                "default": 0
            }
        ],
        "permissions": [
            {
                "role": "System Manager",
                "read": 1, "write": 1,
                "create": 1, "delete": 1
            },
            {
                "role": "All",
                "read": 1
            }
        ],
    }).insert(ignore_permissions=True)

    # States + UTs
    states = [
        ("Andhra Pradesh", False), ("Arunachal Pradesh", False),
        ("Assam", False), ("Bihar", False), ("Chhattisgarh", False),
        ("Goa", False), ("Gujarat", False), ("Haryana", False),
        ("Himachal Pradesh", False), ("Jharkhand", False), ("Karnataka", False),
        ("Kerala", False), ("Madhya Pradesh", False), ("Maharashtra", False),
        ("Manipur", False), ("Meghalaya", False), ("Mizoram", False),
        ("Nagaland", False), ("Odisha", False), ("Punjab", False),
        ("Rajasthan", False), ("Sikkim", False), ("Tamil Nadu", False),
        ("Telangana", False), ("Tripura", False), ("Uttar Pradesh", False),
        ("Uttarakhand", False), ("West Bengal", False),
        # UTs
        ("Andaman and Nicobar Islands", True),
        ("Chandigarh", True),
        ("Dadra and Nagar Haveli and Daman and Diu", True),
        ("Delhi", True),
        ("Jammu and Kashmir", True),
        ("Ladakh", True),
        ("Lakshadweep", True),
        ("Puducherry", True),
    ]

    # Insert data if missing
    for state, is_ut in states:
        if not frappe.db.exists("SR State", state):
            frappe.get_doc({
                "doctype": "SR State",
                "sr_state_name": state,
                "sr_country": "India",
                "sr_is_union_territory": 1 if is_ut else 0
            }).insert(ignore_permissions=True)

    frappe.db.commit()
    frappe.logger().info("SR State Doctype and data seeded")

def _ensure_sr_lead_pipeline():
    """Create SR Lead Pipeline master."""
    if frappe.db.exists("DocType", "SR Lead Pipeline"):
        return

    frappe.get_doc({
        "doctype": "DocType",
        "name": "SR Lead Pipeline",
        "module": MODULE_DEF_NAME,
        "custom": 0,
        "istable": 0,
        "issingle": 0,
        "editable_grid": 0,
        "track_changes": 1,
        "allow_rename": 0,
        "allow_import": 1,

        "naming_rule": "By fieldname",
        "autoname": "field:sr_pipeline_name",
        "title_field": "sr_pipeline_name",

        "field_order": ["sr_pipeline_name", "is_active", "description"],
        "fields": [
            {
                "fieldname": "sr_pipeline_name",
                "label": "Pipeline Name",
                "fieldtype": "Data",
                "reqd": 1,
                "unique": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
            },
            {
                "fieldname": "is_active",
                "label": "Is Active",
                "fieldtype": "Check",
                "default": "1",
            },
            {
                "fieldname": "description",
                "label": "Description",
                "fieldtype": "Small Text",
            },
        ],

        "search_fields": "sr_pipeline_name",
        "show_name_in_global_search": 1,

        "permissions": [
            {"role": "System Manager", "read":1, "write":1, "create":1, "delete":1, "print":1, "email":1, "export":1},
            {"role": "Healthcare Administrator", "read":1, "write":1, "create":1, "delete":1},
        ],
    }).insert(ignore_permissions=True)

def _ensure_sr_lead_platform():
    """Create SR Lead Platform master."""
    if frappe.db.exists("DocType", "SR Lead Platform"):
        return

    frappe.get_doc({
        "doctype":"DocType",
        "name":"SR Lead Platform",
        "module":MODULE_DEF_NAME,
        "custom":0,
        "istable":0,
        "editable_grid":0,
        "issingle":0,
        "track_changes":1,
        "naming_rule":"By fieldname",
        "autoname":"field:sr_platform_name",
        "title_field":"sr_platform_name",
        "field_order":["sr_platform_name","sr_platform_details"],
        "fields": [
            {"fieldname": "sr_platform_name","fieldtype": "Data","label": "Platform Name","reqd": 1,"in_list_view": 1,"unique": 1},
            {"fieldname": "sr_platform_details","fieldtype": "Text Editor","label": "Platform Details"},
        ],
        "permissions": [
            {"role": "System Manager","read": 1, "write": 1, "create": 1, "delete": 1,"print": 1, "email": 1, "export": 1},
            {"role": "Healthcare Administrator","read": 1, "write": 1, "create": 1, "delete": 1},
        ],
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

def _ensure_sr_lead_disposition():
    """Create SR Lead Disposition master."""
    if frappe.db.exists("DocType", "SR Lead Disposition"):
        return

    frappe.get_doc({
        "doctype": "DocType",
        "name": "SR Lead Disposition",
        "module": MODULE_DEF_NAME,
        "custom": 0,
        "istable": 0,
        "issingle": 0,
        "editable_grid": 0,
        "track_changes": 1,
        "allow_rename": 0,
        "allow_import": 1,

        # Naming / title
        "naming_rule": "By fieldname",
        "autoname": "field:sr_disposition_name",
        "title_field": "sr_disposition_name",

        # Layout
        "field_order": [
            "sr_disposition_name",
            "sr_lead_status",
            "is_active",
            "description"
        ],

        "fields": [
            {
                "fieldname": "sr_disposition_name",
                "label": "Disposition Name",
                "fieldtype": "Data",
                "reqd": 1,
                "unique": 1,
                "in_list_view": 1,
                "in_standard_filter": 1
            },
            {
                "fieldname": "sr_lead_status",
                "label": "CRM Lead Status",
                "fieldtype": "Link",
                "options": "CRM Lead Status",
                "in_standard_filter": 1
            },
            {
                "fieldname": "is_active",
                "label": "Is Active",
                "fieldtype": "Check",
                "default": "1"
            },
            {
                "fieldname": "description",
                "label": "Description",
                "fieldtype": "Small Text"
            },
        ],

        # Permissions (adjust to your roles)
        "permissions": [
            { "role": "System Manager", "read":1, "write":1, "create":1, "delete":1, "print":1, "email":1, "export":1 },
            { "role": "Healthcare Administrator", "read":1, "write":1, "create":1, "delete":1 },
        ],
    }).insert(ignore_permissions=True)

def _ensure_dpt_disease():
    """Create DPT Disease master."""
    if frappe.db.exists("DocType", "DPT Disease"):
        return

    frappe.get_doc({
        "doctype": "DocType",
        "name": "DPT Disease",
        "module": MODULE_DEF_NAME,
        "naming_rule": "By fieldname",
        "autoname": "field:dept_disease_name",
        "title_field": "dept_disease_name",
        "field_order": ["dept_disease_name"],
        "fields":[
            {
                "fieldname":"dept_disease_name","label":"Disease Name","fieldtype":"Data","reqd":1,"in_list_view":1,"unique":1
            }
        ],
        "permissions":[
            {
                "role":"System Manager","read":1,"write":1,"create":1,"delete":1,"print":1,"email":1,"export":1
            }
        ],
    }).insert(ignore_permissions=True)

def _ensure_dpt_language():
    """Create DPT Language master."""
    if frappe.db.exists("DocType", "DPT Language"):
        return

    frappe.get_doc({
        "doctype": "DocType",
        "name": "DPT Language",
        "module": MODULE_DEF_NAME,
        "naming_rule": "By fieldname",
        "autoname": "field:dept_language_name",
        "title_field": "dept_language_name",
        "field_order": ["dept_language_name"],
        "fields":[
            {
                "fieldname":"dept_language_name","label":"Language","fieldtype":"Data","reqd":1,"in_list_view":1,"unique":1
            }
        ],
        "permissions":[
            {
                "role":"System Manager","read":1,"write":1,"create":1,"delete":1,"print":1,"email":1,"export":1
            }
        ],
    }).insert(ignore_permissions=True)

def _ensure_sr_medical_report_doctype():
    """Create SR Medical Report child table."""
    if frappe.db.exists("DocType", "SR Medical Report"):
        return

    frappe.get_doc({
        "doctype": "DocType",
        "name": "SR Medical Report",
        "module": MODULE_DEF_NAME,
        "custom": 1,
        "istable": 1,
        "editable_grid": 1,
        "field_order": [
            "sr_payment_entry", "sr_posting_date", "sr_paid_amount", "sr_mode_of_payment"
        ],
        "fields": [
            {
                "fieldname": "report",
                "label": "Report",
                "fieldtype": "Attach",
                "in_list_view":1,
                "columns":3
            },
            {
                "fieldname": "report_date",
                "label": "Report Date",
                "fieldtype": "Date",
                "in_list_view": 1,
                "columns": 2
            },
            {
                "fieldname": "report_type",
                "label": "Report Type",
                "fieldtype": "Data",
                "in_list_view": 0,
                "columns":2
            },
            {
                "fieldname": "notes",
                "label": "Notes",
                "fieldtype": "Small Text",
                "in_list_view": 0,
                "columns":3
            },
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Healthcare Administrator", "read": 1, "write": 0, "create": 0, "delete": 0}
        ]
    }).insert(ignore_permissions=True)

def create_bulk_clearance_doctype():
    """
    Idempotently create the 'Bulk Clearance Upload' DocType used to upload CSV and run bulk settle jobs.
    Run with:
      bench --site <site> execute sriaas_clinic.setup.masters.create_bulk_clearance_doctype
    """
    doctype_name = "Bulk Clearance Upload"

    if frappe.db.exists("DocType", doctype_name):
        print(f"DocType '{doctype_name}' already exists. Skipping.")
        return {"skipped": True, "reason": "exists"}

    # Basic DocType structure
    frappe.get_doc({
        "doctype": "DocType",
        "name": doctype_name,
        "module": MODULE_DEF_NAME,
        "custom": 1,
        "fields": [
            {
                "label": "CSV File",
                "fieldname": "csv_file",
                "fieldtype": "Attach",
                "reqd": 1
            },
            {
                "label": "Run Actual (create entries)",
                "fieldname": "run_actual",
                "fieldtype": "Check",
                "default": "0",
                "description": "When checked, the backend will create and submit Payment Entries. Otherwise performs dry-run."
            },
            {
                "label": "Process File",
                "fieldname": "process_button",
                "fieldtype": "Button"
            },
            {
                "label": "Result / Status",
                "fieldname": "status_html",
                "fieldtype": "HTML"
            },
            {
                "label": "Log File",
                "fieldname": "log_file",
                "fieldtype": "Data",
                "description": "URL of generated log CSV (e.g. /files/xxx.csv)"
            },
            {
                "label": "Last Run",
                "fieldname": "last_run",
                "fieldtype": "Datetime"
            }
        ],
        # small UX settings
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1},
            {"role": "Accounts Manager", "read": 1, "write": 1, "create": 1}
        ],

        # use hash autoname to avoid needing naming series setup
        "autoname": "hash",
        "is_table": 0,
        "issingle": 0,
        "istable": 0,
        "show_in_calendar": 0,
        "track_changes": 1,
        "allow_rename": 0,
        "module": MODULE_DEF_NAME,
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"Created DocType '{doctype_name}' in module '{MODULE_DEF_NAME}'.")

# End of sriaas_clinic/setup/masters.py