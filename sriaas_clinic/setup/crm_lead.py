# apps/sriaas_clinic/sriaas_clinic/setup/crm_lead.py

import frappe
from .utils import create_cf_with_module, upsert_property_setter, ensure_field_after, ensure_field_before, set_full_field_order

DT = "CRM Lead"

def apply():
    _make_crm_lead_fields()
    _apply_crm_lead_ui_customizations()

def _make_crm_lead_fields():
    """Add custom fields + Meta Details tab + PEX tab to CRM Lead"""
    if not frappe.db.exists("DocType", DT):
        return

    create_cf_with_module({
        DT: [
            {
                "fieldname": "sr_lead_disposition",
                "label": "Lead Disposition",
                "fieldtype": "Link",
                "options": "SR Lead Disposition",
                "insert_after": "status",
                "depends_on": "eval: !!doc.status",
            },
            {
                "fieldname": "sr_lead_country",
                "label": "Country",
                "fieldtype": "Link",
                "options": "Country",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "email",
            },
            {"fieldname": "sr_lead_personal_cb2","fieldtype": "Column Break","insert_after": "mobile_no"},
            # {
            #     "fieldname": "sr_lead_department",
            #     "label": "Department",
            #     "fieldtype": "Link",
            #     "options": "Medical Department",
            #     "insert_after": "sr_lead_personal_cb2",
            # },
            {
                "fieldname": "sr_lead_message",
                "label": "Message",
                "fieldtype": "Small Text",
                "insert_after": "sr_lead_personal_cb2",
            },
            {
                "fieldname": "sr_lead_notes",
                "label": "Notes",
                "fieldtype": "Small Text",
                "insert_after": "sr_lead_message",
            },
            {"fieldname": "sr_lead_personal_cb3","fieldtype": "Column Break","insert_after": "sr_lead_notes"},
            {
                "fieldname": "sr_lead_pipeline",
                "label": "Pipeline",
                "fieldtype": "Link",
                "options": "SR Lead Pipeline",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "sr_lead_personal_cb3",
            },

             # TAB: PEX (after Meta Details)
            {
                "fieldname": "sr_lead_pex_tab",
                "label": "PEX",
                "fieldtype": "Tab Break",
                "insert_after": "status_change_log",
            },
            {
                "fieldname": "sr_lead_pex_launcher_html",
                "label": "PEX Launcher",
                "fieldtype": "HTML",
                "insert_after": "sr_lead_pex_tab",
                "read_only": 0,
            },

            # TAB: Meta Details
            {
                "fieldname": "sr_meta_tab",
                "label": "Meta Details",
                "fieldtype": "Tab Break",
                "insert_after": "sr_lead_pex_launcher_html",
            },
            # ---- Section: General Tracking ----
            {
                "fieldname": "sr_meta_general_sb",
                "label": "General Tracking",
                "fieldtype": "Section Break",
                "insert_after": "sr_meta_tab",
            },
            # Col 1
            {
                "fieldname": "sr_ip_address",
                "label": "IP Address",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_meta_general_sb",
            },
            {
                "fieldname": "sr_vpn_status",
                "label": "VPN Status",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_ip_address",
            },
            {
                "fieldname": "sr_landing_page",
                "label": "Landing Page",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_vpn_status",
            },
            # Col 2
            {
                "fieldname": "sr_meta_general_cb2",
                "label": "",
                "fieldtype": "Column Break",
                "insert_after": "sr_landing_page",
            },
            {
                "fieldname": "sr_remote_location",
                "label": "Remote Location",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_meta_general_cb2",
            },
            {
                "fieldname": "sr_user_agent",
                "label": "User Agent",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_remote_location",
            },
            # ---- Section: Google Tracking ----
            {
                "fieldname": "sr_meta_google_sb",
                "label": "Google Tracking",
                "fieldtype": "Section Break",
                "insert_after": "sr_user_agent",
            },
            # Col 1
            {
                "fieldname": "sr_utm_source",
                "label": "UTM Source",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_meta_google_sb",
            },
            {
                "fieldname": "sr_utm_campaign",
                "label": "UTM Campaign",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_utm_source",
            },
            {
                "fieldname": "sr_utm_campaign_id",
                "label": "UTM Campaign ID",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_utm_campaign",
            },
            {
                "fieldname": "sr_gclid",
                "label": "GCLID",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_utm_campaign_id",
            },
            # Col 2
            {
                "fieldname": "sr_meta_google_cb2",
                "label": "",
                "fieldtype": "Column Break",
                "insert_after": "sr_gclid",
            },
            {
                "fieldname": "sr_utm_medium",
                "label": "UTM Medium",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_meta_google_cb2",
            },
            {
                "fieldname": "sr_utm_term",
                "label": "UTM Term",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_utm_medium",
            },
            {
                "fieldname": "sr_utm_adgroup_id",
                "label": "UTM Ad Group ID",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_utm_term",
            },

            # ---- Section: Facebook Tracking ----
            {
                "fieldname": "sr_meta_facebook_sb",
                "label": "Facebook Tracking",
                "fieldtype": "Section Break",
                "insert_after": "sr_utm_adgroup_id",
            },
            {
                "fieldname": "sr_fbclid",
                "label": "FBCLID",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_meta_facebook_sb",
            },

            # ---- Section: Interakt Tracking ----
            {
                "fieldname": "sr_meta_interakt_sb",
                "label": "Interakt Tracking",
                "fieldtype": "Section Break",
                "insert_after": "sr_fbclid",
            },
            {
                "fieldname": "sr_w_source_id",
                "label": "W Source_id",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_meta_interakt_sb",
            },
            {
                "fieldname": "sr_w_source_url",
                "label": "W Source_url",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_w_source_id",
            },
            {
                "fieldname": "sr_w_ctwa_clid",
                "label": "W Ctwa_clid",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_w_source_url",
            },
            {
                "fieldname": "sr_w_team_id",
                "label": "W Team_id",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "sr_w_ctwa_clid",
            },
            # DEDUPE SECTION/TABLE (after your Meta Details or wherever you prefer)
            {
                "fieldname": "sr_dedupe_tab",
                "label": "Duplicates",
                "fieldtype": "Tab Break",
                "insert_after": "sr_w_team_id",
            },
            {
                "fieldname": "sr_dedupe_sec",
                "label": "Duplicates",
                "fieldtype": "Section Break",
                "insert_after": "sr_dedupe_tab",
            },
            {
                "fieldname": "sr_is_latest",
                "label": "Is Latest for Mobile",
                "fieldtype": "Check",
                "default": "1",            # harmless; your doc_events will overwrite correctly
                "read_only": 1,
                "insert_after": "sr_dedupe_sec",
                "in_list_view": 0,
                "in_standard_filter": 0,   # <— hide from the filter panel
            },
            {
                "fieldname": "sr_duplicate_count",
                "label": "Duplicate Count",
                "fieldtype": "Int",
                "default": 0,
                "read_only": 1,
                "insert_after": "sr_is_latest",
                "in_list_view": 0,
                "in_standard_filter": 0,
            },
            {
                "fieldname": "sr_primary_lead",
                "label": "Primary (Latest) Lead",
                "fieldtype": "Link",
                "options": "CRM Lead",
                "read_only": 1,
                "insert_after": "sr_duplicate_count",
            },
            {
                "fieldname": "sr_is_archived",
                "label": "Archived (Hidden)",
                "fieldtype": "Check",
                "default": "0",
                "read_only": 1,
                "insert_after": "sr_primary_lead",
                "in_list_view": 0,
                "in_standard_filter": 0    # <— also hidden
            },
        ]
    })

