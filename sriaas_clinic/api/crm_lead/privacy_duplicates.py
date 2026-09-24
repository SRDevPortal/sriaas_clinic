"""Duplicate-popup response adapter; matching and authorization remain upstream."""
import frappe


@frappe.whitelist()
def get_duplicates_for_crm_lead(lead_name: str, columns=None):
    from crm_lead_dedupe.api.crm_lead_duplicates import get_duplicates_for_crm_lead as original
    from privacy_shield.desk import enabled
    from privacy_shield.policy import current_capabilities
    from privacy_shield.duplicate_views import project_duplicate_rows

    # Delegate directly, not through the RPC dispatcher (which would recurse).
    # Source/candidate permissions, feature flags, matching and ordering run first.
    rows = original(lead_name, columns)
    if not enabled("CRM Lead") or current_capabilities().view_full:
        return rows
    return project_duplicate_rows(rows)
