import frappe
from frappe import _


PAYMENT_FIELDS = ("name", "posting_date", "paid_amount", "mode_of_payment")


def _has_payment_viewer_role(user: str) -> bool:
    try:
        from sriaas_role_permissions.api.roles import get_roles, user_has_any_role

        return user_has_any_role(user, get_roles("Patient", "Payment Viewer"))
    except Exception:
        frappe.logger("sriaas").exception("Failed to evaluate Patient Payment Viewer roles")
        return False


def _can_view_patient_payment_summary(patient: str, user: str) -> bool:
    if user == "Administrator":
        return True

    if _has_payment_viewer_role(user):
        return True

    if frappe.has_permission("Payment Entry", "read", user=user):
        return True

    return False


@frappe.whitelist()
def get_patient_payment_entries(patient: str, limit_page_length: int = 100) -> list[dict]:
    if not patient:
        return []

    patient_doc = frappe.get_doc("Patient", patient)
    if not patient_doc.has_permission("read"):
        raise frappe.PermissionError

    if not patient_doc.customer:
        return []

    user = frappe.session.user
    if not _can_view_patient_payment_summary(patient_doc.name, user):
        raise frappe.PermissionError(_("Not permitted to view patient payment summary"))

    limit = max(1, min(int(limit_page_length or 100), 100))
    entries = frappe.db.get_all(
        "Payment Entry",
        filters={
            "party_type": "Customer",
            "party": patient_doc.customer,
            "docstatus": 1,
        },
        fields=PAYMENT_FIELDS,
        order_by="posting_date desc, creation desc",
        limit_page_length=limit,
    )

    return entries
