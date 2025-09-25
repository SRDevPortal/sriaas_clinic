# sriaas_clinic/setup/crm_lead.py

import frappe
from .utils import create_cf_with_module, upsert_property_setter

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
                "in_standard_filter": 1,
                "insert_after": "email",
            },
            {"fieldname": "sr_lead_personal_cb2","fieldtype": "Column Break","insert_after": "mobile_no"},
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

    # 1) Retarget Lead Source link to your custom SR Lead Source master
    #    Common built-in fieldnames in lead doctypes are usually 'source' or 'lead_source'.
    #    We'll update both safely; only the existing one will take effect.
    upsert_property_setter(DT, "source", "options", "SR Lead Source", "Link")
    upsert_property_setter(DT, "lead_source", "options", "SR Lead Source", "Link")

    # 2) (Optional) Rename label to 'Lead Source' consistently
    upsert_property_setter(DT, "source", "label", "Lead Source", "Data")
    upsert_property_setter(DT, "lead_source", "label", "Lead Source", "Data")

    # 4) (Optional) Show Lead Source in list view
    upsert_property_setter(DT, "source", "in_list_view", "1", "Check")
    upsert_property_setter(DT, "lead_source", "in_list_view", "1", "Check")

    upsert_property_setter(DT, "mobile_no", "reqd", "1", "Check")
    upsert_property_setter(DT, "phone", "insert_after", "mobile_no", "Data")

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