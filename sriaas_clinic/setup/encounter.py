# apps/sriaas_clinic/sriaas_clinic/setup/encounter.py
import frappe
from .utils import create_cf_with_module, upsert_property_setter, collapse_section, set_label, upsert_title_field, ensure_field_after

DT = "Patient Encounter"

def apply():
    _make_encounter_fields()
    _setup_clinical_notes_section()
    _add_diet_chart_link_to_encounter()
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

            {"fieldname":"sr_encounter_place","label":"Encounter Place","fieldtype":"Select","options":"\nOnline\nOPD","reqd":1,"in_list_view":1,"in_standard_filter":1,"insert_after":"sr_encounter_type"},

            {"fieldname":"sr_sales_type","label":"Sales Type","fieldtype":"Link","options":"SR Sales Type","depends_on":'eval:doc.sr_encounter_type=="Order"',"mandatory_depends_on":'eval:doc.sr_encounter_type=="Order"',"insert_after":"sr_encounter_place"},

            {"fieldname":"sr_pe_mobile","label":"Patient Mobile","fieldtype":"Data","read_only":1,"depends_on":"eval:doc.patient","fetch_from":"patient.mobile","in_list_view":1,"in_standard_filter":1, "insert_after":"inpatient_status"},

            {"fieldname":"sr_pe_id","label":"Patient ID","fieldtype":"Data","read_only":1,"depends_on":"eval:doc.patient","fetch_from":"patient.sr_patient_id","in_list_view":1,"in_standard_filter":1,"insert_after":"sr_pe_mobile"},

            {"fieldname":"sr_pe_deptt","label":"Patient Department","fieldtype":"Link","options": "Medical Department","read_only":1,"depends_on":"eval:doc.patient","fetch_from":"patient.sr_medical_department","in_list_view":1,"in_standard_filter":1,"insert_after":"sr_pe_id"},

            {"fieldname":"sr_pe_age","label":"Patient Age","fieldtype":"Data","read_only":1,"depends_on":"eval:doc.patient","fetch_from":"patient.sr_patient_age","in_list_view":1,"in_standard_filter":1,"insert_after":"sr_pe_deptt"},

            {"fieldname":"sr_encounter_source","label":"Encounter Source","fieldtype":"Link","options":lead_source_dt,"reqd":1,"depends_on":'eval:doc.sr_encounter_place=="Online"',"mandatory_depends_on":'eval:doc.sr_encounter_place=="Online"',"insert_after":"google_meet_link"},

            {"fieldname":"sr_encounter_status","label":"Encounter Status","fieldtype":"Link","options":"SR Encounter Status","reqd":1,"in_list_view":1,"in_standard_filter":1,"allow_on_submit":1,"depends_on":'eval:doc.sr_encounter_place=="Online"',"mandatory_depends_on":'eval:doc.sr_encounter_place=="Online"',"insert_after":"sr_encounter_source"},

            {
                "fieldname": "created_by_agent",
                "label": "Created By",
                "fieldtype": "Link",
                "options": "User",
                "read_only": 1,
                "in_list_view":1,
                # do NOT set default here – we populate per-doc in before_insert
                "insert_after": "sr_encounter_status"
            },
        ]
    })

def _setup_clinical_notes_section():
    """Add Clinical Notes section to Patient Encounter"""

    # show_cond = 'eval:!(doc.sr_encounter_type=="Followup" && doc.sr_encounter_place=="Online")'

    hide_cond = 'eval:!(doc.sr_encounter_place=="Online" && ["Followup","Order"].includes(doc.sr_encounter_type))'

    create_cf_with_module({
        DT: [
            {
                "fieldname":"sr_clinical_notes_sb",
                "label":"Clinical Notes",
                "fieldtype":"Section Break",
                "collapsible":0,
                "insert_after":"submit_orders_on_save",
            },
            {
                "fieldname":"sr_complaints",
                "label":"Complaints",
                "fieldtype":"Small Text",
                "insert_after":"sr_clinical_notes_sb",
                "depends_on": hide_cond
            },
            {
                "fieldname":"sr_observations",
                "label":"Observations",
                "fieldtype":"Small Text",
                "insert_after":"sr_complaints",
                "depends_on": hide_cond
            },
            {
                "fieldname":"sr_investigations",
                "label":"Investigations",
                "fieldtype":"Small Text",
                "insert_after":"sr_observations",
                "depends_on": hide_cond
            },
            {
                "fieldname":"sr_diagnosis",
                "label":"Diagnosis",
                "fieldtype":"Small Text",
                "insert_after":"sr_investigations",
                "depends_on": hide_cond
            },
            {
                "fieldname":"sr_notes",
                "label":"Notes",
                "fieldtype":"Small Text",
                "insert_after":"sr_diagnosis"
            },
            # Use a child Table for multiple reports (one row per report)
            # {"fieldname":"sr_medical_reports_table","label":"Attach Medical Report","fieldtype":"Table","options":"SR Medical Report","insert_after":"sr_notes"},
            # HTML preview area for gallery (JS will render here)
            # {"fieldname":"sr_medical_reports_preview","label":"Medical Reports/Attachments","fieldtype":"HTML","insert_after":"sr_medical_reports_table"},
        ]
    })

