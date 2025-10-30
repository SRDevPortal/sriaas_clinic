# sriaas_clinic/setup/encounter.py
import frappe
from .utils import create_cf_with_module, upsert_property_setter, collapse_section, set_label, upsert_title_field

DT = "Patient Encounter"

def apply():
    _make_encounter_fields()
    _setup_clinical_notes_section()
    _setup_ayurvedic_section()
    _setup_homeopathy_section()
    _setup_allopathy_section()
    _setup_instructions_section()
    _setup_draft_invoice_tab()
    _apply_encounter_ui_customizations()

def _make_encounter_fields():
    """Add custom fields to Patient Encounter"""
    lead_source_dt = "SR Lead Source" if frappe.db.exists("DocType", "SR Lead Source") else "Lead Source"

    create_cf_with_module({
        DT: [
            {"fieldname":"sr_encounter_type","label":"Encounter Type","fieldtype":"Select","options":"\nFollowup\nOrder","reqd":1,"in_list_view":1,"in_standard_filter":1,"allow_on_submit":1,"insert_after":"naming_series"},

            {"fieldname":"sr_sales_type","label":"Sales Type","fieldtype":"Link","options":"SR Sales Type","depends_on":'eval:doc.sr_encounter_type=="Order"',"mandatory_depends_on":'eval:doc.sr_encounter_type=="Order"',"insert_after":"sr_encounter_type"},

            {"fieldname":"sr_encounter_place","label":"Encounter Place","fieldtype":"Select","options":"\nOnline\nOPD","reqd":1,"in_list_view":1,"in_standard_filter":1,"insert_after":"sr_sales_type"},

            {"fieldname":"sr_pe_mobile","label":"Patient Mobile","fieldtype":"Data","read_only":1,"depends_on":"eval:doc.patient","fetch_from":"patient.mobile","in_list_view":1,"in_standard_filter":1,
            "insert_after":"inpatient_status"},

            {"fieldname":"sr_pe_id","label":"Patient ID","fieldtype":"Data","read_only":1,"depends_on":"eval:doc.patient","fetch_from":"patient.sr_patient_id","in_list_view":1,"in_standard_filter":1,"insert_after":"sr_pe_mobile"},

            {"fieldname":"sr_pe_deptt","label":"Patient Department","fieldtype":"Link","options": "Medical Department","read_only":1,"depends_on":"eval:doc.patient","fetch_from":"patient.sr_medical_department","in_list_view":1,"in_standard_filter":1,"insert_after":"sr_pe_id"},

            {"fieldname":"sr_pe_age","label":"Patient Age","fieldtype":"Data","read_only":1,"depends_on":"eval:doc.patient","fetch_from":"patient.sr_patient_age","in_list_view":1,"in_standard_filter":1,"insert_after":"sr_pe_deptt"},

            {"fieldname":"sr_encounter_source","label":"Encounter Source","fieldtype":"Link","options":lead_source_dt,"reqd":1,"insert_after":"google_meet_link"},

            {"fieldname":"sr_encounter_status","label":"Encounter Status","fieldtype":"Link","options":"SR Encounter Status","reqd":1,"in_list_view":1,"in_standard_filter":1,"allow_on_submit":1,"insert_after":"sr_encounter_source"},
        ]
    }),
    upsert_property_setter(DT, "get_applicable_treatment_plans", "hidden", "1", "Check")

def _setup_clinical_notes_section():
    """Add Clinical Notes section to Patient Encounter"""
    create_cf_with_module({
        DT: [
            {"fieldname":"sr_clinical_notes_sb","label":"Clinical Notes","fieldtype":"Section Break","collapsible":1,"insert_after":"submit_orders_on_save"},
            {"fieldname":"sr_complaints","label":"Complaints","fieldtype":"Small Text","insert_after":"sr_clinical_notes_sb"},
            {"fieldname":"sr_observations","label":"Observations","fieldtype":"Small Text","insert_after":"sr_complaints"},
            {"fieldname":"sr_investigations","label":"Investigations","fieldtype":"Small Text","insert_after":"sr_observations"},
            {"fieldname":"sr_notes","label":"Notes","fieldtype":"Small Text","insert_after":"sr_investigations"},
        ]
    })

