# sriaas_clinic/setup/customer.py
from .utils import create_cf_with_module, upsert_property_setter

DT = "Customer"

def apply():
    _make_customer_fields()
    _apply_customer_ui_customizations()

def _make_customer_fields():
    """Add custom fields to Customer"""
    create_cf_with_module({
        DT: [
            {
                "fieldname": "sr_customer_id",
                "label": "Customer ID",
                "fieldtype": "Data",
                "insert_after": "customer_name",
                "read_only": 1,
                "unique": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "search_index": 1,
            }
        ]
    })

def _apply_customer_ui_customizations():
    """DocType-level tweaks for Customer"""
    # Uncheck “Allow Rename”
    upsert_property_setter(DT, "allow_rename", "default", "0", "Check")

    # (optional) keep the series field default in one place if you want:
    # upsert_property_setter(DT, "autoname", "default", "naming_series:", "Data")
