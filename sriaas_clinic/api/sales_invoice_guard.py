# sriaas_clinic/api/sales_invoice_guard.py

from __future__ import annotations
import frappe
from frappe import _

ROLE_WAREHOUSE_MAP = {
    "OPD Biller": "OPD Warehouse - SR",
    "Packaging Biller": "Packaging Warehouse - SR",
}

BYPASS_ROLES = {"System Manager"}
BYPASS_USERS = {"Administrator"}


def _get_allowed_warehouse(user: str) -> str | None:
    """
    Return allowed warehouse ONLY for restricted biller users.
    Admin / System Manager → unrestricted
    """
    roles = set(frappe.get_roles(user))

    if user in BYPASS_USERS or roles & BYPASS_ROLES:
        return None

    for role, warehouse in ROLE_WAREHOUSE_MAP.items():
        if role in roles:
            return warehouse

    return None


def _has_other_warehouse(doc, allowed_warehouse: str) -> bool:
    """Check parent + item warehouses."""
    if doc.set_warehouse and doc.set_warehouse != allowed_warehouse:
        return True

    for row in doc.get("items", []):
        if row.warehouse and row.warehouse != allowed_warehouse:
            return True

    return False


# validate, before_submit, before_cancel, before_amend handlers
def validate_sales_invoice_warehouse(doc, method=None):
    """
    HARD GUARD — blocks illegal mutations early.
    """
    user = frappe.session.user
    allowed_warehouse = _get_allowed_warehouse(user)

    # Admin / System Manager / Non-biller
    if not allowed_warehouse:
        return

    if _has_other_warehouse(doc, allowed_warehouse):
        frappe.throw(
            f"You are allowed to work only on Sales Invoices for warehouse: {allowed_warehouse}",
            frappe.PermissionError,
        )


# before_submit handler
def validate_kit_total_vs_grand_total(doc, method=None):
    """
    Prevent submission if Grand Total < Kit Total Price
    when a kit is applied.
    """

    # Skip returns / credit notes
    if doc.is_return or doc.docstatus == 2:
        return
    
    # Only enforce when kit exists
    if not doc.sr_kit_name:
        return

    kit_total = doc.sr_kit_total_price or 0
    grand_total = doc.grand_total or 0

    if kit_total <= 0:
        return

    if grand_total < kit_total:
        frappe.throw(
            _(
                "Grand Total (₹{0}) cannot be less than Kit Total Price (₹{1}). "
                "Please adjust item prices or discounts."
            ).format(
                frappe.utils.fmt_money(grand_total, currency=doc.currency),
                frappe.utils.fmt_money(kit_total, currency=doc.currency),
            ),
            title=_("Invalid Invoice Total"),
        )