def _setup_ayurvedic_section():
    """Add Ayurvedic Medications section to Patient Encounter"""
    hp_meta = frappe.get_meta("Healthcare Practitioner")
    name_field = "practitioner_name" if hp_meta.get_field("practitioner_name") else ("full_name" if hp_meta.get_field("full_name") else "practitioner_name")

    create_cf_with_module({
        DT: [
            {
                "fieldname":"sr_medication_template",
                "label":"Medication Template",
                "fieldtype":"Link",
                "options":"SR Medication Template",
                "insert_after":"sb_drug_prescription"
            },
            {
                "fieldname":"sr_ayurvedic_practitioner",
                "label":"Ayurvedic Practitioner",
                "fieldtype":"Link",
                "options":"Healthcare Practitioner",
                "insert_after":"sr_medication_template"
            },
            {
                "fieldname":"sr_ayurvedic_practitioner_name",
                "label":"Ayurvedic Practitioner Name",
                "fieldtype":"Data",
                "read_only":1,
                "fetch_from":f"sr_ayurvedic_practitioner.{name_field}",
                "insert_after":"sr_ayurvedic_practitioner"
            },
        ]
    })

def _setup_homeopathy_section():
    """Add Homeopathy Medications section to Patient Encounter"""
    hp_meta = frappe.get_meta("Healthcare Practitioner")
    name_field = "practitioner_name" if hp_meta.get_field("practitioner_name") else ("full_name" if hp_meta.get_field("full_name") else "practitioner_name")

    create_cf_with_module({
        DT: [
            {"fieldname":"sr_homeopathy_medications_sb","label":"Homeopathy Medications","fieldtype":"Section Break","collapsible":1,"insert_after":"drug_prescription"},
            {"fieldname":"sr_homeopathy_practitioner","label":"Homeopathy Practitioner","fieldtype":"Link","options":"Healthcare Practitioner","insert_after":"sr_homeopathy_medications_sb"},
            {"fieldname":"sr_homeopathy_practitioner_name","label":"Homeopathy Practitioner Name","fieldtype":"Data","read_only":1,"fetch_from":f"sr_homeopathy_practitioner.{name_field}","insert_after":"sr_homeopathy_practitioner"},
            {"fieldname":"sr_homeopathy_drug_prescription","label":"Homeopathy Drug Prescription","fieldtype":"Table","options":"Drug Prescription","allow_on_submit":1,"insert_after":"sr_homeopathy_practitioner_name"},
        ]
    })

def _setup_allopathy_section():
    """Add Allopathy Medications section to Patient Encounter"""
    hp_meta = frappe.get_meta("Healthcare Practitioner")
    name_field = "practitioner_name" if hp_meta.get_field("practitioner_name") else ("full_name" if hp_meta.get_field("full_name") else "practitioner_name")

    create_cf_with_module({
        DT: [
            {"fieldname":"sr_allopathy_medications_sb","label":"Allopathy Medications","fieldtype":"Section Break","collapsible":1,"insert_after":"sr_homeopathy_drug_prescription"},
            {"fieldname":"sr_allopathy_practitioner","label":"Allopathy Practitioner","fieldtype":"Link","options":"Healthcare Practitioner","insert_after":"sr_allopathy_medications_sb"},
            {"fieldname":"sr_allopathy_practitioner_name","label":"Allopathy Practitioner Name","fieldtype":"Data","read_only":1,"fetch_from":f"sr_allopathy_practitioner.{name_field}","insert_after":"sr_allopathy_practitioner"},
            {"fieldname":"sr_allopathy_drug_prescription","label":"Allopathy Drug Prescription","fieldtype":"Table","options":"Drug Prescription","allow_on_submit":1,"insert_after":"sr_allopathy_practitioner_name"},
        ]
    })

def _setup_instructions_section():
    """Add Instructions section to Patient Encounter"""
    create_cf_with_module({
        DT: [
            {"fieldname":"sr_pe_instruction_sb","label":"Instruction","fieldtype":"Section Break","collapsible":1,"insert_after":"sr_allopathy_drug_prescription"},
            {"fieldname":"sr_pe_instruction","label":"Instruction","fieldtype":"Small Text","insert_after":"sr_pe_instruction_sb"},
        ]
    })

