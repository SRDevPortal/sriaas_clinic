# apps/sriaas_clinic/sriaas_clinic/setup/encounter.py
import frappe
from .utils import create_cf_with_module, upsert_property_setter, collapse_section, set_label, upsert_title_field, ensure_field_after

DT = "Patient Encounter"

def apply():
    _remove_deprecated_encounter_fields()
    _make_encounter_fields()
    _setup_clinical_notes_section()
    _setup_diet_chart_field()
    _setup_ayurvedic_section()
    _setup_homeopathy_section()
    _setup_allopathy_section()
    _setup_instructions_section()
    _setup_draft_invoice_tab()
    _setup_meta_details_tab()
    _apply_encounter_ui_customizations()

def _make_encounter_fields():
    """Add custom fields to Patient Encounter"""

    lead_source_dt = (
        "SR Lead Source"
        if frappe.db.exists("DocType", "SR Lead Source")
        else "Lead Source"
    )

    create_cf_with_module({
        DT: [

            {
                "fieldname": "sr_encounter_type",
                "label": "Encounter Type",
                "fieldtype": "Select",
                "options": "\nFollowup\nOrder\nAppointment",
                "reqd": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "allow_on_submit": 1,
                "insert_after": "naming_series",
            },

            {
                "fieldname": "sr_encounter_place",
                "label": "Encounter Place",
                "fieldtype": "Select",
                "options": "\nOnline\nOPD",
                "reqd": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "sr_encounter_type",
            },

            {
                "fieldname": "sr_sales_type",
                "label": "Sales Type",
                "fieldtype": "Link",
                "options": "SR Sales Type",
                "depends_on": 'eval:doc.sr_encounter_type=="Order"',
                "mandatory_depends_on": 'eval:doc.sr_encounter_type=="Order"',
                "insert_after": "sr_encounter_place",
            },

            {
                "fieldname": "sr_pe_mobile",
                "label": "Patient Mobile",
                "fieldtype": "Data",
                "read_only": 1,
                "depends_on": "eval:doc.patient",
                "fetch_from": "patient.mobile",
                "in_list_view": 1,
                "in_standard_filter": 0,
                "insert_after": "inpatient_status",
            },

            {
                "fieldname": "sr_pe_mobile_norm",
                "label": "Normalized Patient Mobile",
                "fieldtype": "Data",
                "read_only": 1,
                "hidden": 1,
                "no_copy": 1,
                "insert_after": "sr_pe_mobile",
            },

            {
                "fieldname": "sr_pe_id",
                "label": "Patient ID",
                "fieldtype": "Data",
                "read_only": 1,
                "depends_on": "eval:doc.patient",
                "fetch_from": "patient.sr_patient_id",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "sr_pe_mobile_norm",
            },

            {
                "fieldname": "sr_pe_deptt",
                "label": "Patient Department",
                "fieldtype": "Link",
                "options": "Medical Department",
                "read_only": 1,
                "depends_on": "eval:doc.patient",
                "fetch_from": "patient.sr_medical_department",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "sr_pe_id",
            },

            {
                "fieldname": "sr_pe_disease",
                "label": "Patient Disease",
                "fieldtype": "Link",
                "options": "DPT Disease",
                "read_only": 1,
                "depends_on": "eval:doc.patient",
                "fetch_from": "patient.sr_dpt_disease",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "sr_pe_deptt",
            },

            {
                "fieldname": "sr_pe_language",
                "label": "Patient Language",
                "fieldtype": "Link",
                "options": "DPT Language",
                "read_only": 1,
                "depends_on": "eval:doc.patient",
                "fetch_from": "patient.sr_dpt_language",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "sr_pe_disease",
            },

            {
                "fieldname": "sr_pe_age",
                "label": "Patient Age",
                "fieldtype": "Data",
                "read_only": 1,
                "depends_on": "eval:doc.patient",
                "fetch_from": "patient.sr_patient_age",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "sr_pe_deptt",
            },

            {
                "fieldname": "created_by_agent",
                "label": "Created By",
                "fieldtype": "Link",
                "options": "User",
                "read_only": 1,
                "in_list_view": 1,
                "insert_after": "google_meet_link",
            },

            {
                "fieldname": "sr_encounter_source",
                "label": "Encounter Source",
                "fieldtype": "Link",
                "options": lead_source_dt,
                "insert_after": "created_by_agent",
            },

            {
                "fieldname": "sr_source_crm_lead",
                "label": "Source CRM Lead",
                "fieldtype": "Link",
                "options": "CRM Lead",
                "read_only": 1,
                "hidden": 0,
                "insert_after": "sr_encounter_source",
            },

            {
                "fieldname": "sr_lead_notes",
                "label": "Lead Notes",
                "fieldtype": "Small Text",
                "read_only": 1,
                "hidden": 1,
                "insert_after": "sr_source_crm_lead",
            },

            {
                "fieldname": "sr_encounter_status",
                "label": "Encounter Status",
                "fieldtype": "Link",
                "options": "SR Encounter Status",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "allow_on_submit": 1,
                "insert_after": "sr_lead_notes",
            },
        ]
    })


