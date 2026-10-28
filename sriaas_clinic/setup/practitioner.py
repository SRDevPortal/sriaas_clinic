# sriaas_clinic/setup/practitioner.py
import frappe
from .utils import create_cf_with_module, upsert_property_setter

DT = "Healthcare Practitioner"

def apply():
    make_practitioner_fields()
    set_practitioner_autoname()

def make_practitioner_fields():
    """Add custom fields to Healthcare Practitioner"""
    create_cf_with_module({
        DT: [
            {
                "fieldname": "sr_reg_no",
                "label": "Registration No",
                "fieldtype": "Data",
                "insert_after": "office_phone",
            },
            {
                "fieldname": "sr_qualification",
                "label": "Qualification",
                "fieldtype": "Data",
                "reqd": 1,
                "insert_after": "sr_reg_no",
            },
            {
                "fieldname": "sr_college_university",
                "label": "College/University",
                "fieldtype": "Data",
                "insert_after": "sr_qualification",
            },
            {
                "fieldname": "sr_pathy",
                "label": "Pathy",
                "fieldtype": "Link",
                "options": "SR Practitioner Pathy",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "practitioner_type",
            },
        ]
    })

def set_practitioner_autoname():
    """Force naming rule: By fieldname (practitioner_name)."""
    # Naming Rule: use Naming Series or fieldname — keep as you had
    upsert_property_setter(DT, "", "naming_rule", "Naming Series", "Select")
    
    # Which field to use
    upsert_property_setter(DT, "", "autoname", "field:practitioner_name", "Data")
    # upsert_property_setter(DT, "", "autoname", "naming_series:", "Data")

    # Set title field to practitioner_name
    upsert_property_setter(DT, "", "title_field", "practitioner_name", "Data")

    # (Optional hardening) make practitioner_name required & unique
    upsert_property_setter(DT, "practitioner_name", "reqd", "1", "Check")
    upsert_property_setter(DT, "practitioner_name", "unique", "1", "Check")
