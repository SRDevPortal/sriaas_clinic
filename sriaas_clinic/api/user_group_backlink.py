# sriaas_clinic/api/user_group_backlink.py
from __future__ import annotations
import frappe
from typing import Optional, Tuple, Set, List

SEGMENTS = ("Reception", "Fresh", "Repeat")

def _parse_group_name(name: str) -> Tuple[Optional[str], Optional[str]]:
    name = (name or "").strip()
    for seg in SEGMENTS:
        suf = f" {seg}"
        if name.endswith(suf):
            dept = name[: -len(suf)].strip()
            return (dept or None, seg)
    return (None, None)

def _seg_field(seg: str) -> Optional[str]:
    return {
        "Reception": "sr_seg_reception",
        "Fresh": "sr_seg_fresh",
        "Repeat": "sr_seg_repeat",
    }.get(seg)

def _members_fieldname() -> Optional[str]:
    meta = frappe.get_meta("User Group")
    for f in meta.fields:
        if f.fieldtype in ("Table", "Table MultiSelect") and f.options == "User Group Member":
            return f.fieldname
    for guess in ("user_group_members", "users", "members"):
        if meta.has_field(guess):
            return guess
    return None

def _pluck_users(rows: List) -> Set[str]:
    return {
        getattr(r, "user", "")
        for r in (rows or [])
        if (getattr(r, "user", "") and getattr(r, "user", "") != "Administrator")
    }

def _db_set(user: str, field: str, value):
    # direct write, no hooks, don’t bump modified
    frappe.db.set_value("User", user, field, value, update_modified=False)

def _set_flags_for_users(users: Set[str], dept: str, seg: str) -> None:
    seg_field = _seg_field(seg)
    if not seg_field:
        return
    for u in users:
        # set dept if empty; turn ON segment flag
        current_dept = frappe.db.get_value("User", u, "sr_medical_department")
        if not current_dept:
            _db_set(u, "sr_medical_department", dept)
        _db_set(u, seg_field, 1)

def _unset_flags_for_users(users: Set[str], dept: str, seg: str) -> None:
    seg_field = _seg_field(seg)
    if not seg_field:
        return
    for u in users:
        # only uncheck if this group’s dept matches the user’s current dept
        current_dept, rec, fresh, rep = frappe.db.get_value(
            "User",
            u,
            ["sr_medical_department", "sr_seg_reception", "sr_seg_fresh", "sr_seg_repeat"],
        )
        if current_dept != dept:
            continue
        _db_set(u, seg_field, 0)
        # if no segments remain, clear dept
        if not ((rec or 0) or (fresh or 0) or (rep or 0)):
            _db_set(u, "sr_medical_department", None)

def user_group_before_save(doc, method=None):
    """Diff members new vs old and reflect back to User *without firing User hooks*."""
    dept, seg = _parse_group_name(doc.name)
    if not (dept and seg):
        return
    members_field = _members_fieldname()
    if not members_field:
        return

    # NEW state from form
    new_users = _pluck_users(getattr(doc, members_field, []))

    # OLD state from DB
    old_users = set(
        frappe.get_all(
            "User Group Member",
            filters={"parent": doc.name, "parenttype": "User Group"},
            pluck="user",
        )
    )
    old_users.discard("Administrator")

    added   = new_users - old_users
    removed = old_users - new_users

    # tell the system we’re doing backlink DB updates
    frappe.flags.sr_usergroup_backlink_running = True

    try:
        if added:
            _set_flags_for_users(added, dept, seg)      # uses frappe.db.set_value
        if removed:
            _unset_flags_for_users(removed, dept, seg)  # uses frappe.db.set_value
    finally:
        frappe.flags.sr_usergroup_backlink_running = False
