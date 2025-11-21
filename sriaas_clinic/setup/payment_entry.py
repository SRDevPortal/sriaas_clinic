# sriaas_clinic/setup/payment_entry.py
import frappe
from .utils import create_cf_with_module, upsert_property_setter, upsert_title_field, ensure_field_after

DT = "Payment Entry"

def apply():
    _make_payment_entry_fields()
    _customize_payment_entry_doctype()

def _lead_source_dt() -> str:
    if frappe.db.exists("DocType", "SR Lead Source"):
        return "SR Lead Source"
    if frappe.db.exists("DocType", "CRM Lead Source"):
        return "CRM Lead Source"
    return "Lead Source"

def _make_payment_entry_fields():
    """
    Adds a hidden, read-only Link field on Payment Entry:
      - Fieldname: intended_sales_invoice
      - Links to:  Sales Invoice
      - Insert after: references
    Safe to run multiple times.
    """
    # Determine which Lead Source doctype to link to
    lead_source_dt = _lead_source_dt()
    
    create_cf_with_module({
        DT: [
            {
                "fieldname": "intended_sales_invoice",
                "label": "Intended Sales Invoice",
                "fieldtype": "Link",
                "options": "Sales Invoice",
                "insert_after": "references",
                "read_only": 1,
                "hidden": 1,
            },
            {
                "fieldname": "created_by_agent",
                "label": "Created By",
                "fieldtype": "Link",
                "options": "User",
                "read_only": 1,
                # do NOT set default here — we'll populate per-doc via before_insert
                "insert_after": "posting_date",
            },

            {"fieldname":"sr_pe_track_sb","label":"Order Tracking Details","fieldtype":"Section Break","collapsible":1,"insert_after":"cost_center"},

            {"fieldname": "sr_pe_order_source","label": "Order Source","fieldtype": "Link","options": lead_source_dt,"in_list_view":1,"in_standard_filter":1,"insert_after": "sr_pe_track_sb"},

            {"fieldname": "sr_pe_encounter_place","label": "Encounter Place","fieldtype": "Data","in_list_view":1,"in_standard_filter":1,"insert_after": "sr_pe_order_source",},

            {"fieldname": "sr_pe_sales_type","label": "Sales Type","fieldtype": "Link","options": "SR Sales Type","in_list_view":1,"in_standard_filter":1,"insert_after": "sr_pe_encounter_place",},
            
            {"fieldname": "sr_pe_delivery_type","label": "Delivery Type","fieldtype": "Link","options": "SR Delivery Type","in_list_view":1,"in_standard_filter":1,"allow_on_submit":0,"insert_after": "sr_pe_sales_type"},
        ]
    })

def _customize_payment_entry_doctype():
    """Additional customizations to Payment Entry doctype."""
    meta = frappe.get_meta(DT)

    ensure_field_after(DT, "sr_pe_track_sb", "cost_center")

    # (Optional) ensure it's not in list/filters/print
    upsert_property_setter(DT, "intended_sales_invoice", "in_list_view", "0", "Check")
    upsert_property_setter(DT, "intended_sales_invoice", "in_standard_filter", "0", "Check")
    upsert_property_setter(DT, "intended_sales_invoice", "print_hide", "1", "Check")

    # Example: ensure created_by_agent is hidden and not shown in list/filter
    if meta.get_field("created_by_agent"):
        upsert_property_setter(DT, "created_by_agent", "hidden", "0", "Check")
        upsert_property_setter(DT, "created_by_agent", "in_list_view", "0", "Check")
        upsert_property_setter(DT, "created_by_agent", "in_standard_filter", "0", "Check")
        upsert_property_setter(DT, "created_by_agent", "print_hide", "1", "Check")
    
    # Set title field to party_name
    upsert_title_field(DT, "party_name")