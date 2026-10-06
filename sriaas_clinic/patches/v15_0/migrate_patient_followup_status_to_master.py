from __future__ import annotations

import frappe

from sriaas_clinic.setup.masters import (
    ensure_followup_status_doctype,
    ensure_legacy_followup_statuses,
    seed_followup_statuses,
)
from sriaas_clinic.setup.utils import ensure_module_def


OBSOLETE_OPTIONS_PROPERTY_SETTER = "Patient-sr_followup_status-options"


def execute() -> None:
    """Prepare legacy Patient values before converting the field to a Link."""
    if not frappe.db.exists("DocType", "Patient"):
        return

    ensure_module_def()
    ensure_followup_status_doctype()
    seed_followup_statuses()
    inserted = ensure_legacy_followup_statuses()

    _remove_obsolete_options_property_setter()
    _assert_all_patient_statuses_resolve()

    frappe.clear_cache(doctype="Patient")
    frappe.clear_cache(doctype="SR Followup Status")
    frappe.logger("sriaas_clinic").info(
        "Patient Follow-up Status master migration completed; legacy statuses inserted: %s",
        inserted,
    )


def _remove_obsolete_options_property_setter() -> None:
    if not frappe.db.exists("Property Setter", OBSOLETE_OPTIONS_PROPERTY_SETTER):
        return

    frappe.delete_doc(
        "Property Setter",
        OBSOLETE_OPTIONS_PROPERTY_SETTER,
        force=True,
        ignore_permissions=True,
        delete_permanently=True,
    )


def _assert_all_patient_statuses_resolve() -> None:
    status_names = frappe.get_all(
        "Patient",
        filters={"sr_followup_status": ["is", "set"]},
        pluck="sr_followup_status",
        distinct=True,
        limit_page_length=0,
    )
    missing = [
        status_name
        for status_name in status_names
        if not frappe.db.exists("SR Followup Status", status_name)
    ]
    if missing:
        frappe.throw(
            "Patient Follow-up Status values are missing from the master: "
            + ", ".join(sorted(missing))
        )
