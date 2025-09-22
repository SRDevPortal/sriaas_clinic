# sriaas_clinic/setup/customer.py
from .utils import create_cf_with_module

DT = "Customer"

def apply():
    _make_customer_fields()

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
                "search_index": 1
            }
        ]
    })
