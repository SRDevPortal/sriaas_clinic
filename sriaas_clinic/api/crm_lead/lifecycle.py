# sriaas_clinic/api/crm_lead/lifecycle.py
# after_insert automation for CRM Lead (NO auto-sync on update)

from __future__ import annotations
import frappe
from frappe.desk.form import assign_to

DOCTYPE = "CRM Lead"

# -----------------------------
# Helpers
# -----------------------------

def _set_assignment(doctype: str, name: str, user: str | None) -> None:
    """Replace existing assignments with exactly one assignee (user), or clear if None."""
    assign_to.clear(doctype, name)
    if user:
        assign_to.add(
            {
                "assign_to": [user],
                "doctype": doctype,
                "name": name,
                "description": "Lead Owner",
                "notify": 0,
            },
            ignore_permissions=True,
        )


def _remove_all_user_shares(doctype: str, name: str) -> None:
    """Remove all DocShare rows for this document."""
    frappe.db.delete("DocShare", {
        "share_doctype": doctype,
        "share_name": name,
    })


def _ensure_share(doctype: str, name: str, user: str) -> None:
    """Create a single read+write DocShare row for user."""
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


def _sync_assignment_from_owner_on_insert(doc) -> None:
    """
    ONE-TIME sync on INSERT ONLY.
    lead_owner → Assignment + DocShare.
    """
    if doc.doctype != DOCTYPE:
        return

    owner = (doc.lead_owner or "").strip()

    _set_assignment(doc.doctype, doc.name, owner or None)
    _remove_all_user_shares(doc.doctype, doc.name)

    if owner:
        _ensure_share(doc.doctype, doc.name, owner)


# -----------------------------
# Hooks
# -----------------------------

def after_insert(doc, method: str | None = None) -> None:
    """
    Initial assignment ONLY.
    """
    try:
        _sync_assignment_from_owner_on_insert(doc)
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Lead Owner sync (after_insert) failed",
        )


def on_update(doc, method: str | None = None) -> None:
    """
    Intentionally empty.

    Assignment must NOT auto-sync on update.
    All assignment changes happen via controller APIs.
    """
    return


# -----------------------------
# Utilities (explicit admin use only)
# -----------------------------

@frappe.whitelist()
def resync_all_leads() -> dict:
    """
    Manual admin-only repair tool.
    Does NOT run automatically.
    """
    names = frappe.get_all(DOCTYPE, pluck="name")
    for name in names:
        d = frappe.get_doc(DOCTYPE, name)
        _sync_assignment_from_owner_on_insert(d)
    return {"status": "ok", "count": len(names)}
