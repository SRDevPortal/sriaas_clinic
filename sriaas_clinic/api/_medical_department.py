# apps/sriaas_clinic/sriaas_clinic/api/medical_department.py

from __future__ import annotations
import frappe
from typing import List, Optional

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

# Change this if your DocType is named differently
DEPARTMENT_DOTYPE = "Medical Department"

# Default segments for each department (become "<Dept> <Segment>" groups)
DEFAULT_SEGMENTS: List[str] = ["Reception", "Fresh", "Repeat"]

# Optionally attach roles to every created User Group (leave empty to skip)
DEFAULT_GROUP_ROLES: List[str] = [
    # "Sales User",
    # "CRM User",
]

# -------------------------------------------------------------------
# INTERNAL HELPERS
# -------------------------------------------------------------------

def _log(msg: str):
    frappe.logger("sriaas_clinic.med_dept").info(msg)


# --- put this near the top with your other helpers -----------------
def _members_field_info():
    """Return (fieldname, field_meta) for the members child table on User Group."""
    meta = frappe.get_meta("User Group")
    # Preferred pointer to 'User Group Member'
    for f in meta.fields:
        if f.fieldtype in ("Table", "Table MultiSelect") and f.options == "User Group Member":
            return f.fieldname, f
    # Fallback guesses seen on customized sites
    for guess in ("user_group_members", "users", "members"):
        if meta.has_field(guess):
            return guess, meta.get_field(guess)
    return None, None


def ensure_user_group(group_name: str) -> str:
    """
    Idempotently create a User Group named exactly `group_name`.
    Seeds an 'Administrator' row in the members table on insert,
    so mandatory child table validation never fails and the group
    isn't empty by default.
    """
    if not group_name:
        return ""

    # Already there?
    if frappe.db.exists("User Group", group_name):
        return group_name

    meta = frappe.get_meta("User Group")
    fields = {f.fieldname for f in meta.fields}

    payload = {"doctype": "User Group"}

    # Fill a human title field if present
    if "user_group_name" in fields:
        payload["user_group_name"] = group_name
    elif "title" in fields:
        payload["title"] = group_name

    # Hard-set the name so autoname never complains
    doc = frappe.get_doc(payload)
    doc.name = group_name

    # Seed Administrator in members child table (if present)
    members_field, _ = _members_field_info()
    if members_field:
        # ensure we start with at least one row
        doc.set(members_field, [{"user": "Administrator"}])

    # Insert (no ignore_mandatory needed now that we seeded members)
    doc.insert(ignore_permissions=True)
    return group_name


def ensure_groups_for_department(dept: str) -> List[str]:
    """
    Create '<Dept> Reception/Fresh/Repeat' groups safely.
    Return the list of group names that now exist (idempotent).
    """
    if not dept:
        return []
    created: List[str] = []
    for seg in DEFAULT_SEGMENTS:
        group = f"{dept} {seg}"
        ensure_user_group(group)
        created.append(group)
    return created


# -------------------------------------------------------------------
# DOC EVENTS
# -------------------------------------------------------------------

def after_insert(doc, method: Optional[str] = None):
    """
    Hook: Medical Department → After Insert
    Creates 3 user groups for the newly created department:
      <Dept> Reception, <Dept> Fresh, <Dept> Repeat
    """
    try:
        if doc.doctype != DEPARTMENT_DOTYPE:
            return
        ensure_groups_for_department(doc.name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Medical Department after_insert failed")


def on_rename(doc, method: Optional[str] = None, old: Optional[str] = None, new: Optional[str] = None):
    """
    Optional: if you rename a department, also rename its user groups.
    Add to hooks if you want this behavior.
    """
    try:
        if doc.doctype != DEPARTMENT_DOTYPE:
            return

        old_name = old or getattr(doc, "old_name", None)
        new_name = new or doc.name
        if not old_name or not new_name or old_name == new_name:
            return

        for seg in DEFAULT_SEGMENTS:
            old_group = f"{old_name} {seg}"
            new_group = f"{new_name} {seg}"
            if frappe.db.exists("User Group", old_group) and not frappe.db.exists("User Group", new_group):
                frappe.rename_doc("User Group", old_group, new_group, ignore_permissions=True, force=True)
                _log(f"Renamed User Group: {old_group} → {new_group}")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Medical Department on_rename failed")


# -------------------------------------------------------------------
# UTILITIES (optional but handy)
# -------------------------------------------------------------------

@frappe.whitelist()
def backfill_user_groups_for_all_departments():
    """
    Create missing <Dept> <Segment> groups for all departments.
    Safe to run multiple times (idempotent).
    """
    depts = frappe.get_all(DEPARTMENT_DOTYPE, pluck="name")
    total_groups_checked = 0
    for d in depts:
        total_groups_checked += len(ensure_groups_for_department(d))
    return {"status": "ok", "total_groups_checked": total_groups_checked, "departments": len(depts)}


@frappe.whitelist()
def seed_admin_on_existing_department_groups():
    """
    For all '<Dept> <Segment>' groups, if the members table is empty,
    add an 'Administrator' seed row.
    """
    members_field, _ = _members_field_info()
    if not members_field:
        return {"status": "skipped", "reason": "No members child table found on User Group"}

    # Find all groups that look like '<Dept> <Segment>'
    seg_suffixes = tuple(f" {s}" for s in DEFAULT_SEGMENTS)
    groups = [
        g["name"]
        for g in frappe.get_all("User Group", fields=["name"])
        if g["name"].endswith(seg_suffixes)
    ]

    updated = 0
    for name in groups:
        ug = frappe.get_doc("User Group", name)
        rows = getattr(ug, members_field, []) or []
        if not rows:
            ug.append(members_field, {"user": "Administrator"})
            ug.save(ignore_permissions=True)
            updated += 1

    return {"status": "ok", "checked": len(groups), "updated": updated}


@frappe.whitelist()
def apply_roles_to_all_department_groups():
    """
    Ensures DEFAULT_GROUP_ROLES exist on all '<Dept> <Segment>' groups.
    """
    if not DEFAULT_GROUP_ROLES:
        return {"status": "skipped", "reason": "DEFAULT_GROUP_ROLES empty"}

    groups = frappe.get_all("User Group", fields=["name"])
    count = 0
    for g in groups:
        name = g["name"]
        # only touch groups that follow our "<Dept> <Segment>" pattern
        if not any(name.endswith(f" {seg}") for seg in DEFAULT_SEGMENTS):
            continue
        ug = frappe.get_doc("User Group", name)
        current = {row.role for row in (ug.roles or [])}
        changed = False
        for role in DEFAULT_GROUP_ROLES:
            if role not in current:
                ug.append("roles", {"role": role})
                changed = True
        if changed:
            ug.save(ignore_permissions=True)
            count += 1
    return {"status": "ok", "updated_groups": count}
