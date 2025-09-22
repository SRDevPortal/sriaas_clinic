# sriaas_clinic/setup/drug_prescription.py
import frappe
from .utils import create_cf_with_module, upsert_property_setter

DT = "Drug Prescription"

def apply():
    _make_drug_prescription_fields()

def _make_drug_prescription_fields():
    create_cf_with_module({
        DT: [
            {
                "fieldname": "sr_medication_name_print",
                "label": "Medication Name",
                "fieldtype": "Data",
                "read_only": 1,
                "in_list_view": 1,
                "in_standard_filter": 0,
                "insert_after": "medication",
            },
            {
                "fieldname": "sr_drug_instruction",
                "label": "Instruction",
                "fieldtype": "Link",
                "options": "SR Instruction",
                "in_list_view": 1,
                "in_standard_filter": 0,
                "insert_after": "period",
            },
        ]
    })

   # In case the field already exists, enforce these props
    # upsert_property_setter(DT, "sr_medication_name_print", "read_only", "1", "Check")
    # upsert_property_setter(DT, "sr_medication_name_print", "in_list_view", "1", "Check")
    # upsert_property_setter(DT, "sr_medication_name_print", "in_standard_filter", "0", "Check")

    # upsert_property_setter(DT, "sr_drug_instruction", "in_list_view", "1", "Check")
    # upsert_property_setter(DT, "sr_drug_instruction", "in_standard_filter", "0", "Check")
