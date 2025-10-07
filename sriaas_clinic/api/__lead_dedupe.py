from __future__ import annotations
import re
from typing import Optional, Dict, Any, List
import frappe
from frappe import _

DT = "CRM Lead"

# ----------------- helpers -----------------

def _mobile_key(doc_or_value: Any) -> str:
    """Use the exact cleaned mobile_no as the dedupe key (no extra normalization)."""
    if isinstance(doc_or_value, str):
        return (doc_or_value or "").strip()
    if hasattr(doc_or_value, "mobile_no"):
        v = doc_or_value.mobile_no or ""
        return v.strip()
    return ""

def _fieldnames(doctype: str) -> set:
    meta = frappe.get_meta(doctype)
    try:
        return {df.fieldname for df in getattr(meta, "fields", []) if getattr(df, "fieldname", None)}
    except Exception:
        return {f.get("fieldname") for f in (meta.get("fields") or []) if f.get("fieldname")}

def _get_all_for_mobile_key(mobile_key: str) -> List[Dict[str, Any]]:
    """Fetch all leads that have the exact same mobile_no value, newest first."""
    if not mobile_key:
        return []
    fns = _fieldnames(DT)
    base = ["name", "creation", "owner", "status", "source", "mobile_no"]
    opt  = [
        "sr_lead_country","sr_lead_message","sr_landing_page","sr_vpn_status",
        "sr_ip_address","sr_remote_location","sr_user_agent"
    ]
    cols = base + [c for c in opt if c in fns]
    select_clause = ", ".join(cols)
    rows = frappe.db.sql(
        f"""select {select_clause}
              from `tab{DT}`
             where coalesce(mobile_no,'')=%s and docstatus<2
             order by creation desc""",
        (mobile_key,), as_dict=True
    )
    return rows

def _apply_archive_grouping(mobile_key: str) -> None:
    """
    New rule:
      - NEWEST = primary/visible → sr_is_archived=0, sr_is_latest=1
      - OLDER = archived/hidden → sr_is_archived=1, sr_is_latest=0
      - All point sr_primary_lead -> newest
      - Primary sr_duplicate_count = number of archived
    """
    rows = _get_all_for_mobile_key(mobile_key)
    if not rows:
        return
    primary = rows[0]["name"]
    older   = [r["name"] for r in rows[1:]]
    dup_cnt = len(older)

    # primary
    frappe.db.set_value(DT, primary, "sr_is_latest", 1)
    frappe.db.set_value(DT, primary, "sr_is_archived", 0)
    frappe.db.set_value(DT, primary, "sr_primary_lead", primary)
    frappe.db.set_value(DT, primary, "sr_duplicate_count", dup_cnt)

    # older
    for nm in older:
        frappe.db.set_value(DT, nm, "sr_is_latest", 0)
        frappe.db.set_value(DT, nm, "sr_is_archived", 1)
        frappe.db.set_value(DT, nm, "sr_primary_lead", primary)
        frappe.db.set_value(DT, nm, "sr_duplicate_count", 0)

# ----------------- doc events -----------------

def on_validate(doc, method=None):
    # Do NOT normalize here; your before_save already cleaned strings.
    # Nothing to do, but keep the hook to be future-proof.
    pass

def on_after_insert(doc, method=None):
    mk = _mobile_key(doc)
    if mk:
        _apply_archive_grouping(mk)

def on_update(doc, method=None):
    mk = _mobile_key(doc)
    if mk:
        _apply_archive_grouping(mk)

def on_trash(doc, method=None):
    mk = _mobile_key(doc)
    if not mk:
        return
    frappe.enqueue(
        "sriaas_clinic.api.lead_dedupe.repair_group",
        queue="short",
        mobile_key=mk,
        now=False,
    )

def repair_group(mobile_key: str):
    _apply_archive_grouping(mobile_key)

# ----------------- UI APIs -----------------

@frappe.whitelist()
def hits(name: str) -> Dict[str, Any]:
    """For the pill: return {count, latest} using exact mobile_no match."""
    doc = frappe.get_doc(DT, name)
    mk = _mobile_key(doc)
    rows = _get_all_for_mobile_key(mk)
    if not rows:
        return {"count": 0, "latest": None}
    return {"count": max(0, len(rows)-1), "latest": rows[0]["name"]}

@frappe.whitelist()
def merged_list(name: str) -> Dict[str, Any]:
    """Modal rows: all older leads for the same exact mobile_no."""
    doc = frappe.get_doc(DT, name)
    mk = _mobile_key(doc)
    rows = _get_all_for_mobile_key(mk)  # newest first
    if not rows:
        return {"latest": None, "data": []}
    latest = rows[0]["name"]
    older  = rows[1:]
    data = [{
        "lead_id": r["name"],
        "owner":   r.get("owner"),
        "stage":   r.get("status"),
        "creation": r.get("creation"),
        "country": r.get("sr_lead_country"),
        "message": r.get("sr_lead_message"),
        "source":  r.get("source"),
        "page_url": r.get("sr_landing_page"),
        "vpn_status": r.get("sr_vpn_status"),
        "remote_ip": r.get("sr_ip_address"),
        "remote_loc": r.get("sr_remote_location"),
        "user_agent": r.get("sr_user_agent"),
    } for r in older]
    return {"latest": latest, "data": data}
