# sriaas_clinic/sriaas_clinic/api/bulk_clearance.py
import frappe
import csv
import os
import traceback
from frappe.utils import flt, getdate, nowdate

@frappe.whitelist()
def process_file(file_url="/files/sample.csv", submit=0, clearing_account=None):
    """
    Process bulk clearance CSV and create Journal Entries (Debit Clearing -> Credit Customer).
    Params:
      - file_url: '/files/sample.csv' or absolute server path
      - submit: 0 => dry run (default), 1 => create & submit JEs
      - clearing_account: optional override (string). Default: "Clearing account - SR"
    Returns:
      dict { processed: [...], skipped: [...], errors: [...], log_file: "/files/..." }
    """
    submit = bool(int(submit))
    try:
        site_path = frappe.get_site_path()

        # Resolve CSV path
        if file_url.startswith("/files/"):
            csv_path = os.path.join(site_path, "public", file_url.lstrip("/"))
        else:
            csv_path = file_url

        if not os.path.exists(csv_path):
            frappe.throw(f"CSV not found at: {csv_path}")

        # Default clearing account
        if not clearing_account:
            clearing_account = "Clearing account - SR"

        # Read CSV and normalize headers to lowercase
        rows = []
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                normalized = { (k.strip().lower() if k else k): (v.strip() if isinstance(v, str) else v) for k, v in r.items() }
                rows.append(normalized)

        result = {"processed": [], "skipped": [], "errors": []}
        log_rows = []

        for idx, row in enumerate(rows, start=1):
            invoice = (row.get("invoice")
                        or row.get("id")
                        or row.get("ID")
                        or row.get("sales_invoice")
                        or row.get("sinv")
                        or row.get("order id")
                        or row.get("order_id")
                        or "").strip()
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

            # determine amount (csv amount if present else outstanding)
            amount = None
            if row.get("amount"):
                try:
                    amount = flt(row.get("amount"))
                except:
                    amount = None
            if not amount:
                amount = flt(si.get("outstanding_amount") or si.get("grand_total") or 0)

            if amount <= 0:
                result["skipped"].append({"row": idx, "invoice": invoice, "reason": f"invalid amount {amount}"})
                log_rows.append([idx, invoice, "skipped", f"invalid amount {amount}", ""])
                continue

            posting_date = row.get("remittance_date") or nowdate()
            # build remarks
            remarks_parts = [f"Clearance for Invoice {invoice}"]
            for k in ("remittance_date", "utr", "awb", "crf_id", "courier"):
                if row.get(k):
                    remarks_parts.append(f"{k.upper()}: {row.get(k)}")
            remarks = " | ".join(remarks_parts)

            # idempotency: skip if JE exists with same remark or similar reference
            existing = _find_existing_je(invoice, amount)
            if existing:
                result["skipped"].append({"row": idx, "invoice": invoice, "reason": f"je_exists:{existing}"})
                log_rows.append([idx, invoice, "skipped", f"je_exists:{existing}", existing])
                continue

            if not submit:
                # dry run
                result["processed"].append({"row": idx, "invoice": invoice, "amount": amount, "action": "dry_run", "posting_date": posting_date})
                log_rows.append([idx, invoice, "dry_run", "", ""])
                continue

            # create & submit JE
            try:
                je_name = _create_and_submit_je(si, amount, posting_date, remarks, clearing_account)
                result["processed"].append({"row": idx, "invoice": invoice, "amount": amount, "je": je_name})
                log_rows.append([idx, invoice, "created", "", je_name])
            except Exception as e:
                tb = traceback.format_exc()
                frappe.log_error(tb, "bulk_clearance_error")
                result["errors"].append({"row": idx, "invoice": invoice, "error": str(e)})
                log_rows.append([idx, invoice, "error", str(e), ""])

        # write log CSV to public files and return URL
        log_file = _write_log_csv(log_rows)
        result["log_file"] = log_file
        return result

    except Exception as outer:
        frappe.log_error(traceback.format_exc(), "bulk_clearance_outer_error")
        frappe.throw(str(outer))


def _find_existing_je(invoice, amount):
    """Return JE name if exists - checks remark text and accounts table for match."""
    like_remark = f"%Clearance for Invoice {invoice}%"
    res = frappe.db.get_all("Journal Entry", filters=[["remark", "like", like_remark]], fields=["name"], limit_page_length=1)
    if res:
        return res[0].get("name")
    # extra check: JE with matching credit and party (customer) in accounts table
    customer = frappe.db.get_value("Sales Invoice", invoice, "customer")
    if customer:
        res2 = frappe.db.sql("""
            select je.name from `tabJournal Entry` je
            join `tabJournal Entry Account` ja on ja.parent = je.name
            where ja.credit = %s and ja.party = %s
            limit 1
        """, (amount, customer), as_dict=True)
        if res2:
            return res2[0].name
    return None


def _create_and_submit_je(si, amount, posting_date, remarks, clearing_account):
    receivable = _get_receivable_account(si.company)
    if not receivable:
        frappe.throw(f"Receivable account not found for company {si.company}")

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = si.company
    je.posting_date = getdate(posting_date)
    je.remark = remarks

    # Debit clearing
    je.append("accounts", {
        "account": clearing_account,
        "debit": flt(amount),
        "credit": 0.0
    })

    # Credit receivable (customer)
    je.append("accounts", {
        "account": receivable,
        "debit": 0.0,
        "credit": flt(amount),
        "party_type": "Customer",
        "party": si.customer
    })

    je.insert(ignore_permissions=True)
    je.submit()
    return je.name


def _get_receivable_account(company):
    acc = frappe.get_value("Account", {"company": company, "account_type": "Receivable"}, "name")
    if acc:
        return acc
    candidates = frappe.get_all("Account", filters={"company": company}, fields=["name"])
    for c in candidates:
        n = (c.get("name") or "").lower()
        if "receivable" in n or "debtors" in n or "accounts receivable" in n:
            return c["name"]
    return None


def _write_log_csv(rows):
    """rows: list of [row, invoice, status, error, je]"""
    site_path = frappe.get_site_path()
    files_dir = os.path.join(site_path, "public", "files")
    os.makedirs(files_dir, exist_ok=True)
    fname = f"bulk_clearance_log_{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}.csv"
    fpath = os.path.join(files_dir, fname)
    with open(fpath, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["row", "invoice", "status", "error", "je"])
        for r in rows:
            writer.writerow(r)
    return "/files/" + fname