def _setup_clinical_notes_section():
    """Add Clinical Notes section to Patient Encounter"""

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
        ]
    })


def _setup_diet_chart_field():
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


# healthcare practitioner fields helpers
def get_practitioner_name_field():
    """Return the correct name field for Healthcare Practitioner"""
    hp_meta = frappe.get_meta("Healthcare Practitioner")

    for field in ("practitioner_name", "full_name", "name"):
        if hp_meta.get_field(field):
            return field

    # Final safe fallback
    return "practitioner_name"

def get_practitioner_reg_field():
    """Return the correct registration number field for Healthcare Practitioner"""
    hp_meta = frappe.get_meta("Healthcare Practitioner")

    for field in ("sr_reg_no", "registration_no", "ayush_reg_no"):
        if hp_meta.get_field(field):
            return field

    return None


def _setup_ayurvedic_section():
    """Add Ayurvedic Medications section to Patient Encounter"""
    
    name_field = get_practitioner_name_field()
    reg_field = get_practitioner_reg_field()

    fields = [
        {
            "fieldname": "sr_medication_template",
            "label": "Medication Template",
            "fieldtype": "Link",
            "options": "SR Medication Template",
            "insert_after": "sb_drug_prescription"
        },
        {
            "fieldname": "sr_ayurvedic_practitioner",
            "label": "Ayurvedic Practitioner",
            "fieldtype": "Link",
            "options": "Healthcare Practitioner",
            "insert_after": "sr_medication_template"
        },
        {
            "fieldname": "sr_ayurvedic_practitioner_name",
            "label": "Practitioner Name",
            "fieldtype": "Data",
            "read_only": 1,
            "fetch_from": f"sr_ayurvedic_practitioner.{name_field}",
            "insert_after": "sr_ayurvedic_practitioner"
        }
    ]

    regno_field = {
        "fieldname": "sr_ayurvedic_practitioner_reg",
        "label": "Registration Number",
        "fieldtype": "Data",
        "read_only": 1,
        "insert_after": "sr_ayurvedic_practitioner_name"
    }

    if reg_field:
        regno_field["fetch_from"] = f"sr_ayurvedic_practitioner.{reg_field}"

    fields.append(regno_field)

    create_cf_with_module({DT: fields})


def _setup_homeopathy_section():
    """Add Homeopathy Medications section to Patient Encounter"""

    name_field = get_practitioner_name_field()
    reg_field = get_practitioner_reg_field()

    fields = [
        {
            "fieldname": "sr_homeopathy_medications_sb",
            "label": "Homeopathy Medications",
            "fieldtype": "Section Break",
            "collapsible": 0,
            "insert_after": "drug_prescription",
        },
        {
            "fieldname": "sr_homeopathy_practitioner",
            "label": "Homeopathy Practitioner",
            "fieldtype": "Link",
            "options": "Healthcare Practitioner",
            "insert_after": "sr_homeopathy_medications_sb",
        },
        {
            "fieldname": "sr_homeopathy_practitioner_name",
            "label": "Homeopathy Practitioner Name",
            "fieldtype": "Data",
            "read_only": 1,
            "fetch_from": f"sr_homeopathy_practitioner.{name_field}",
            "insert_after": "sr_homeopathy_practitioner",
        },
    ]

    regno_field = {
        "fieldname": "sr_homeopathy_practitioner_reg",
        "label": "Registration Number",
        "fieldtype": "Data",
        "read_only": 1,
        "insert_after": "sr_homeopathy_practitioner_name",
    }

    if reg_field:
        regno_field["fetch_from"] = f"sr_homeopathy_practitioner.{reg_field}"

    fields.append(regno_field)

    fields.append({
        "fieldname": "sr_homeopathy_drug_prescription",
        "label": "Homeopathy Drug Prescription",
        "fieldtype": "Table",
        "options": "Drug Prescription",
        "allow_on_submit": 1,
        "insert_after": "sr_homeopathy_practitioner_reg",
    })

    create_cf_with_module({ DT: fields})


