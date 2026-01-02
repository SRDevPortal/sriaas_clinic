# sriaas_clinic/api/crm_lead/controller.py
# Public APIs (normalize / assign / clear) for CRM Lead

import frappe
from sriaas_clinic.api.crm_lead.utils import clean_spaces
from frappe.core.doctype.user_permission.user_permission import get_user_permissions


# ---------------------------------------------------------------------------
# NORMALIZE PHONE-LIKE FIELDS
# ---------------------------------------------------------------------------

def normalize_phoneish_fields(doc, method=None):
    """
    Strip whitespace from phone-like fields on CRM Lead.
    Runs on CRM Lead.before_save. Idempotent.

    Uses a bypass flag so the field-guard doesn't treat these
    programmatic updates as user edits.
    """
    if doc.doctype != "CRM Lead":
        return

    CANDIDATE_FIELDS = (
        "mobile", "mobile_no",
        "phone", "phone_no",
        "whatsapp_no",
        "alternate_phone",
        "sr_mobile_no", "sr_whatsapp_no",
    )

    prev_flag = getattr(frappe.flags, "sr_bypass_field_guard", False)
    frappe.flags.sr_bypass_field_guard = True
    try:
        for field in CANDIDATE_FIELDS:
            val = doc.get(field)
            cleaned = clean_spaces(val)
            if cleaned != val:
                doc.set(field, cleaned)
    finally:
        frappe.flags.sr_bypass_field_guard = prev_flag


# ---------------------------------------------------------------------------
# PIPELINE PERMISSION HELPER (NEW)
# ---------------------------------------------------------------------------

def _agent_allowed_for_pipeline(user: str, pipeline: str) -> bool:
    """
    Check whether agent has User Permission for given SR Lead Pipeline
    """
    perms = get_user_permissions(user) or {}
    raw = perms.get("SR Lead Pipeline") or []

    allowed = set()
    for v in raw:
        if isinstance(v, str):
            allowed.add(v)
        elif isinstance(v, dict):
            allowed.add(v.get("doc") or v.get("value") or v.get("name"))

    allowed.discard(None)
    allowed.discard("")
    return pipeline in allowed


# ---------------------------------------------------------------------------
# ASSIGN CRM LEAD OWNER (Team Leader only)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def assign_crm_lead_owner(leads, new_owner):
    from sriaas_clinic.api.assign_guard import _is_team_leader

    if not _is_team_leader(frappe.session.user):
        frappe.throw(
            "Only Team Leaders can assign CRM Leads.",
            frappe.PermissionError
        )

    if isinstance(leads, str):
        leads = frappe.parse_json(leads)

    if not frappe.db.exists("User", {"name": new_owner, "enabled": 1}):
        frappe.throw("Invalid or disabled user selected")

    for lead in leads:
        doc = frappe.get_doc("CRM Lead", lead)

        # 🔒 HARD BLOCK: pipeline permission enforcement
        pipeline = doc.sr_lead_pipeline
        if pipeline and not _agent_allowed_for_pipeline(new_owner, pipeline):
            # frappe.throw(
            #     f"❌ Assignment blocked.<br>"
            #     f"Agent <b>{new_owner}</b> is not allowed for pipeline "
            #     f"<b>{pipeline}</b>."
            # )

            # frappe.throw(
            #     title="Assignment Not Allowed",
            #     msg=(
            #         f"This lead belongs to <b>{pipeline}</b> pipeline.<br>"
            #         f"Agent <b>{new_owner}</b> is not allowed for this pipeline."
            #     ),
            #     exc=frappe.PermissionError,
            # )

            frappe.throw(
                frappe._(
                    "This lead belongs to <b>{0}</b> pipeline.<br>"
                    "Agent <b>{1}</b> is not allowed for this pipeline."
                ).format(pipeline, new_owner),
                title="Assignment Not Allowed"
            )

        # Skip if already owner
        if doc.lead_owner == new_owner:
            continue

        # Set owner
        doc.lead_owner = new_owner
        doc.save(ignore_permissions=True)

        # Close existing assignments
        frappe.db.sql("""
            UPDATE `tabToDo`
            SET status='Closed'
            WHERE reference_type='CRM Lead'
              AND reference_name=%s
              AND status='Open'
        """, lead)

        # Assign to new owner
        from frappe.desk.form.assign_to import add
        add({
            "assign_to": [new_owner],
            "doctype": "CRM Lead",
            "name": lead,
            "notify": 1
        })

        # Audit trail
        doc.add_comment(
            "Info",
            f"Lead assigned to {new_owner} by {frappe.session.user}"
        )

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# CLEAR CRM LEAD ASSIGNMENT (ToDo + owner cleared intentionally)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def clear_crm_lead_owner(leads):
    from sriaas_clinic.api.assign_guard import clear, _is_team_leader

    if not _is_team_leader(frappe.session.user):
        frappe.throw(
            "Only Team Leaders can clear CRM Lead assignments.",
            frappe.PermissionError
        )

    if isinstance(leads, str):
        leads = frappe.parse_json(leads)

    for lead in leads:
        # 🚫 Explicit signal: this is an intentional clear
        frappe.flags._sr_skip_owner_restore = True

        # 1️⃣ Clear assignment (ToDo)
        clear("CRM Lead", lead)

        # 2️⃣ Explicitly clear lead_owner
        frappe.db.set_value(
            "CRM Lead",
            lead,
            "lead_owner",
            None,
            update_modified=False
        )

    return {"status": "ok"}
