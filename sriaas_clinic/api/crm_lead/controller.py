# sriaas_clinic/api/crm_lead/controller.py
# Public APIs (normalize / assign / clear) for CRM Lead

import frappe
from sriaas_clinic.api.crm_lead.config import REF_DOCTYPE, get_config, get_locked_fields
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
    if doc.doctype != get_config().ref_doctype:
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
    pipeline_doctype = get_config().pipeline_doctype
    if not pipeline_doctype:
        return False

    perms = get_user_permissions(user) or {}
    raw = perms.get(pipeline_doctype) or []

    allowed = set()
    for v in raw:
        if isinstance(v, str):
            allowed.add(v)
        elif isinstance(v, dict):
            allowed.add(v.get("doc") or v.get("value") or v.get("name"))

    allowed.discard(None)
    allowed.discard("")
    return pipeline in allowed


@frappe.whitelist()
def get_crm_lead_role_context():
    from sriaas_clinic.api.assign_guard import _is_team_leader
    from sriaas_clinic.api.crm_lead.access import (
        _is_assistant_team_lead,
        _is_effective_team_leader,
        _is_main_team_lead,
        _reports_to_team_leader,
        get_managed_team_users,
    )
    from sriaas_role_permissions.api.roles import has_agent_role, has_team_leader_role, is_privileged

    user = frappe.session.user
    config = get_config()
    locked = get_locked_fields()
    reports_to = _reports_to_team_leader(user)
    can_manage = _is_team_leader(user)

    return {
        "user": user,
        "ref_doctype": config.ref_doctype,
        "pipeline_doctype": config.pipeline_doctype,
        "pipeline_fieldname": config.pipeline_fieldname,
        "owner_fieldname": config.owner_fieldname,
        "team_leader_fieldname": config.team_leader_fieldname,
        "team_leader_label": config.team_leader_label,
        "agent_label": config.agent_label,
        "privileged_label": config.privileged_label,
        "lock_after_insert_fields": sorted(locked["lock_after_insert"]),
        "agent_always_lock_fields": sorted(locked["agent_always_lock"]),
        "is_privileged": is_privileged(user, REF_DOCTYPE),
        "has_team_leader_role": has_team_leader_role(user, REF_DOCTYPE),
        "has_agent_role": has_agent_role(user, REF_DOCTYPE),
        "reports_to_team_leader": reports_to,
        "is_main_team_lead": _is_main_team_lead(user),
        "is_assistant_team_lead": _is_assistant_team_lead(user),
        "is_effective_team_leader": _is_effective_team_leader(user),
        "managed_team_users": get_managed_team_users(user),
        "can_manage_assignment": can_manage,
    }


def _ensure_assignment_target_allowed(new_owner: str) -> None:
    from sriaas_clinic.api.crm_lead.access import _is_privileged, get_managed_team_users

    if _is_privileged(frappe.session.user):
        return

    managed_users = set(get_managed_team_users(frappe.session.user))
    if new_owner not in managed_users:
        frappe.throw(
            frappe._("{0} can assign only to active members of their managed team.").format(
                get_config().team_leader_label
            ),
            title="Assignment Not Allowed",
            exc=frappe.PermissionError,
        )


def _ensure_can_manage_lead(doc) -> None:
    from sriaas_clinic.api.crm_lead.access import _is_privileged, crm_lead_has_permission

    if _is_privileged(frappe.session.user):
        return

    if not crm_lead_has_permission(doc, frappe.session.user):
        frappe.throw(
            frappe._("You can manage only leads visible to your managed team."),
            title="Lead Not Allowed",
            exc=frappe.PermissionError,
        )


# ---------------------------------------------------------------------------
# ASSIGN CRM LEAD OWNER (Team Leader only)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def assign_crm_lead_owner(leads, new_owner):
    from crm_lead_assignment.api.manual import assign_crm_leads

    return assign_crm_leads(leads, new_owner)

    from sriaas_clinic.api.assign_guard import _is_team_leader

    if not _is_team_leader(frappe.session.user):
        frappe.throw(
            f"Only configured {get_config().team_leader_label} users can assign {get_config().ref_doctype} records.",
            frappe.PermissionError
        )

    if isinstance(leads, str):
        leads = frappe.parse_json(leads)

    if not frappe.db.exists("User", {"name": new_owner, "enabled": 1}):
        frappe.throw("Invalid or disabled user selected")

    _ensure_assignment_target_allowed(new_owner)

    for lead in leads:
        config = get_config()
        doc = frappe.get_doc(config.ref_doctype, lead)
        _ensure_can_manage_lead(doc)

        # 🔒 HARD BLOCK: pipeline permission enforcement
        pipeline = doc.get(config.pipeline_fieldname)
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
                    "{2} <b>{1}</b> is not allowed for this pipeline."
                ).format(pipeline, new_owner, config.agent_label),
                title="Assignment Not Allowed"
            )

        # Skip if already owner
        if doc.get(config.owner_fieldname) == new_owner:
            continue

        # Set owner
        doc.set(config.owner_fieldname, new_owner)
        doc.save(ignore_permissions=True)

        # Close existing assignments
        frappe.db.sql("""
            UPDATE `tabToDo`
            SET status='Closed'
            WHERE reference_type=%s
              AND reference_name=%s
              AND status='Open'
        """, (config.ref_doctype, lead))

        # Assign to new owner
        from frappe.desk.form.assign_to import add
        add({
            "assign_to": [new_owner],
            "doctype": config.ref_doctype,
            "name": lead,
            "notify": 1
        })
        _repair_assignment_reference(lead, new_owner)

        # Audit trail
        doc.add_comment(
            "Info",
            f"Lead assigned to {new_owner} by {frappe.session.user}"
        )

    return {"status": "ok"}


def _repair_assignment_reference(lead, owner):
    config = get_config()
    frappe.db.sql(
        """
        UPDATE `tabToDo`
        SET reference_name = %s
        WHERE reference_type = %s
          AND allocated_to = %s
          AND status = 'Open'
          AND (reference_name IS NULL OR reference_name = '')
          AND description LIKE %s
        """,
        (lead, config.ref_doctype, owner, f"%{lead}%"),
    )


# ---------------------------------------------------------------------------
# CLEAR CRM LEAD ASSIGNMENT (ToDo + owner cleared intentionally)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def clear_crm_lead_owner(leads):
    from crm_lead_assignment.api.manual import clear_crm_leads

    return clear_crm_leads(leads)

    from sriaas_clinic.api.assign_guard import clear, _is_team_leader

    if not _is_team_leader(frappe.session.user):
        frappe.throw(
            f"Only configured {get_config().team_leader_label} users can clear {get_config().ref_doctype} assignments.",
            frappe.PermissionError
        )

    if isinstance(leads, str):
        leads = frappe.parse_json(leads)

    for lead in leads:
        config = get_config()
        doc = frappe.get_doc(config.ref_doctype, lead)
        _ensure_can_manage_lead(doc)

        # 🚫 Explicit signal: this is an intentional clear
        frappe.flags._sr_skip_owner_restore = True

        # 1️⃣ Clear assignment (ToDo)
        clear(config.ref_doctype, lead)

        # 2️⃣ Explicitly clear lead_owner
        frappe.db.set_value(
            config.ref_doctype,
            lead,
            config.owner_fieldname,
            None,
            update_modified=False
        )

    return {"status": "ok"}
