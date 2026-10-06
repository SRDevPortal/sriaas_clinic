"""Clinic-owned CRM mention preview protection and deduplication."""
import frappe
from crm.fcrm.doctype.crm_notification.crm_notification import CRMNotification


class PrivacyCRMNotification(CRMNotification):
    def insert(self, *args, **kwargs):
        if frappe.conf.get("privacy_shield_desk_enabled", False) and self.get("type") == "Mention":
            from privacy_shield.import_access import TARGETS
            from privacy_shield.notification_privacy import NOTICE
            if self.get("reference_doctype") in TARGETS:
                self.message = NOTICE
                self.notification_text = "You were mentioned in a comment"
                # CRM's caller checks duplicates before insert using the original
                # prose. Check the sanitized equivalent before delegating.
                fields = ("from_user", "to_user", "type", "message", "notification_text",
                          "notification_type_doctype", "notification_type_doc", "reference_doctype", "reference_name")
                if self.flags.ignore_permissions or kwargs.get("ignore_permissions"):
                    existing = frappe.db.exists("CRM Notification", {key: self.get(key) for key in fields})
                    if existing:
                        return frappe.get_doc("CRM Notification", existing)
        return super().insert(*args, **kwargs)


@frappe.whitelist()
def get_notifications():
    from crm.api.notifications import get_notifications as original
    from privacy_shield.raw_access import restricted
    result = original()
    if not restricted():
        return result
    from privacy_shield.notification_reads import NOTICE
    # CRM normalizes every non-deal reference to 'lead' in this response.
    # Treat that whole category conservatively rather than infer raw types.
    projected = []
    for row in result:
        if row.get("reference_doctype") != "deal":
            row = {key: row.get(key) for key in ("creation", "from_user", "type", "to_user", "read", "hash", "notification_type_doctype", "notification_type_doc", "reference_doctype", "reference_name", "route_name")}
            row["notification_text"] = NOTICE
        projected.append(row)
    return projected


@frappe.whitelist()
def mark_as_read(user=None, doc=None):
    from privacy_shield.raw_access import restricted
    if not restricted():
        from crm.api.notifications import mark_as_read as original
        return original(user=user, doc=doc)
    if user and user != frappe.session.user:
        raise frappe.PermissionError("Only your own notifications can be marked as read.")
    if frappe.flags.read_only:
        return
    filters = {"to_user": frappe.session.user, "read": 0}
    or_filters = [{"comment": doc}, {"notification_type_doc": doc}] if doc else None
    for row in frappe.get_all("CRM Notification", filters=filters, or_filters=or_filters, fields=["name"]):
        frappe.db.set_value("CRM Notification", {"name": row.name, "to_user": frappe.session.user}, "read", 1, update_modified=False)
