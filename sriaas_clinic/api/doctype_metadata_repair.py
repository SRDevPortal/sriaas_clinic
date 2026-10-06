from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import frappe


CHILD_TABLE_FIELDTYPES = {"Table", "Table MultiSelect"}
LAYOUT_FIELDTYPES = {
    "Section Break",
    "Column Break",
    "Tab Break",
    "HTML",
    "Button",
    "Fold",
    "Heading",
    "Image",
    "Table Break",
}


def repair_missing_standard_docfields(commit: bool = False) -> dict[str, Any]:
    """
    Restore standard DocField rows that exist in installed app JSON but are missing
    from this site's tabDocField metadata.

    This repairs metadata corruption like ToDo.reference_name disappearing while
    tabToDo.reference_name still exists.
    """
    restored = []
    skipped = []
    affected_doctypes = set()

    for source in _iter_source_docfields():
        if frappe.db.exists("DocField", {"parent": source["doctype"], "fieldname": source["fieldname"]}):
            continue

        if not _should_restore(source):
            skipped.append(_summary(source, reason="not_high_confidence"))
            continue

        _shift_docfield_idx(source["doctype"], source["idx"])
        docfield = frappe.get_doc(_docfield_payload(source))
        docfield.insert(ignore_permissions=True)

        restored.append(_summary(source, docfield_name=docfield.name))
        affected_doctypes.add(source["doctype"])
        frappe.clear_cache(doctype=source["doctype"])

    for doctype in sorted(affected_doctypes):
        frappe.db.updatedb(doctype)
        frappe.clear_cache(doctype=doctype)

    if commit:
        frappe.db.commit()

    return {
        "restored_count": len(restored),
        "skipped_count": len(skipped),
        "restored": restored,
        "skipped_sample": skipped[:50],
    }


def _iter_source_docfields() -> list[dict[str, Any]]:
    bench = Path(frappe.utils.get_bench_path())
    apps_file = bench / "sites" / "apps.txt"
    app_names = [line.strip() for line in apps_file.read_text().splitlines() if line.strip()]
    out = []

    for app in app_names:
        app_path = bench / "apps" / app
        if not app_path.exists():
            continue

        for json_path in app_path.rglob("*.json"):
            try:
                data = json.loads(json_path.read_text())
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            if data.get("doctype") != "DocType" or not data.get("name"):
                continue

            doctype = data["name"]
            if not frappe.db.exists("DocType", doctype):
                continue

            for idx, field in enumerate(data.get("fields") or [], start=1):
                if not isinstance(field, dict) or not field.get("fieldname"):
                    continue
                out.append(
                    {
                        "app": app,
                        "doctype": doctype,
                        "idx": idx,
                        "json_path": str(json_path.relative_to(bench)),
                        "field": field,
                        "fieldname": field.get("fieldname"),
                        "fieldtype": field.get("fieldtype"),
                    }
                )

    return out


def _should_restore(source: dict[str, Any]) -> bool:
    fieldtype = source["fieldtype"]
    if fieldtype in LAYOUT_FIELDTYPES or fieldtype in CHILD_TABLE_FIELDTYPES:
        return True

    has_table = frappe.db.table_exists(source["doctype"])
    column_exists = bool(has_table and frappe.db.has_column(source["doctype"], source["fieldname"]))

    # Highest-confidence corruption pattern: DB column exists but DocField row vanished.
    if column_exists:
        return True

    # Dynamic Links are often operational reference fields; if missing, values may
    # be dropped before schema sync can create the column.
    if fieldtype == "Dynamic Link":
        return True

    return False


def _docfield_payload(source: dict[str, Any]) -> dict[str, Any]:
    field = dict(source["field"])
    allowed = frappe.get_meta("DocField").get_valid_columns()
    payload = {key: value for key, value in field.items() if key in allowed}
    payload.update(
        {
            "doctype": "DocField",
            "parent": source["doctype"],
            "parenttype": "DocType",
            "parentfield": "fields",
            "idx": source["idx"],
        }
    )
    return payload


def _shift_docfield_idx(doctype: str, idx: int) -> None:
    frappe.db.sql(
        """
        UPDATE `tabDocField`
        SET idx = idx + 1
        WHERE parent = %s
          AND parenttype = 'DocType'
          AND parentfield = 'fields'
          AND idx >= %s
        """,
        (doctype, idx),
    )


def _summary(source: dict[str, Any], reason: str | None = None, docfield_name: str | None = None):
    row = {
        "app": source["app"],
        "doctype": source["doctype"],
        "fieldname": source["fieldname"],
        "fieldtype": source["fieldtype"],
        "idx": source["idx"],
        "json_path": source["json_path"],
    }
    if reason:
        row["reason"] = reason
    if docfield_name:
        row["docfield_name"] = docfield_name
    return row
