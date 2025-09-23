# sriaas_clinic/setup/print_formats.py
import os, frappe
from .utils import MODULE_DEF_NAME, upsert_property_setter

def _load(relpath: str) -> str:
    app_path = frappe.get_app_path("sriaas_clinic")
    with open(os.path.join(app_path, relpath), "r", encoding="utf-8") as f:
        return f.read()

def apply():
    """Create/Update 'Patient Encounter New' Print Format (Jinja)"""
    name = "Patient Encounter New"
    html = _load("print_formats/patient_encounter_new.html")

    payload = {
        "doc_type": "Patient Encounter",
        "module": MODULE_DEF_NAME,     # << use Module Def, not package
        "custom_format": 1,
        "print_format_type": "Jinja",
        "disabled": 0,
        "standard": "No",
        "html": html,
    }

    if frappe.db.exists("Print Format", name):
        pf = frappe.get_doc("Print Format", name)
        pf.update(payload)
        pf.save(ignore_permissions=True)
    else:
        pf = frappe.get_doc({"doctype": "Print Format", "name": name, **payload})
        pf.insert(ignore_permissions=True)
    
    # set this as default for Patient Encounter
    upsert_property_setter("Patient Encounter", None, "default_print_format", name, "Data", module=MODULE_DEF_NAME)

    frappe.clear_cache(doctype="Patient Encounter")