def _apply_crm_lead_ui_customizations():
    """
    Adjust some built-in/standard fields on CRM Lead via Property Setters:
    - Point Lead Source -> SR Lead Source (your custom master)
    - Move a few fields to sit nicely with your new fields
    - Make some filters/list view choices
    """
    if not frappe.db.exists("DocType", DT):
        return

    upsert_property_setter(DT, "status", "in_standard_filter", "1", "Check")
    upsert_property_setter(DT, "first_name", "reqd", "0", "Check")
    upsert_property_setter(DT, "mobile_no", "reqd", "1", "Check")
    upsert_property_setter(DT, "mobile_no", "in_list_view", "1", "Check")
    upsert_property_setter(DT, "mobile_no", "in_standard_filter", "1", "Check")
    upsert_property_setter(DT, "source", "label", "Lead Source", "Data")
    upsert_property_setter(DT, "source", "options", "SR Lead Source", "Link")
    upsert_property_setter(DT, "source", "in_list_view", "1", "Check")
    upsert_property_setter(DT, "source", "in_standard_filter", "1", "Check")

    # make the three fields non-editable by both roles (permlevel=1, nobody gets write)
    upsert_property_setter(DT, "source", "permlevel", "1", "Int")
    upsert_property_setter(DT, "sr_lead_pipeline", "permlevel", "1", "Int")
    upsert_property_setter(DT, "mobile_no", "permlevel", "1", "Int")

    # put lead_owner on its own level so ONLY Team Leader can be given write
    upsert_property_setter(DT, "lead_owner", "permlevel", "2", "Int")

    ensure_field_after(DT, "status", "sr_lead_pipeline")
    ensure_field_after(DT, "lead_name", "last_name")
    ensure_field_after(DT, "phone", "mobile_no")
    ensure_field_after(DT, "gender", "phone")

    # 5) Hide unwanted flags/fieldss
    targets = (
        "organization",
        "website",
        "territory",
        "industry",
        "job_title",
        "middle_name",
        "no_of_employees",
        "annual_revenue",
        "image",
        "converted",
        "salutation",
        "products",
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