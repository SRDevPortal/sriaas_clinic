# sriaas_clinic/setup/company.py
from .utils import create_cf_with_module

DT = "Company"

def apply():
    _make_company_fields()

def _make_company_fields():
    """Add custom fields to Company"""
    create_cf_with_module({
        DT: [
            {
                "fieldname": "sr_company_cin_no",
                "label": "CIN No",
                "fieldtype": "Data",
                "insert_after": "pan",
            }
        ]
    })
