# sriaas_clinic/setup/payment_entry.py
import frappe
from .utils import create_cf_with_module, upsert_property_setter, upsert_title_field

DT = "Payment Entry"

def apply():
    _make_payment_entry_fields()
    _customize_payment_entry_doctype()
    
def _make_payment_entry_fields():
    """
    Adds a hidden, read-only Link field on Payment Entry:
      - Fieldname: intended_sales_invoice
      - Links to:  Sales Invoice
      - Insert after: references
    Safe to run multiple times.
    """
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
            {
                "fieldname": "sr_payment_modes_sb",
                "label": "Payment Modes",
                "fieldtype": "Section Break",
                "collapsible": 0,
                "insert_after": "base_received_amount_after_tax"
            },
            {
                "fieldname": "sr_payment_modes",
                "label": "Payment Modes",
                "fieldtype": "Table",
                "options": "Payment Mode Detail",
                "insert_after": "sr_payment_modes_sb",
            },
            # {
            #     "fieldname": "sr_linked_journal_entry",
            #     "label": "Linked Journal Entry",
            #     "fieldtype": "Link",
            #     "options": "Journal Entry",
            #     "read_only": 1,
            #     "insert_after": "sr_payment_modes_sb"
            # }

        ]
    })

def _customize_payment_entry_doctype():
    """Additional customizations to Payment Entry doctype."""
    meta = frappe.get_meta(DT)

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