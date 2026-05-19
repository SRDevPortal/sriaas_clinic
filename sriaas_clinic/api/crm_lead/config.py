from __future__ import annotations

import frappe


REF_DOCTYPE = "CRM Lead"


def get_config():
    from sriaas_role_permissions.api.config import get_doctype_config

    return get_doctype_config(REF_DOCTYPE)


def get_locked_fields() -> dict[str, set[str]]:
    from sriaas_role_permissions.api.config import get_locked_fields as _get_locked_fields

    return _get_locked_fields(REF_DOCTYPE)


def sql_column(fieldname: str) -> str:
    from sriaas_role_permissions.api.config import sql_column as _sql_column

    return _sql_column(get_config().ref_doctype, fieldname)


def user_has_team_leader_field() -> bool:
    fieldname = get_config().team_leader_fieldname
    return bool(fieldname and frappe.db.has_column("User", fieldname))
