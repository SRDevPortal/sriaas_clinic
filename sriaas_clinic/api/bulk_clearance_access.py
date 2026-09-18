"""Authorization and bounded local input for the bulk-clearance workflow."""
from pathlib import Path
from urllib.parse import urlsplit, unquote
import csv
import frappe

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 1000


def authorize(submit):
    if str(submit) not in ("0", "1"):
        raise frappe.ValidationError("Submit must be 0 or 1.")
    submit = str(submit) == "1"
    roles = set(frappe.get_roles())
    allowed = {"System Manager", "Accounts Manager"} if submit else {"System Manager", "Accounts Manager", "Accounts User"}
    if frappe.session.user == "Guest" or not roles.intersection(allowed):
        raise frappe.PermissionError("Accounting permissions are required for bulk clearance.")
    frappe.has_permission("Sales Invoice", "read", throw=True)
    if submit:
        frappe.has_permission("Payment Entry", "create", throw=True)
        frappe.has_permission("Payment Entry", "submit", throw=True)
    if frappe.conf.get("privacy_shield_desk_enabled", False):
        from privacy_shield.policy import current_capabilities
        caps = current_capabilities()
        if not caps.view_full or (submit and not caps.edit_original):
            raise frappe.PermissionError("Bulk clearance is not available for your privacy permissions.")
    return submit


def read_rows(value):
    if not isinstance(value, str) or not value:
        raise frappe.ValidationError("Select an uploaded CSV File.")
    if value.startswith(("/files/", "/private/files/")):
        names = frappe.get_all("File", filters={"file_url": value}, pluck="name", limit_page_length=101)
        if len(names) > 100:
            raise frappe.PermissionError("File references require review.")
        docs = [frappe.get_doc("File", name) for name in names]
        doc = next((d for d in docs if d.has_permission("read")), None)
        if doc is None:
            raise frappe.PermissionError("The CSV File is not accessible.")
    elif "/" not in value and chr(92) not in value and frappe.db.exists("File", value):
        doc = frappe.get_doc("File", value)
        doc.check_permission("read")
    else:
        raise frappe.PermissionError("Select a local File record; filesystem paths are not accepted.")
    url = doc.file_url or ""
    if not url.startswith(("/files/", "/private/files/")) or urlsplit(url).query or urlsplit(url).fragment:
        raise frappe.ValidationError("Only local CSV files are supported.")
    if any(part in (".", "..") for part in unquote(url).split("/")):
        raise frappe.PermissionError("Invalid local File path.")
    root = Path(frappe.get_site_path("private/files" if url.startswith("/private/files/") else "public/files")).resolve()
    path = Path(doc.get_full_path()).resolve()
    if not path.is_relative_to(root) or path.suffix.lower() != ".csv":
        raise frappe.PermissionError("Select a CSV file within site file storage.")
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise frappe.ValidationError("CSV is missing or exceeds the 5 MB limit.")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = {str(k).strip().lower() for k in reader.fieldnames or []}
        if not headers.intersection({"invoice", "id", "sinv"}):
            raise frappe.ValidationError("CSV requires an invoice, id or sinv column.")
        rows = []
        for row in reader:
            if len(rows) >= MAX_ROWS:
                raise frappe.ValidationError("Process at most 1000 rows per file.")
            rows.append({k.strip().lower() if k else k: v.strip() if isinstance(v, str) else v for k, v in row.items()})
    return rows


def checked_invoices(rows, submit, clearing_account):
    """Authorize all referenced documents before starting accounting mutations."""
    invoices = {}
    for row in rows:
        name = row.get("invoice") or row.get("id") or row.get("sinv")
        if not name or name in invoices:
            continue
        try:
            doc = frappe.get_doc("Sales Invoice", name)
            doc.check_permission("read")
        except (frappe.DoesNotExistError, frappe.PermissionError):
            raise frappe.PermissionError("One or more invoices are unavailable or not accessible.") from None
        if submit and doc.docstatus != 1:
            raise frappe.ValidationError("Only submitted invoices can be settled.")
        invoices[name] = doc
    if submit:
        account = frappe.get_doc("Account", clearing_account)
        account.check_permission("read")
        if account.is_group or account.disabled:
            raise frappe.ValidationError("Select an active ledger account.")
        if any(doc.company != account.company for doc in invoices.values()):
            raise frappe.ValidationError("The clearing account must belong to each invoice's company.")
    return invoices
