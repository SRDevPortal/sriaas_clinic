"""Output entry points owned by Sriaas Clinic."""
from privacy_shield.outputs import (
    export_data, export_query, export_numbers, download_pdf as _download_pdf, get_html_and_style,
)


import frappe


@frappe.whitelist()
def download_pdf(doctype, name, format=None, doc=None, no_letterhead=0,
                 language=None, letterhead=None, pdf_generator=None):
    from sriaas_clinic.pilot_pdf import GENERATOR, require_access
    if pdf_generator != GENERATOR:
        return _download_pdf(doctype, name, format, doc, no_letterhead, language, letterhead, pdf_generator)
    # Native RPC validates generator arguments against wkhtmltopdf/chrome. Select
    # our registered hook through request-local state, after all pilot checks.
    original = frappe.local.form_dict
    frappe.local.form_dict = frappe._dict(original, doctype=doctype, name=name,
                                          doc=doc, pdf_generator=GENERATOR)
    try:
        require_access(format)
        return _download_pdf(doctype, name, format, doc, no_letterhead, language, letterhead, None)
    finally:
        frappe.local.form_dict = original