def _setup_allopathy_section():
    """Add Allopathy Medications section to Patient Encounter"""

    name_field = get_practitioner_name_field()
    reg_field = get_practitioner_reg_field()

    fields = [
        {
            "fieldname": "sr_allopathy_medications_sb",
            "label": "Allopathy Medications",
            "fieldtype": "Section Break",
            "collapsible": 0,
            "insert_after": "sr_homeopathy_drug_prescription",
        },
        {
            "fieldname": "sr_allopathy_practitioner",
            "label": "Allopathy Practitioner",
            "fieldtype": "Link",
            "options": "Healthcare Practitioner",
            "insert_after": "sr_allopathy_medications_sb",
        },
        {
            "fieldname": "sr_allopathy_practitioner_name",
            "label": "Allopathy Practitioner Name",
            "fieldtype": "Data",
            "read_only": 1,
            "fetch_from": f"sr_allopathy_practitioner.{name_field}",
            "insert_after": "sr_allopathy_practitioner",
        },
    ]

    regno_field = {
        "fieldname": "sr_allopathy_practitioner_reg",
        "label": "Registration Number",
        "fieldtype": "Data",
        "read_only": 1,
        "insert_after": "sr_allopathy_practitioner_name",
    }

    if reg_field:
        regno_field["fetch_from"] = f"sr_allopathy_practitioner.{reg_field}"

    fields.append(regno_field)

    fields.append({
        "fieldname": "sr_allopathy_drug_prescription",
        "label": "Allopathy Drug Prescription",
        "fieldtype": "Table",
        "options": "Drug Prescription",
        "allow_on_submit": 1,
        "insert_after": "sr_allopathy_practitioner_reg",
    })

    create_cf_with_module({DT: fields})


def _setup_instructions_section():
    """Add Instructions section to Patient Encounter"""

    create_cf_with_module({
        DT: [

            {
                "fieldname": "sr_pe_instruction_sb",
                "label": "Instruction",
                "fieldtype": "Section Break",
                "collapsible": 1,
                "insert_after": "sr_allopathy_drug_prescription",
            },

            {
                "fieldname": "sr_pe_instruction",
                "label": "Instruction",
                "fieldtype": "Small Text",
                "insert_after": "sr_pe_instruction_sb",
            },
        ]
    })


def _setup_draft_invoice_tab():
    """Add Draft Invoice tab to Patient Encounter for Order and Appointment encounters"""

    both_cond = (
        'eval:["Order","Appointment"].includes(doc.sr_encounter_type) && '
        '(doc.sr_encounter_place=="Online" || doc.sr_encounter_place=="OPD")'
    )
    order_only_cond = (
        'eval:doc.sr_encounter_type=="Order" && '
        '(doc.sr_encounter_place=="Online" || doc.sr_encounter_place=="OPD")'
    )

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
                "mandatory_depends_on": order_only_cond,
            },

            {
                "fieldname": "sr_items_list_sb",
                "label": "Items List",
                "fieldtype": "Section Break",
                "collapsible": 0,
                "insert_after": "sr_delivery_type",
            },

            {
                "fieldname": "sr_pe_order_items",
                "label": "Order Items",
                "fieldtype": "Table",
                "options": "SR Order Item",
                "insert_after": "sr_items_list_sb",
            },

            {
                "fieldname": "enc_mmp_sb",
                "label": "Payments",
                "fieldtype": "Section Break",
                "collapsible": 0,
                "insert_after": "sr_pe_order_items",
            },

            {
                "fieldname": "enc_multi_payments",
                "label": "Payments (Multiple)",
                "fieldtype": "Table",
                "options": "SR Multi Mode Payment",
                "insert_after": "enc_mmp_sb",
                "in_list_view": 0,
            },
        ]
    })


