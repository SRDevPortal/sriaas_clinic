# apps/sriaas_clinic/sriaas_clinic/api/crm_lead_assignment.py
from __future__ import annotations
import frappe
from frappe.desk.form import assign_to

DOCTYPE = "CRM Lead"

# -----------------------------
# Internal helpers
# -----------------------------

def _set_assignment(doctype: str, name: str, user: str | None) -> None:
    """Replace existing assignments with exactly one assignee (user), or clear if None."""
    # always clear first (idempotent)
    assign_to.clear(doctype, name)
    if user:
        # assign_to.add expects a LIST for "assign_to"
        assign_to.add(
            {
                "assign_to": [user],
                "doctype": doctype,
                "name": name,
                "description": "Lead Owner",
                "notify": 0,
            },
            # ← make sure TL can assign even if assignee currently lacks access
            ignore_permissions=True,
        )

def _remove_all_user_shares(doctype: str, name: str) -> None:
    """Remove all DocShare rows for this document (plain delete, no commit)."""
    frappe.db.delete("DocShare", {"share_doctype": doctype, "share_name": name})
    # don't commit here; let the outer request/transaction commit

def _ensure_share(doctype: str, name: str, user: str) -> None:
    """Create a single read+write share row for 'user' (robust to perms)."""
    # de-dupe any older rows first
    frappe.db.delete("DocShare", {
        "share_doctype": doctype,
        "share_name": name,
        "user": user,
    })
    frappe.get_doc({
        "doctype": "DocShare",
        "share_doctype": doctype,
        "share_name": name,
        "user": user,
        "read": 1,
        "write": 1,
        "share": 0,
        "notify_by_email": 0,
    }).insert(ignore_permissions=True)

def _sync_from_owner(doc) -> None:
    """
    Mirror doc.lead_owner -> Assignment + DocShare.
    - If owner is present: one Assignment, one DocShare (RW) for that user.
    - If owner is blank: clear Assignment and all DocShare rows.
    """
    if doc.doctype != DOCTYPE:
        return

    owner = (doc.lead_owner or "").strip()

    # 1) Assignment
    _set_assignment(doc.doctype, doc.name, owner or None)

    # 2) DocShare (clean slate, then add one if owner present)
    _remove_all_user_shares(doc.doctype, doc.name)
    if owner:
        _ensure_share(doc.doctype, doc.name, owner)

# -----------------------------
# Hooks
# -----------------------------

def after_insert(doc, method: str | None = None) -> None:
    try:
        _sync_from_owner(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Lead Owner sync (after_insert) failed")

def on_update(doc, method: str | None = None) -> None:
    try:
        _sync_from_owner(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Lead Owner sync (on_update) failed")

# -----------------------------
# Utilities (optional)
# -----------------------------

@frappe.whitelist()
def resync_all_leads() -> dict:
    names = frappe.get_all(DOCTYPE, pluck="name")
    for name in names:
        d = frappe.get_doc(DOCTYPE, name)
        _sync_from_owner(d)
    return {"status": "ok", "count": len(names)}
