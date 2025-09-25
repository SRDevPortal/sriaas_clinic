# sriaas_clinic/setup/item_price.py
import frappe
from .utils import create_cf_with_module

DT = "Item Price"

def apply():
    if not frappe.db.exists("DocType", DT):
        return
    create_cf_with_module({
        DT: [
            {
                "fieldname": "sr_cost_price",
                "label": "Cost Price",
                "fieldtype": "Currency",
                "insert_after": "price_list_rate",
                "description": "Cost for this Item in this Price List (used for margin calc).",
            }
        ]
    })
