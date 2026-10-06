# apps/sriaas_clinic/sriaas_clinic/api/user_department_membership.py
from __future__ import annotations
import frappe
from typing import Optional, List

# Segments that become "<Department> <Segment>" user groups
SEGMENTS: List[str] = ["Reception", "Fresh", "Repeat"]

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def _members_field_info():
    """Return (fieldname, field_meta) for the members child table on User Group."""
    meta = frappe.get_meta("User Group")
    # Preferred pointer to 'User Group Member'
    for f in meta.fields:
        if f.fieldtype in ("Table", "Table MultiSelect") and f.options == "User Group Member":
            return f.fieldname, f
    # Fallback guesses
    for guess in ("user_group_members", "users", "members"):
        if meta.has_field(guess):
            return guess, meta.get_field(guess)
    return None, None


def _ensure_group(name: str) -> None:
    if frappe.db.exists("User Group", name):
        return

    doc = frappe.get_doc({"doctype": "User Group", "name": name})
    meta = frappe.get_meta("User Group")
    if meta.has_field("user_group_name"):
        doc.user_group_name = name
    elif meta.has_field("title"):
        doc.title = name

    members_field, fmeta = _members_field_info()
    # If the child table is mandatory, add a seed row so insert() passes
    if members_field and fmeta and getattr(fmeta, "reqd", 0):
        doc.set(members_field, [{"user": "Administrator"}])

    doc.insert(ignore_permissions=True)


def _prune_admin_seed(ug, members_field: str):
    # Only drop the seed admin if:
    #   - the field is NOT mandatory, or
    #   - at least one non-admin member will remain
    _, fmeta = _members_field_info()
    rows = getattr(ug, members_field, []) or []
    keep = [r for r in rows if getattr(r, "user", "") != "Administrator"]

    field_is_reqd = bool(getattr(fmeta, "reqd", 0))
    if field_is_reqd and not keep:
        return  # can't prune; would make it empty and fail validation

    if len(keep) != len(rows):
        setattr(ug, members_field, keep)
        ug.save(ignore_permissions=True)


def _add_user_to_group(user: str, group_name: str) -> None:
    if not frappe.db.exists("User Group", group_name):
        _ensure_group(group_name)

    members_field, fmeta = _members_field_info()
    if not members_field:
        frappe.throw("Could not locate members child table on User Group")

    ug = frappe.get_doc("User Group", group_name)
    ug.reload()

    rows = getattr(ug, members_field, []) or []
    if any(getattr(r, "user", None) == user for r in rows):
        _prune_admin_seed(ug, members_field)
        return

    ug.append(members_field, {"user": user})
    ug.save(ignore_permissions=True)

    # Now that there is at least one real member, prune the seed if allowed
    _prune_admin_seed(ug, members_field)


def _remove_user_from_group(user: str, group_name: str) -> None:
    if not frappe.db.exists("User Group", group_name):
        return

    members_field, fmeta = _members_field_info()
    if not members_field:
        return

    ug = frappe.get_doc("User Group", group_name)
    ug.reload()

    rows = getattr(ug, members_field, []) or []
    keep = [r for r in rows if getattr(r, "user", None) != user]

    # If this would make the list empty but the field is mandatory, leave a seed
    field_is_reqd = bool(getattr(fmeta, "reqd", 0))
    if field_is_reqd and not keep:
        keep = [{"user": "Administrator"}]  # minimal placeholder

    if len(keep) != len(rows):
        setattr(ug, members_field, keep)
        ug.save(ignore_permissions=True)


# ---------------------------------------------------------------------
# Core sync (from in-memory doc) + DB-backed variant for queued calls
# ---------------------------------------------------------------------

