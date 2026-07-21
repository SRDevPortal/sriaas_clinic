from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from sriaas_clinic.phone_utils import normalize_phone_last10


DEFAULT_PAGE_LENGTH = 20
MAX_PAGE_LENGTH = 100
PARENT_FIELDS = (
    "name",
    "patient",
    "patient_name",
    "sr_pe_id",
    "sr_pe_mobile",
    "sr_pe_deptt",
    "sr_encounter_status",
    "sr_encounter_type",
    "sr_encounter_place",
    "owner",
    "creation",
    "modified",
)
EXACT_FILTER_FIELDS = {
    "sr_pe_id",
    "sr_pe_deptt",
    "sr_encounter_status",
    "sr_encounter_type",
    "sr_encounter_place",
    "owner",
}
ALLOWED_FILTER_KEYS = EXACT_FILTER_FIELDS | {
    "mobile",
    "creation_from",
    "creation_to",
}
INDEXED_PHONE_LOOKUP_CONFIG = "enable_indexed_patient_encounter_phone_lookup"


@frappe.whitelist()
def get_optimized_encounters(filters=None, start=0, page_length=DEFAULT_PAGE_LENGTH):
    """Return a permission-aware Encounter page without joining child tables."""
    frappe.has_permission("Patient Encounter", "read", throw=True)
    meta = frappe.get_meta("Patient Encounter")
    parsed_filters = _parse_filters(filters)
    query_filters = _build_parent_filters(parsed_filters, meta)
    start = max(cint(start), 0)
    page_length = min(max(cint(page_length) or DEFAULT_PAGE_LENGTH, 1), MAX_PAGE_LENGTH)
    fields = [fieldname for fieldname in PARENT_FIELDS if fieldname == "name" or meta.has_field(fieldname)]

    rows = frappe.get_list(
        "Patient Encounter",
        filters=query_filters,
        fields=fields,
        order_by="modified desc, name desc",
        start=start,
        page_length=page_length + 1,
    )
    has_more = len(rows) > page_length
    rows = rows[:page_length]
    names = [row.name for row in rows]

    order_totals = _child_totals("SR Order Item", "sr_item_amount", names)
    payment_totals = _child_totals("SR Multi Mode Payment", "mmp_paid_amount", names)
    for row in rows:
        row["order_total"] = order_totals.get(row.name, 0)
        row["paid_total"] = payment_totals.get(row.name, 0)

    return {
        "rows": rows,
        "has_more": has_more,
        "next_start": start + len(rows) if has_more else None,
    }


def _parse_filters(filters) -> dict[str, Any]:
    if not filters:
        return {}
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    if not isinstance(filters, dict):
        frappe.throw(_("filters must be an object"))

    unknown = sorted(set(filters) - ALLOWED_FILTER_KEYS)
    if unknown:
        frappe.throw(_("Unsupported Patient Encounter filters: {0}").format(", ".join(unknown)))
    return filters


def _build_parent_filters(filters: dict[str, Any], meta) -> list[list[Any]]:
    query_filters: list[list[Any]] = []
    for fieldname in EXACT_FILTER_FIELDS:
        value = filters.get(fieldname)
        if value not in (None, "") and meta.has_field(fieldname):
            query_filters.append([fieldname, "=", value])

    mobile = str(filters.get("mobile") or "").strip()
    if mobile:
        normalized = _normalize_phone_lookup(mobile)
        if not normalized:
            frappe.throw(_("Enter a phone number containing at least 10 digits."))
        if meta.has_field("sr_pe_mobile_norm") and _indexed_phone_lookup_enabled():
            query_filters.append(["sr_pe_mobile_norm", "=", normalized])
        elif meta.has_field("sr_pe_mobile"):
            # This exact compatibility path intentionally avoids a leading
            # wildcard. The normalized field is preferred after DB rollout.
            query_filters.append(["sr_pe_mobile", "=", mobile])

    creation_from = filters.get("creation_from")
    creation_to = filters.get("creation_to")
    if creation_from:
        query_filters.append(["creation", ">=", creation_from])
    if creation_to:
        query_filters.append(["creation", "<=", creation_to])
    return query_filters


def _normalize_phone_lookup(value: str) -> str:
    return normalize_phone_last10(value)


def _indexed_phone_lookup_enabled() -> bool:
    return bool(cint(frappe.conf.get(INDEXED_PHONE_LOOKUP_CONFIG)))


def _child_totals(doctype: str, amount_field: str, parents: list[str]) -> dict[str, Any]:
    if not parents or not frappe.db.exists("DocType", doctype):
        return {}
    if not frappe.db.has_column(doctype, amount_field):
        return {}

    rows = frappe.get_all(
        doctype,
        filters={"parenttype": "Patient Encounter", "parent": ["in", parents]},
        fields=["parent", f"sum(`{amount_field}`) as total"],
        group_by="parent",
        limit_page_length=0,
    )
    return {row.parent: row.total or 0 for row in rows}
