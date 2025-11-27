# sriaas_clinic/setup/purchase_order.py
import frappe
from .utils import create_cf_with_module, upsert_property_setter, ensure_field_after

# Child doctype which will receive the new field
DT_CHILD = "Purchase Order Item"
# Parent doctype to sanity-check / enforce child table options
PARENT_DT = "Purchase Order"

def apply():
    _make_po_item_fields()

def _make_po_item_fields():
    """
    Adds a Link field on Purchase Order Item:
      - fieldname: batch_no
      - label: Batch No
      - fieldtype: Link
      - options: Batch
      - insert_after: warehouse
    Safe to run multiple times.
    """
    create_cf_with_module({
        DT_CHILD: [
            {
                "fieldname": "batch_no",
                "label": "Batch No",
                "fieldtype": "Link",
                "options": "Batch",
                "insert_after": "warehouse",
                "in_list_view": 1,
                "print_hide": 0
            }
        ]
    })
