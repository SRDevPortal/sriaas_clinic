# sriaas_clinic/sriaas_clinic/api/bulk_clearance.py
import frappe
import csv, io, traceback
from .bulk_clearance_access import authorize, read_rows, checked_invoices
from frappe.utils import flt, nowdate, getdate

@frappe.whitelist(methods=["POST"])
def process_file_settle_invoices(file_url="/files/sample.csv", submit=0, clearing_account=None):
    """
    Improved: Bulk settle invoices using Payment Entry (Receive) with paid_to = clearing_account.
    Supports multiple trenches: if invoice already has partial payments, will only pay outstanding.
    - file_url: a readable local File URL or File record ID (CSV, at most 5 MB/1000 rows)
    - submit: 0 -> dry run (default), 1 -> create & submit Payment Entries
    - clearing_account: optional override ledger name (default "Clearing account - SR")
    CSV expected header: invoice (or id). optional columns: amount, remittance_date, utr, awb, crf_id, courier
    """
    submit = authorize(submit)
    rows = read_rows(file_url)
    clearing_account = clearing_account or "Clearing account - SR"
    invoices = checked_invoices(rows, submit, clearing_account)
    try:
        result = {"processed": [], "skipped": [], "errors": []}
        log_rows = []

        for idx, row in enumerate(rows, start=1):
            try:
                invoice = (row.get("invoice") or row.get("id") or row.get("sinv") or "").strip()
                if not invoice:
                    result["skipped"].append({"row": idx, "reason": "missing invoice"})
                    log_rows.append([idx, "", "skipped", "missing invoice", ""])
                    continue

                si = invoices[invoice]

                # current outstanding on invoice at time of run
                current_outstanding = flt(si.get("outstanding_amount") or 0)

                # determine requested_amount: CSV amount overrides outstanding (but we'll cap later)
                requested_amount = None
                if row.get("amount"):
                    try:
                        requested_amount = flt(row.get("amount"))
                    except:
                        requested_amount = None

                # If no amount provided, we intend to pay full outstanding
                if not requested_amount:
                    requested_amount = current_outstanding

                # If outstanding is zero at this moment, skip
                if current_outstanding <= 0:
                    result["skipped"].append({"row": idx, "invoice": invoice, "reason": "already_settled"})
                    log_rows.append([idx, invoice, "skipped", "already_settled", ""])
                    continue

                # Decide allocate_amount = min(requested_amount, current_outstanding)
                allocate_amount = min(flt(requested_amount), current_outstanding)

                if allocate_amount <= 0:
                    result["skipped"].append({"row": idx, "invoice": invoice, "reason": f"invalid_allocate_amount:{allocate_amount}"})
                    log_rows.append([idx, invoice, "skipped", f"invalid_allocate_amount:{allocate_amount}", ""])
                    continue

                posting_date = row.get("remittance_date") or nowdate()
                remarks_parts = [f"Clearing payment for {invoice}"]
                for k in ("utr","awb","crf_id","courier"):
                    if row.get(k):
                        remarks_parts.append(f"{k.upper()}: {row.get(k)}")
                remarks = " | ".join(remarks_parts)

                # dry-run: report what would be created (including if we truncated requested -> allocate_amount)
                if not submit:
                    note = ""
                    if flt(requested_amount) != flt(allocate_amount):
                        note = f"requested {requested_amount} truncated to {allocate_amount} due to outstanding {current_outstanding}"
                    result["processed"].append({
                        "row": idx,
                        "invoice": invoice,
                        "requested_amount": requested_amount,
                        "allocated_amount": allocate_amount,
                        "posting_date": posting_date,
                        "note": note,
                        "action": "dry_run"
                    })
                    log_rows.append([idx, invoice, "dry_run", note, ""])
                    continue

                # create payment entry & allocate only the allocate_amount
                pe_name = _create_payment_entry_and_allocate(invoice, si, allocate_amount, posting_date, clearing_account, remarks)
                result["processed"].append({"row": idx, "invoice": invoice, "amount": allocate_amount, "payment_entry": pe_name})
                log_rows.append([idx, invoice, "created", "", pe_name])

            except frappe.PermissionError:
                raise
            except Exception as e:
                tb = traceback.format_exc()
                frappe.log_error(tb, "bulk_settle_error")
                result["errors"].append({"row": idx, "invoice": row.get("invoice"), "error": str(e)})
                log_rows.append([idx, row.get("invoice"), "error", str(e), ""])

        # write log csv to files
        log_file = _write_log_csv_common(log_rows)
        result["log_file"] = log_file
        return result

    except frappe.PermissionError:
        raise
    except Exception as outer:
        frappe.log_error(traceback.format_exc(), "bulk_settle_outer")
        frappe.throw(str(outer))

def _create_payment_entry_and_allocate(invoice_name, si_doc, amount, posting_date, paid_to_account, remarks):
    """
    Create & submit a Payment Entry (Receive) to allocate `amount` to invoice_name.
    si_doc: Sales Invoice document (frappe doc)
    """
    from frappe.utils import flt, getdate, nowdate

    if flt(amount) <= 0:
        frappe.throw("Invalid amount")

    # Refresh invoice doc to get real-time outstanding before creating PE
    si_doc = frappe.get_doc("Sales Invoice", si_doc.name)
    si_doc.check_permission("read")

    # If outstanding changed since earlier check, cap again
    current_outstanding = flt(si_doc.get("outstanding_amount") or 0)
    allocate_amount = min(flt(amount), current_outstanding)
    if allocate_amount <= 0:
        frappe.throw(f"Invoice {invoice_name} has no outstanding to allocate (current_outstanding={current_outstanding})")

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Receive"
    pe.party_type = "Customer"
    pe.party = si_doc.customer
    pe.party_name = si_doc.get("customer_name")
    pe.company = si_doc.company
    pe.posting_date = getdate(posting_date) if posting_date else nowdate()
    pe.mode_of_payment = "Bank"
    pe.paid_to = paid_to_account
    pe.paid_amount = flt(allocate_amount)
    pe.received_amount = flt(allocate_amount)
    pe.remark = remarks

    pe.set("references", [{
        "reference_doctype": "Sales Invoice",
        "reference_name": invoice_name,
        "total_amount": si_doc.get("grand_total") or 0,
        "outstanding_amount": si_doc.get("outstanding_amount") or 0,
        "allocated_amount": flt(allocate_amount)
    }])

    pe.insert()
    pe.submit()
    return pe.name

def _write_log_csv_common(rows):
    """Create an owner-accessible private File, never a public report path."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["row", "invoice", "status", "error_or_note", "reference"])
    for row in rows:
        cells = (list(row) + [""] * 5)[:5]
        # Keep user-controlled text from becoming spreadsheet formulas.
        writer.writerow(["'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@"))
                         else value for value in cells])
    doc = frappe.get_doc({
        "doctype": "File",
        "file_name": "bulk_settle_log_" + frappe.generate_hash(length=16) + ".csv",
        "content": output.getvalue(),
        "is_private": 1,
    })
    doc.insert()
    return doc.file_url


@frappe.whitelist(methods=["POST"])
def process_file_from_ui(file_value, submit=0, clearing_account=None):
    """The UI and direct API use the same authorization and File resolution."""
    return process_file_settle_invoices(file_value, submit, clearing_account)
