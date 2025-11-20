# sriaas_clinic/sriaas_clinic/api/bulk_clearance.py
import frappe
import csv, os, traceback
from frappe.utils import flt, nowdate, getdate

@frappe.whitelist()
def process_file_settle_invoices(file_url="/files/sample.csv", submit=0, clearing_account=None):
    """
    Improved: Bulk settle invoices using Payment Entry (Receive) with paid_to = clearing_account.
    Supports multiple trenches: if invoice already has partial payments, will only pay outstanding.
    - file_url: '/files/sample.csv' or absolute path
    - submit: 0 -> dry run (default), 1 -> create & submit Payment Entries
    - clearing_account: optional override ledger name (default "Clearing account - SR")
    CSV expected header: invoice (or id). optional columns: amount, remittance_date, utr, awb, crf_id, courier
    """
    submit = bool(int(submit))
    try:
        site_path = frappe.get_site_path()
        # Resolve full path properly for both public & private files
        if file_url.startswith("/files/"):
            csv_path = os.path.join(site_path, "public", file_url.lstrip("/"))
        elif file_url.startswith("/private/files/"):
            csv_path = os.path.join(site_path, "private", "files", os.path.basename(file_url))
        else:
            # fallback (absolute path or unknown)
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
                normalized = { (k.strip().lower() if k else k): (v.strip() if isinstance(v, str) else v) for k, v in r.items() }
                rows.append(normalized)

        result = {"processed": [], "skipped": [], "errors": []}
        log_rows = []

        for idx, row in enumerate(rows, start=1):
            try:
                invoice = (row.get("invoice") or row.get("id") or row.get("sinv") or "").strip()
                if not invoice:
                    result["skipped"].append({"row": idx, "reason": "missing invoice"})
                    log_rows.append([idx, "", "skipped", "missing invoice", ""])
                    continue

                # fetch sales invoice
                try:
                    si = frappe.get_doc("Sales Invoice", invoice)
                except Exception as e:
                    result["errors"].append({"row": idx, "invoice": invoice, "error": f"invoice not found: {e}"})
                    log_rows.append([idx, invoice, "error", f"invoice not found: {e}", ""])
                    continue

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

    pe.insert(ignore_permissions=True)
    pe.submit()
    return pe.name

def _write_log_csv_common(rows):
    """
    Write rows to a CSV file inside sites/<site>/public/files and return the web path (/files/...)
    rows: list of [row, invoice, status, error_or_note, reference_name]
    """
    import os
    site_path = frappe.get_site_path()
    files_dir = os.path.join(site_path, "public", "files")
    os.makedirs(files_dir, exist_ok=True)
    fname = f"bulk_settle_log_{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}.csv"
    fpath = os.path.join(files_dir, fname)
    try:
        with open(fpath, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["row", "invoice", "status", "error_or_note", "reference"])
            for r in rows:
                # ensure row has 5 columns
                out = list(r) + [""] * (5 - len(r))
                writer.writerow(out[:5])
    except Exception as e:
        frappe.log_error(f"Could not write log CSV: {e}\n{frappe.get_traceback()}", "bulk_settle_log_write_error")
        # still return intended path so caller can inspect error log
    return "/files/" + fname

@frappe.whitelist()
def process_file_from_ui(file_value, submit=0, clearing_account=None):
    """
    UI wrapper for Bulk Clearance Upload.
    - file_value: value from Attach field (either '/files/xxx.csv' or File docname)
    - submit: 0 => dry-run, 1 => actual
    - clearing_account: optional ledger override
    Returns: result dict from process_file_settle_invoices
    """
    # Resolve file_url:
    if not file_value:
        frappe.throw("Please attach a CSV file in the CSV File field.")

    file_url = None

    # If the Attach stores a File docname, fetch the file_url.
    try:
        if file_value.startswith("/files/"):
            file_url = file_value
        elif frappe.db.exists("File", file_value):
            file_doc = frappe.get_doc("File", file_value)
            file_url = file_doc.file_url
        else:
            # Sometimes Attach returns the filename only; try /files/<value>
            if file_value.endswith(".csv"):
                tentative = "/files/" + os.path.basename(file_value)
                # check file exists physically
                site_path = frappe.get_site_path()
                path = os.path.join(site_path, "public", tentative.lstrip("/"))
                if os.path.exists(path):
                    file_url = tentative
            # fallback to treating as direct URL
            if not file_url:
                file_url = file_value
    except Exception:
        # fallback safe behavior
        file_url = file_value

    # Call your main processor. This function must exist in this module:
    # process_file_settle_invoices(file_url, submit, clearing_account)
    # convert submit to int
    submit_flag = int(submit) if submit is not None else 0

    # Security: only allow users with appropriate roles to run actual submission
    if submit_flag == 1:
        # server-side role check using frappe.get_roles()
        try:
            current_user = frappe.session.user
        except Exception:
            current_user = None

        allowed_roles = {"System Manager", "Accounts Manager"}

        user_roles = set(frappe.get_roles(current_user or frappe.session.user))
        if not (user_roles & allowed_roles):
            frappe.throw("You are not authorized to perform this action. Ask System Manager or Accounts Manager to run actual process.")

    # call the processor
    return process_file_settle_invoices(
        file_url=file_url,
        submit=submit_flag,
        clearing_account=clearing_account
    )
