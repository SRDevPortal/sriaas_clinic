# sriaas_clinic/setup/print_formats.py
import os
import shutil
import subprocess

import frappe
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

def _install_pdf_fonts():
    """
    Register bundled fonts for wkhtmltopdf.

    wkhtmltopdf is more reliable with fontconfig-installed fonts than with
    @font-face URLs/data URIs, especially for Devanagari in generated PDFs.
    """
    app_path = frappe.get_app_path("sriaas_clinic")
    source_dir = os.path.join(app_path, "public", "fonts")
    if not os.path.isdir(source_dir):
        return

    target_dir = os.path.expanduser("~/.local/share/fonts")
    os.makedirs(target_dir, exist_ok=True)

    copied = False
    for filename in os.listdir(source_dir):
        if not filename.lower().endswith((".ttf", ".otf")):
            continue

        source = os.path.join(source_dir, filename)
        target = os.path.join(target_dir, filename)
        shutil.copy2(source, target)
        copied = True

    if copied and shutil.which("fc-cache"):
        subprocess.run(
            ["fc-cache", "-f", target_dir],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

def apply():
    _install_pdf_fonts()
    _upsert_pf("Patient Encounter New", "Patient Encounter", "print_formats/patient_encounter_new.html")
    _upsert_pf("Sales Invoice New", "Sales Invoice", "print_formats/sales_invoice_new.html")
    _upsert_pf("Sales Invoice New2", "Sales Invoice", "print_formats/sales_invoice_new2.html")
    _upsert_pf("Kit Billing Invoice", "Sales Invoice", "print_formats/kit_billing_invoice.html")
    _upsert_pf("Purchase Order New", "Purchase Order", "print_formats/purchase_order_new.html")
