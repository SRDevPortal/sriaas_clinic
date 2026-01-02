# sriaas_clinic/api/sales_invoice_guard.py

from __future__ import annotations
import frappe

ROLE_WAREHOUSE_MAP = {
    "OPD Biller": "OPD Warehouse - SR",
    "Packaging Biller": "Packaging Warehouse - SR",
}

# Roles that should NEVER be restricted
BYPASS_ROLES = {
    "System Manager",
}

BYPASS_USERS = {
    "Administrator",
}


def _get_allowed_warehouse(user: str) -> str | None:
    """
    Return allowed warehouse ONLY for restricted biller users.
    Admin / System Manager must bypass all restrictions.
    """
    roles = set(frappe.get_roles(user))

    # 🚨 FULL BYPASS
    if user in BYPASS_USERS or roles.intersection(BYPASS_ROLES):
        return None

    # Apply restriction only if user has a biller role
    for role, warehouse in ROLE_WAREHOUSE_MAP.items():
        if role in roles:
            return warehouse

    return None


def _has_other_warehouse(doc, allowed_warehouse: str) -> bool:
    """
    Check if Sales Invoice uses any warehouse
    other than the allowed warehouse.
    """
    # Source warehouse
    if doc.set_warehouse and doc.set_warehouse != allowed_warehouse:
        return True

    # Item-level warehouses
    for row in doc.get("items", []):
        if row.warehouse and row.warehouse != allowed_warehouse:
            return True

    return False


def validate_sales_invoice_warehouse(doc, method=None):
    """
    Warehouse ownership guard for Sales Invoice.

    Enforced for:
    - Create
    - Save
    - Submit
    - Cancel
    - Amend

    Not enforced for:
    - Read
    - Print
    - Administrator / System Manager
    """
    user = frappe.session.user
    allowed_warehouse = _get_allowed_warehouse(user)

    # Non-biller users → unrestricted
    if not allowed_warehouse:
        return

    # Guard enforcement
    if _has_other_warehouse(doc, allowed_warehouse):
        frappe.throw(
            (
                f"You are allowed to work only on Sales Invoices "
                f"for warehouse: {allowed_warehouse}"
            ),
            frappe.PermissionError,
        )
