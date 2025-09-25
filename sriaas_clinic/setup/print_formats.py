# sriaas_clinic/setup/print_formats.py
import os, frappe
from .utils import MODULE_DEF_NAME, upsert_property_setter

def _load(relpath: str) -> str:
    app_path = frappe.get_app_path("sriaas_clinic")
    with open(os.path.join(app_path, relpath), "r", encoding="utf-8") as f:
        return f.read()

def _upsert_pf(name: str, doctype: str, relpath: str):
    html = _load(relpath)
    payload = {
        "doc_type": doctype,
        "module": MODULE_DEF_NAME,
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

    # set as default for this doctype
    upsert_property_setter(doctype, None, "default_print_format", name, "Data", module=MODULE_DEF_NAME)
    frappe.clear_cache(doctype=doctype)

def apply():
    # Patient Encounter
    _upsert_pf("Patient Encounter New", "Patient Encounter", "print_formats/patient_encounter_new.html")
    # Sales Invoice
    _upsert_pf("Sales Invoice New", "Sales Invoice", "print_formats/sales_invoice_new.html")