def _setup_draft_invoice_tab():
    """Add Draft Invoice tab to Patient Encounter for 'Order' type encounters"""
    both_cond = 'eval:doc.sr_encounter_type=="Order" && doc.sr_encounter_place=="Online"'

    create_cf_with_module({
        DT: [
            {
                "fieldname": "sr_draft_invoice_tab",
                "label": "Draft Invoice",
                "fieldtype": "Tab Break",
                "insert_after": "clinical_notes",
                "depends_on": both_cond,
            },

            {
                "fieldname": "sr_delivery_type",
                "label": "Delivery Type",
                "fieldtype": "Link",
                "options": "SR Delivery Type",
                "insert_after": "sr_draft_invoice_tab",
                "depends_on": both_cond,
                "mandatory_depends_on": both_cond,
            },
            
            {"fieldname":"sr_items_list_sb","label":"Items List","fieldtype":"Section Break","collapsible":0,"insert_after":"sr_delivery_type"},
            {"fieldname":"sr_pe_order_items","label":"Order Items","fieldtype":"Table","options":"SR Order Item","insert_after":"sr_items_list_sb"},
            
            {"fieldname":"sr_advance_payment_sb","label":"Advance Payment","fieldtype":"Section Break","collapsible":0,"insert_after":"sr_pe_order_items"},
            {"fieldname":"sr_pe_paid_amount","label":"Paid Amount","fieldtype":"Currency","insert_after":"sr_advance_payment_sb"},
            {"fieldname":"sr_advance_payment_cb","fieldtype": "Column Break","insert_after": "sr_pe_paid_amount"},
            {"fieldname":"sr_pe_mode_of_payment","label":"Mode of Payment","fieldtype":"Link","options":"Mode of Payment", "insert_after":"sr_advance_payment_cb"},
            
            {"fieldname":"sr_payment_receipt_sb","label":"Payment Receipt","fieldtype":"Section Break","collapsible":0,"insert_after":"sr_pe_mode_of_payment"},
            {"fieldname":"sr_pe_payment_reference_no","label":"Payment Reference No","fieldtype":"Data","insert_after":"sr_payment_receipt_sb"},
            {"fieldname":"sr_pe_payment_proof","label":"Payment Proof","fieldtype":"Attach Image","insert_after":"sr_pe_payment_reference_no"},
            {"fieldname":"sr_payment_receipt_cb","fieldtype": "Column Break","insert_after": "sr_pe_payment_proof"},
            {"fieldname":"sr_pe_payment_reference_date","label":"Payment Reference Date","fieldtype":"Date","insert_after":"sr_payment_receipt_cb"},
        ]
    })

def _apply_encounter_ui_customizations():
    """Apply various UI customizations to Patient Encounter"""
    
    # --------------------------
    # 1) Collapse selected sections
    # --------------------------
    for f in [
        "sb_symptoms",
        "sb_test_prescription",
        "sb_procedures",
        "rehabilitation_section",
        "section_break_33"
    ]:
        collapse_section(DT, f, True)

    # Rename section for clarity
    set_label(DT, "section_break_33", "Review")

    # Make drug prescription section collapsible
    upsert_property_setter(DT, "sb_drug_prescription", "collapsible", "1", "Check")
    
    # Rename drug prescription section to Ayurvedic Medications
    set_label(DT, "sb_drug_prescription", "Ayurvedic Medications")
    set_label(DT, "drug_prescription", "Ayurvedic Drug Prescription")

    # show when Advance > 0
    for f in ["sr_pe_mode_of_payment","sr_payment_receipt_sb","sr_pe_payment_reference_no","sr_pe_payment_proof","sr_payment_receipt_cb","sr_pe_payment_reference_date"]:
        upsert_property_setter(DT, f, "depends_on", "eval:doc.sr_pe_paid_amount>0", "Data")

    # make these *visibly* required when Advance > 0
    for f in ["sr_pe_mode_of_payment","sr_pe_payment_proof","sr_pe_payment_reference_date"]:
        upsert_property_setter(DT, f, "mandatory_depends_on", "eval:doc.sr_pe_paid_amount>0", "Data")

    # and ensure the hard `reqd` flag is OFF so draft autosaves won't error
    for f in ["sr_pe_mode_of_payment","sr_pe_payment_proof","sr_pe_payment_reference_date"]:
        upsert_property_setter(DT, f, "reqd", "0", "Check")
    
    upsert_property_setter(DT, "sr_pe_payment_proof", "read_only", "0", "Check")

    upsert_property_setter(DT, "practitioner", "reqd", "0", "Check")

    # --------------------------
    # 2) Hide unwanted flags/fields
    # --------------------------
    targets = (
        "company",
        "practitioner",
        "invoiced",
        "submit_orders_on_save",
        "codification_table",
        "symptoms",
        "diagnosis",
        "procedure_prescription",
        "therapy_plan",
        "therapies",
        "naming_series",
        "appointment",
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
    
    # Set title field to patient_name
    upsert_title_field(DT, "patient_name")
