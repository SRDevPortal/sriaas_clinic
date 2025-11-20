# sriaas_clinic/sriaas_clinic/api/bulk_clearance.py
import frappe
import csv, os, traceback
from frappe.utils import flt, nowdate

@frappe.whitelist()
def process_file_settle_invoices(file_url="/files/sample.csv", submit=0, clearing_account=None):
    """
    Bulk settle invoices using Payment Entry (Receive) with paid_to = clearing_account.
    - file_url: '/files/sample.csv' or absolute path
    - submit: 0 -> dry run (default), 1 -> create & submit Payment Entries
    - clearing_account: optional override ledger name (default "Clearing account - SR")
    Returns: dict { processed:[], skipped:[], errors:[], log_file: "/files/..." }
    CSV expected header: invoice (or id). optional columns: amount, remittance_date, utr, awb, crf_id, courier
    """
    submit = bool(int(submit))
    try:
        site_path = frappe.get_site_path()
        if file_url.startswith("/files/"):
            csv_path = os.path.join(site_path, "public", file_url.lstrip("/"))
        else:
            csv_path = file_url

        if not os.path.exists(csv_path):
            frappe.throw(f"CSV not found: {csv_path}")

        if not clearing_account:
            clearing_account = "Clearing account - SR"

        # read csv
        rows = []
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                # normalize keys to lowercase
                normalized = { (k.strip().lower() if k else k): (v.strip() if isinstance(v, str) else v) for k, v in r.items() }
                rows.append(normalized)

        result = {"processed": [], "skipped": [], "errors": []}
        log_rows = []

        for idx, row in enumerate(rows, start=1):
            try:
                # get invoice id from several possible headers
                invoice = (row.get("invoice") or row.get("id") or row.get("sinv") or "").strip()
                if not invoice:
                    result["skipped"].append({"row": idx, "reason": "missing invoice"})
                    log_rows.append([idx, "", "skipped", "missing invoice", ""])
                    continue

                # fetch sales invoice
                si = None
                try:
                    si = frappe.get_doc("Sales Invoice", invoice)
                except Exception as e:
                    result["errors"].append({"row": idx, "invoice": invoice, "error": f"invoice not found: {e}"})
                    log_rows.append([idx, invoice, "error", f"invoice not found: {e}", ""])
                    continue

                # determine amount: CSV amount overrides outstanding
                amount = None
                if row.get("amount"):
                    try:
                        amount = flt(row.get("amount"))
                    except:
                        amount = None

                if not amount:
                    amount = flt(si.get("outstanding_amount") or 0)

                if amount <= 0:
                    result["skipped"].append({"row": idx, "invoice": invoice, "reason": f"invalid amount {amount}"})
                    log_rows.append([idx, invoice, "skipped", f"invalid amount {amount}", ""])
                    continue

                posting_date = row.get("remittance_date") or nowdate()
                # simple remarks with metadata
                remarks_parts = [f"Clearing payment for {invoice}"]
                for k in ("utr","awb","crf_id","courier"):
                    if row.get(k):
                        remarks_parts.append(f"{k.upper()}: {row.get(k)}")
                remarks = " | ".join(remarks_parts)

                # idempotency: skip if a Payment Entry exists referencing this invoice
                existing_pe = _find_existing_payment_entry(invoice)
                if existing_pe:
                    result["skipped"].append({"row": idx, "invoice": invoice, "reason": f"payment_exists:{existing_pe}"})
                    log_rows.append([idx, invoice, "skipped", f"payment_exists:{existing_pe}", existing_pe])
                    continue

                # dry-run
                if not submit:
                    result["processed"].append({"row": idx, "invoice": invoice, "amount": amount, "posting_date": posting_date, "action": "dry_run"})
                    log_rows.append([idx, invoice, "dry_run", "", ""])
                    continue

                # create payment entry and submit
                pe_name = _create_payment_entry_and_allocate(invoice, si, amount, posting_date, clearing_account, remarks)
                result["processed"].append({"row": idx, "invoice": invoice, "amount": amount, "payment_entry": pe_name})
                log_rows.append([idx, invoice, "created", "", pe_name])

            except Exception as e:
                tb = traceback.format_exc()
                frappe.log_error(tb, "bulk_settle_error")
                result["errors"].append({"row": idx, "invoice": row.get("invoice"), "error": str(e)})
                log_rows.append([idx, row.get("invoice"), "error", str(e), ""])

        # write log csv to files
        log_file = _write_log_csv_common(log_rows)
        result["log_file"] = log_file
        return result

    except Exception as outer:
        frappe.log_error(traceback.format_exc(), "bulk_settle_outer")
        frappe.throw(str(outer))


def _find_existing_payment_entry(invoice):
    """
    Correct idempotency check: search Payment Entry child table (tabPayment Entry Reference)
    that references the invoice. Returns Payment Entry name if found, else None.
    """
    if not invoice:
        return None

    # Use the Payment Entry Reference child table to find a payment referencing this invoice
    res = frappe.db.sql(
        "SELECT parent FROM `tabPayment Entry Reference` WHERE reference_name = %s LIMIT 1",
        (invoice,),
        as_dict=True
    )
    if res and len(res) > 0:
        return res[0].get("parent")
    return None


def _create_payment_entry_and_allocate(invoice_name, si_doc, amount, posting_date, paid_to_account, remarks):
    """
    Create & submit a Payment Entry (Receive) to allocate `amount` to invoice_name.
    si_doc: Sales Invoice document (frappe doc) - used for party and amounts
    """
    from frappe.utils import flt, getdate, nowdate

    if flt(amount) <= 0:
        frappe.throw("Invalid amount")

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Receive"
    pe.party_type = "Customer"
    pe.party = si_doc.customer
    pe.party_name = si_doc.get("customer_name")
    pe.company = si_doc.company
    pe.posting_date = getdate(posting_date) if posting_date else nowdate()
    pe.mode_of_payment = "Bank"
    pe.paid_to = paid_to_account
    pe.paid_amount = flt(amount)
    pe.received_amount = flt(amount)
    pe.remark = remarks

    pe.set("references", [{
        "reference_doctype": "Sales Invoice",
        "reference_name": invoice_name,
        "total_amount": si_doc.get("grand_total") or 0,
        "outstanding_amount": si_doc.get("outstanding_amount") or 0,
        "allocated_amount": flt(amount)
    }])

    pe.insert(ignore_permissions=True)
    pe.submit()
    return pe.name


def _write_log_csv_common(rows):
    """Write log rows into /files/ and return URL"""
    site_path = frappe.get_site_path()
    files_dir = os.path.join(site_path, "public", "files")
    os.makedirs(files_dir, exist_ok=True)
    fname = f"bulk_settle_log_{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}.csv"
    fpath = os.path.join(files_dir, fname)
    with open(fpath, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["row","invoice","status","error","payment_entry"])
        for r in rows:
            writer.writerow(r)
    return "/files/" + fname
# End of sriaas_clinic/sriaas_clinic/api/bulk_clearance.py