def _sync_user_groups_from_doc(user_doc) -> None:
    """
    Reconcile membership using the *current in-memory values* on User.
    Do NOT reload the doc here (after_save hasn't committed yet).
    """
    # skip if the backlink is currently updating the User to avoid loops
    if getattr(frappe.flags, "sr_usergroup_backlink_running", False):
        return

    user_name = user_doc.name
    dept = (getattr(user_doc, "sr_medical_department", None) or "").strip()

    # build desired segments
    selected: List[str] = []
    if dept:
        if getattr(user_doc, "sr_seg_reception", 0): selected.append("Reception")
        if getattr(user_doc, "sr_seg_fresh", 0):     selected.append("Fresh")
        if getattr(user_doc, "sr_seg_repeat", 0):    selected.append("Repeat")

    desired = {f"{dept} {seg}" for seg in selected} if dept else set()

    # current managed memberships (any "<AnyDept> <Segment>")
    current_parents = set(
        frappe.get_all(
            "User Group Member",
            filters={"user": user_name, "parenttype": "User Group"},
            pluck="parent",
        )
    )
    managed_current = {
        g for g in current_parents
        if any(g.endswith(f" {seg}") for seg in SEGMENTS)
    }

    # reconcile
    to_add = desired - managed_current
    to_remove = managed_current - desired

    for g in sorted(to_add):
        _add_user_to_group(user_name, g)
    for g in sorted(to_remove):
        _remove_user_from_group(user_name, g)


# ---------------------------
# Hooks (run inline)
# ---------------------------

def after_insert(doc, method: Optional[str] = None) -> None:
    try:
        _sync_user_groups_from_doc(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "User group sync (after_insert) failed")

def on_update(doc, method: Optional[str] = None) -> None:
    try:
        _sync_user_groups_from_doc(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "User group sync (on_update) failed")

def after_save(doc, method: Optional[str] = None) -> None:
    try:
        _sync_user_groups_from_doc(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "User group sync (after_save) failed")


# -----------------------------------------------------------------------------
# Admin utilities (optional)
# -----------------------------------------------------------------------------

@frappe.whitelist()
def ensure_only_member_in_group(group_name: str, user: str, prune_admin: int = 1):
    members_field, _ = _members_field_info()
    if not members_field:
        frappe.throw("Could not locate members child table on User Group")

    ug = frappe.get_doc("User Group", group_name)
    ug.reload()

    rows = getattr(ug, members_field, []) or []
    keep = [r for r in rows if getattr(r, "user", "") != "Administrator"] if prune_admin else rows

    if not any(getattr(r, "user", None) == user for r in keep):
        setattr(ug, members_field, keep)
        ug.append(members_field, {"user": user})
    else:
        setattr(ug, members_field, keep)

    ug.save(ignore_permissions=True)
    return {"status": "ok", "group": group_name, "members": [r.user for r in getattr(ug, members_field, [])]}


@frappe.whitelist()
def add_member_direct_and_prune(group_name: str, user: str, prune_admin: int = 1):
    members_field, _ = _members_field_info()
    if not members_field:
        members_field = "user_group_members"  # last-resort fallback

    if not frappe.db.exists("User Group", group_name):
        _ensure_group(group_name)

    exists = frappe.db.exists("User Group Member", {
        "parent": group_name,
        "parenttype": "User Group",
        "parentfield": members_field,
        "user": user,
    })
    if not exists:
        frappe.get_doc({
            "doctype": "User Group Member",
            "parent": group_name,
            "parenttype": "User Group",
            "parentfield": members_field,
            "user": user,
        }).insert(ignore_permissions=True)

    if prune_admin:
        frappe.db.delete("User Group Member", {
            "parent": group_name,
            "parenttype": "User Group",
            "parentfield": members_field,
            "user": "Administrator",
        })
    frappe.db.commit()

    rows = frappe.get_all(
        "User Group Member",
        filters={"parent": group_name, "parenttype": "User Group", "parentfield": members_field},
        pluck="user",
    )
    return {"status": "ok", "group": group_name, "members": rows}


@frappe.whitelist()
def backfill_user_group_memberships():
    """Re-apply sync for all users once (runs inline, no queue)."""
    users = frappe.get_all("User", pluck="name")
    count = 0
    for name in users:
        doc = frappe.get_doc("User", name)
        _sync_user_groups_from_doc(doc)
        count += 1
    return {"status": "ok", "processed": count}
