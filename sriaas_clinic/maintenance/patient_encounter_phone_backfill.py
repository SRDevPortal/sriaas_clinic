from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import cint

from sriaas_clinic.phone_utils import normalize_phone_last10


DOCTYPE = "Patient Encounter"
SOURCE_FIELD = "sr_pe_mobile"
TARGET_FIELD = "sr_pe_mobile_norm"
PROGRESS_KEY = "sriaas_clinic_patient_encounter_phone_backfill_last_name"
DEFAULT_BATCH_SIZE = 2000
MAX_BATCH_SIZE = 5000
INDEX_NAME = "idx_pe_mobile_norm_modified"


def normalized_update(row: Any) -> dict[str, str]:
    normalized = normalize_phone_last10(row.get(SOURCE_FIELD))
    if str(row.get(TARGET_FIELD) or "") == normalized:
        return {}
    return {TARGET_FIELD: normalized}


def _fields_ready() -> bool:
    return frappe.db.has_column(DOCTYPE, SOURCE_FIELD) and frappe.db.has_column(
        DOCTYPE, TARGET_FIELD
    )


@frappe.whitelist()
def backfill_phone_keys(
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_batches: int = 10,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Backfill the exact Patient Encounter phone key in bounded resumable batches."""
    frappe.only_for("System Manager")
    if not _fields_ready():
        return {
            "doctype": DOCTYPE,
            "done": True,
            "reason": "source_or_target_field_missing",
        }

    batch_size = max(100, min(cint(batch_size) or DEFAULT_BATCH_SIZE, MAX_BATCH_SIZE))
    max_batches = max(1, min(cint(max_batches) or 10, 100))
    dry_run = bool(cint(dry_run))
    last_name = str(frappe.db.get_global(PROGRESS_KEY) or "")
    processed = updated = invalid = 0
    done = False

    for _batch in range(max_batches):
        filters = {"name": [">", last_name]} if last_name else None
        rows = frappe.get_all(
            DOCTYPE,
            filters=filters,
            fields=["name", SOURCE_FIELD, TARGET_FIELD],
            order_by="name asc",
            limit_page_length=batch_size,
        )
        if not rows:
            done = True
            break

        updates: dict[str, dict[str, str]] = {}
        for row in rows:
            processed += 1
            if str(row.get(SOURCE_FIELD) or "").strip() and not normalize_phone_last10(
                row.get(SOURCE_FIELD)
            ):
                invalid += 1
            changed = normalized_update(row)
            if changed:
                updates[row.name] = changed

        updated += len(updates)
        last_name = rows[-1].name
        if not dry_run:
            if updates:
                frappe.db.bulk_update(
                    DOCTYPE,
                    updates,
                    chunk_size=min(200, batch_size),
                    update_modified=False,
                )
            frappe.db.set_global(PROGRESS_KEY, last_name)
            frappe.db.commit()

        if len(rows) < batch_size:
            done = True
            break

    return {
        "doctype": DOCTYPE,
        "dry_run": dry_run,
        "processed": processed,
        "updated": updated,
        "invalid": invalid,
        "last_name": last_name,
        "done": done,
        "source_field": SOURCE_FIELD,
        "target_field": TARGET_FIELD,
    }


@frappe.whitelist()
def reset_phone_backfill() -> dict[str, Any]:
    frappe.only_for("System Manager")
    frappe.db.set_global(PROGRESS_KEY, "")
    frappe.db.commit()
    return {"doctype": DOCTYPE, "reset": True}


@frappe.whitelist()
def phone_key_coverage() -> dict[str, Any]:
    """Return valid, invalid, missing, and mismatched key counts in one table scan."""
    frappe.only_for("System Manager")
    return _phone_key_coverage()


def _phone_key_coverage() -> dict[str, Any]:
    if not _fields_ready():
        return {
            "doctype": DOCTYPE,
            "total": frappe.db.count(DOCTYPE),
            "ready": False,
            "reason": "source_or_target_field_missing",
        }

    row = frappe.db.sql(
        f"""
        SELECT
            COUNT(*) AS total,
            SUM(source_value = '') AS empty_source,
            SUM(source_value != '' AND CHAR_LENGTH(source_digits) < 10) AS invalid_source,
            SUM(CHAR_LENGTH(source_digits) >= 10) AS valid_source,
            SUM(
                CHAR_LENGTH(source_digits) >= 10
                AND target_value = ''
            ) AS missing,
            SUM(
                CHAR_LENGTH(source_digits) >= 10
                AND target_value != ''
                AND target_value != RIGHT(source_digits, 10)
            ) AS mismatch
        FROM (
            SELECT
                COALESCE(`{SOURCE_FIELD}`, '') AS source_value,
                REGEXP_REPLACE(COALESCE(`{SOURCE_FIELD}`, ''), '[^0-9]', '') AS source_digits,
                COALESCE(`{TARGET_FIELD}`, '') AS target_value
            FROM `tab{DOCTYPE}`
        ) phone_keys
        """,
        as_dict=True,
    )[0]
    result = {key: cint(value) for key, value in row.items()}
    result.update(
        {
            "doctype": DOCTYPE,
            "ready": result["missing"] == 0 and result["mismatch"] == 0,
            "source_field": SOURCE_FIELD,
            "target_field": TARGET_FIELD,
        }
    )
    return result


@frappe.whitelist()
def ensure_phone_index() -> dict[str, Any]:
    """Create the lookup index only after all valid phone keys are ready."""
    frappe.only_for("System Manager")
    return _ensure_phone_index()


def _ensure_phone_index() -> dict[str, Any]:
    if not _fields_ready():
        frappe.throw("Patient Encounter normalized-phone fields are missing.")
    if _index_exists(INDEX_NAME):
        return {"doctype": DOCTYPE, "index": INDEX_NAME, "created": False, "exists": True}

    coverage = _phone_key_coverage()
    if not coverage["ready"]:
        frappe.throw(
            "Patient Encounter phone coverage is incomplete: "
            f"missing={coverage['missing']}, mismatch={coverage['mismatch']}."
        )

    _add_phone_index()
    return {"doctype": DOCTYPE, "index": INDEX_NAME, "created": True, "exists": True}


def _add_phone_index() -> None:
    frappe.db.add_index(DOCTYPE, [TARGET_FIELD, "modified"], index_name=INDEX_NAME)


def _index_exists(index_name: str) -> bool:
    return bool(
        frappe.db.sql(
            """
            SELECT 1
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND INDEX_NAME = %s
            LIMIT 1
            """,
            (f"tab{DOCTYPE}", index_name),
        )
    )