def _add_diet_chart_link_to_encounter():
    """
    Add Diet Chart link field inside Encounter Doctype using the shared helper.
    Safe to run multiple times.
    """
    create_cf_with_module({
        DT: [
            {
                "fieldname": "diet_chart",
                "label": "Diet Chart",
                "fieldtype": "Link",
                "options": "Diet Chart",
                "insert_after": "sr_notes",
                "reqd": 0,
                "in_list_view": 0
            }
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
            {"fieldname":"sr_homeopathy_medications_sb","label":"Homeopathy Medications","fieldtype":"Section Break","collapsible":0,"insert_after":"drug_prescription"},
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
            {"fieldname":"sr_allopathy_medications_sb","label":"Allopathy Medications","fieldtype":"Section Break","collapsible":0,"insert_after":"sr_homeopathy_drug_prescription"},
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
    both_cond = 'eval:doc.sr_encounter_type=="Order" && (doc.sr_encounter_place=="Online" || doc.sr_encounter_place=="OPD")'
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
            {
                "fieldname": "sr_items_list_sb",
                "label": "Items List",
                "fieldtype": "Section Break",
                "collapsible": 0,
                "insert_after": "sr_delivery_type"
            },
            {
                "fieldname": "sr_pe_order_items",
                "label": "Order Items",
                "fieldtype": "Table",
                "options": "SR Order Item",
                "insert_after": "sr_items_list_sb"
            },

            {
                "fieldname": "enc_mmp_sb",
                "label": "Payments",
                "fieldtype": "Section Break",
                "collapsible": 0,
                "insert_after": "sr_pe_order_items"
            },
            {
                "fieldname": "enc_multi_payments",
                "label": "Payments (Multiple)",
                "fieldtype": "Table",
                "options": "SR Multi Mode Payment",
                "insert_after": "enc_mmp_sb",
                "in_list_view": 0
            },
        ]
    })

def _apply_encounter_ui_customizations():
    """Apply various UI customizations to Patient Encounter"""
    
    # --------------------------
    # 1) Collapse selected sections
    # --------------------------
    for f in ["sb_symptoms", "sb_test_prescription", "sb_procedures", "rehabilitation_section", "section_break_33"]:
        collapse_section(DT, f, True)

    # Rename section for clarity
    set_label(DT, "section_break_33", "Review")

    # Make drug prescription section collapsible
    upsert_property_setter(DT, "sb_drug_prescription", "collapsible", "0", "Check")

    # Rename drug prescription section to Ayurvedic Medications
    set_label(DT, "sb_drug_prescription", "Ayurvedic Medications")
    set_label(DT, "drug_prescription", "Ayurvedic Drug Prescription")

    # NOTE:
    # Legacy single-advance fields (sr_pe_paid_amount, sr_pe_mode_of_payment, sr_pe_payment_proof, etc.)
    # have been removed in favor of enc_multi_payments (SR Multi Mode Payment).
    # Therefore we no longer create depends_on / mandatory_depends_on rules for the deleted fields.

    upsert_property_setter(DT, "sr_encounter_source", "reqd", "0", "Check")
    upsert_property_setter(DT, "sr_encounter_status", "reqd", "0", "Check")
    upsert_property_setter(DT, "practitioner", "reqd", "0", "Check")

    upsert_property_setter(DT, "company", "reqd", "1", "Check")
    upsert_property_setter(DT, "company", "hidden", "0", "Check")
    upsert_property_setter(DT, "company", "read_only", "0", "Check")

    ensure_field_after(DT, "sr_notes", "sr_diagnosis")

    # --------------------------
    # 2) Hide unwanted flags/fields
    # --------------------------
    targets = (
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
        "get_applicable_treatment_plans",
        "sr_medical_reports_table",
        "sr_medical_reports_preview",
        # keep the new multi-payments UI visible (enc_mmp_sb & enc_multi_payments)
        # don't include deleted legacy single-advance fields here
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
            upsert_property_setter(DT, f, "reqd", "0", "Check")
    
    # Set title field to patient_name
    upsert_title_field(DT, "patient_name")

    # ensure created_by_agent is hidden (but not shown in list)
    upsert_property_setter(DT, "created_by_agent", "hidden", "0", "Check")
    upsert_property_setter(DT, "created_by_agent", "in_list_view", "0", "Check")
    upsert_property_setter(DT, "created_by_agent", "in_standard_filter", "0", "Check")
    upsert_property_setter(DT, "created_by_agent", "print_hide", "1", "Check")