def _setup_meta_details_tab():
    """Add Meta Details tab to Patient Encounter using the CRM Lead structure."""

    has_draft_invoice_fields = (
        frappe.get_meta(DT).get_field("enc_multi_payments")
        or frappe.db.exists("Custom Field", {"dt": DT, "fieldname": "enc_multi_payments"})
    )
    meta_insert_after = "enc_multi_payments" if has_draft_invoice_fields else "clinical_notes"

    create_cf_with_module({
        DT: [
            # Meta Details fields
            {"fieldname": "sr_meta_tab", "label": "Meta Details", "fieldtype": "Tab Break", "insert_after": meta_insert_after},

            # Meta Details - General Tracking
            {"fieldname": "sr_meta_general_sb", "label": "General Tracking", "fieldtype": "Section Break", "insert_after": "sr_meta_tab"},
            {"fieldname": "sr_ip_address", "label": "IP Address", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_meta_general_sb"},
            {"fieldname": "sr_vpn_status", "label": "VPN Status", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_ip_address"},
            {"fieldname": "sr_landing_page", "label": "Landing Page", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_vpn_status"},
            {"fieldname": "sr_meta_general_cb2", "fieldtype": "Column Break", "insert_after": "sr_landing_page"},
            {"fieldname": "sr_remote_location", "label": "Remote Location", "fieldtype": "Small Text", "read_only": 1, "insert_after": "sr_meta_general_cb2"},
            {"fieldname": "sr_user_agent", "label": "User Agent", "fieldtype": "Small Text", "read_only": 1, "insert_after": "sr_remote_location"},

            # Meta Details - Google Tracking
            {"fieldname": "sr_meta_google_sb", "label": "Google Tracking", "fieldtype": "Section Break", "insert_after": "sr_user_agent"},
            {"fieldname": "sr_utm_source", "label": "UTM Source", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_meta_google_sb"},
            {"fieldname": "sr_utm_campaign", "label": "UTM Campaign", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_utm_source"},
            {"fieldname": "sr_utm_campaign_id", "label": "UTM Campaign ID", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_utm_campaign"},
            {"fieldname": "sr_gclid", "label": "GCLID", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_utm_campaign_id"},
            {"fieldname": "sr_meta_google_cb2", "fieldtype": "Column Break", "insert_after": "sr_gclid"},
            {"fieldname": "sr_utm_medium", "label": "UTM Medium", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_meta_google_cb2"},
            {"fieldname": "sr_utm_term", "label": "UTM Term", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_utm_medium"},
            {"fieldname": "sr_utm_adgroup_id", "label": "UTM Ad Group ID", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_utm_term"},

            # Meta Details - Facebook Tracking
            {"fieldname": "sr_meta_facebook_sb", "label": "Facebook Tracking", "fieldtype": "Section Break", "insert_after": "sr_utm_adgroup_id"},
            {"fieldname": "sr_f_ad_id", "label": "Facebook Ad ID", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_meta_facebook_sb"},
            {"fieldname": "sr_f_ad_name", "label": "Facebook Ad Name", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_f_ad_id"},
            {"fieldname": "sr_f_adset_id", "label": "Facebook Ad Set ID", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_f_ad_name"},
            {"fieldname": "sr_f_adset_name", "label": "Facebook Ad Set Name", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_f_adset_id"},
            {"fieldname": "sr_f_campaign_id", "label": "Facebook Campaign ID", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_f_adset_name"},
            {"fieldname": "sr_f_campaign_name", "label": "Facebook Campaign Name", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_f_campaign_id"},
            {"fieldname": "sr_f_utm_medium", "label": "UTM Medium (Facebook)", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_f_campaign_name"},
            {"fieldname": "sr_fbclid", "label": "FBCLID", "fieldtype": "Data", "length": 255, "read_only": 1, "insert_after": "sr_f_utm_medium"},

            # Meta Details - Interakt Tracking
            {"fieldname": "sr_meta_interakt_sb", "label": "Interakt Tracking", "fieldtype": "Section Break", "insert_after": "sr_fbclid"},
            {"fieldname": "sr_w_source_id", "label": "W Source_id", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_meta_interakt_sb"},
            {"fieldname": "sr_w_source_url", "label": "W Source_url", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_w_source_id"},
            {"fieldname": "sr_w_ctwa_clid", "label": "W Ctwa_clid", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_w_source_url"},
            {"fieldname": "sr_w_team_id", "label": "W Team (Id)", "fieldtype": "Data", "hidden": 1, "read_only": 1, "insert_after": "sr_w_ctwa_clid"},
            {"fieldname": "sr_w_team_user", "label": "W Team (User)", "fieldtype": "Link", "options": "User", "read_only": 1, "insert_after": "sr_w_ctwa_clid"},
        ]
    })


def _remove_deprecated_encounter_fields():
    deprecated_fields = ("sr_lead_message",)

    for fieldname in deprecated_fields:
        custom_field = frappe.db.get_value(
            "Custom Field",
            {"dt": DT, "fieldname": fieldname},
            "name",
        )
        if custom_field:
            frappe.delete_doc("Custom Field", custom_field, ignore_permissions=True)

    frappe.clear_cache(doctype=DT)


def _apply_encounter_ui_customizations():
    """Apply various UI customizations to Patient Encounter"""

    # ---------------------------------------------------------------------
    # 1) Collapse & rename selected sections
    # ---------------------------------------------------------------------
    sections_to_collapse = [
        "sb_symptoms",
        "sb_test_prescription",
        "sb_procedures",
        "rehabilitation_section",
        "section_break_33",
    ]

    for fieldname in sections_to_collapse:
        collapse_section(DT, fieldname, True)

    # Rename section for clarity
    set_label(DT, "section_break_33", "Review")

    # Make drug prescription section collapsible
    upsert_property_setter(DT, "sb_drug_prescription", "collapsible", "0","Check")

    # Rename drug prescription section to Ayurvedic Medications
    set_label(DT, "sb_drug_prescription", "Ayurvedic Medications")
    set_label(DT, "drug_prescription", "Ayurvedic Drug Prescription")

    # ---------------------------------------------------------------------
    # NOTE:
    # Legacy single-advance fields (sr_pe_paid_amount, sr_pe_mode_of_payment,
    # sr_pe_payment_proof, etc.) have been removed in favor of
    # enc_multi_payments (SR Multi Mode Payment).
    # Hence, no depends_on / mandatory_depends_on rules exist for them.
    # ---------------------------------------------------------------------

    # Encounter Source rules
    # upsert_property_setter(DT, "sr_encounter_source", "reqd", "0", "Check")
    # upsert_property_setter(DT, "sr_encounter_source", "depends_on", "", "Data")
    # upsert_property_setter(DT, "sr_encounter_source", "mandatory_depends_on", "", "Data")

    # Encounter Status rules
    # upsert_property_setter(DT, "sr_encounter_status", "reqd", "0", "Check")
    # upsert_property_setter(DT, "sr_encounter_status", "hidden", "0", "Check")
    # upsert_property_setter(DT, "sr_encounter_status", "depends_on", "", "Data")
    # upsert_property_setter(DT, "sr_encounter_status", "mandatory_depends_on", "", "Data")

    # Practitioner not mandatory
    upsert_property_setter(DT, "practitioner", "reqd", "0", "Check")

    # Company must be visible and mandatory
    upsert_property_setter(DT, "company", "reqd", "1", "Check")
    upsert_property_setter(DT, "company", "hidden", "0", "Check")
    upsert_property_setter(DT, "company", "read_only", "0", "Check")

    # Ensure notes appear after diagnosis
    ensure_field_after(DT, "sr_notes", "sr_diagnosis")

    # ---------------------------------------------------------------------
    # 2) Hide unwanted flags / legacy fields
    # ---------------------------------------------------------------------
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
        # keep enc_mmp_sb & enc_multi_payments visible
    )

    for fieldname in targets:
        cfname = frappe.db.get_value(
            "Custom Field",
            {"dt": DT, "fieldname": fieldname},
            "name",
        )

        if cfname:
            cf = frappe.get_doc("Custom Field", cfname)
            cf.hidden = 1
            cf.in_list_view = 0
            cf.in_standard_filter = 0
            cf.save(ignore_permissions=True)
        else:
            upsert_property_setter(DT, fieldname, "hidden", "1", "Check")
            upsert_property_setter(DT, fieldname, "in_list_view", "0", "Check")
            upsert_property_setter(
                DT,
                fieldname,
                "in_standard_filter",
                "0",
                "Check",
            )
            upsert_property_setter(DT, fieldname, "reqd", "0", "Check")
    
    # ---------------------------------------------------------------------
    # 3) Final UI adjustments
    # ---------------------------------------------------------------------

    # Set title field to patient_name
    upsert_title_field(DT, "patient_name")

    # created_by_agent:
    # - visible on form
    # - hidden from list & filters
    # - hidden in print
    upsert_property_setter(DT, "created_by_agent", "hidden", "0", "Check")
    upsert_property_setter(DT, "created_by_agent", "in_list_view", "0", "Check")
    upsert_property_setter(DT, "created_by_agent", "in_standard_filter", "0", "Check")
    upsert_property_setter(DT, "created_by_agent", "print_hide", "1", "Check")
