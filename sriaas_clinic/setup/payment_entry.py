# sriaas_clinic/setup/payment_entry.py
import frappe
from .utils import create_cf_with_module, upsert_property_setter

DT = "Payment Entry"

def apply():
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
            }
        ]
    })

    # (Optional) ensure it's not in list/filters/print
    upsert_property_setter(DT, "intended_sales_invoice", "in_list_view", "0", "Check")
    upsert_property_setter(DT, "intended_sales_invoice", "in_standard_filter", "0", "Check")
    upsert_property_setter(DT, "intended_sales_invoice", "print_hide", "1", "Check")
