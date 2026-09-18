"""Legacy entry point retained as a guarded compatibility wrapper."""
import frappe
from .bulk_clearance import process_file_settle_invoices as _process


@frappe.whitelist(methods=["POST"])
def process_file(file_url="/files/sample.csv", submit=0, clearing_account=None):
    return _process(file_url, submit, clearing_account)
