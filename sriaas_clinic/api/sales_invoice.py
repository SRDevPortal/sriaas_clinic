import frappe
from frappe import _


@frappe.whitelist()
def get_sales_invoice_series_config():
    return {
        "sales_invoice_series": frappe.conf.get("sales_invoice_series"),
        "credit_note_series": frappe.conf.get("credit_note_series"),
    }


def set_sales_invoice_series(doc, method=None):
    if doc.docstatus != 0:
        return

    series = _get_series_for_doc(doc)
    if not series:
        return

    if doc.is_new() or not doc.naming_series:
        doc.naming_series = series


def validate_sales_invoice_series(doc, method=None):
    if doc.docstatus != 0:
        return

    series = _get_series_for_doc(doc)
    series_type = "credit_note_series" if doc.is_return else "sales_invoice_series"

    if not series:
        frappe.throw(_("Please set {0} in site config.").format(series_type))

    if doc.naming_series != series:
        frappe.throw(
            _("Sales Invoice series must be {0} for this site.").format(
                frappe.bold(series)
            )
        )


def _get_series_for_doc(doc):
    config = get_sales_invoice_series_config()
    if doc.is_return:
        return config.get("credit_note_series")

    return config.get("sales_invoice_series")
