import frappe

MODULE = "SRIAAS Clinic"
APP = "sriaas_clinic"

# Doctypes to hard-clean (module-scoped)
CUSTOMIZATION_DT_LIST = [
    "Custom Field",
    "Property Setter",
    "Client Script",
    "Server Script",
    "Workspace",
    "Workspace Link",
    "Print Format",
    "Report",
    "Dashboard Chart",
    "Notification",
    "Web Template",
    "Form Tour",
    "Form Tour Step",
    "Custom DocPerm",
]

def _delete_all(dt, filters):
    names = frappe.get_all(dt, pluck="name", filters=filters)
    for name in names:
        try:
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True, delete_permanently=True)
        except Exception:
            # Fallback: mark as deprecated/disabled (rarely needed)
            if frappe.db.has_column(dt, "disabled"):
                frappe.db.set_value(dt, name, "disabled", 1)

def _delete_app_doctypes():
    """
    Remove any non-standard doctypes that still point to our app/module.
    Usually bench uninstall removes them, but this is a safety net.
    """
    dts = frappe.get_all("DocType", fields=["name", "module", "custom", "issingle", "istable", "is_virtual"],
                         filters={"module": MODULE})
    for d in dts:
        # Delete only doctypes that belong to our module and are not core
        # (Uninstall normally handles these, but we double-sanitize.)
        try:
            frappe.delete_doc("DocType", d.name, force=True, ignore_permissions=True, delete_permanently=True)
        except Exception:
            pass

def before_uninstall():
    """
    Do heavy cleanup BEFORE the framework drops app schema.
    """
    frappe.clear_cache()

    # 1) Remove module-scoped customizations on standard doctypes
    for dt in CUSTOMIZATION_DT_LIST:
        _delete_all(dt, {"module": MODULE})

    # Extra heuristics: some rows miss 'module' but do have 'app' or 'owner' references.
    # Try a second pass where 'module' field doesn't exist / wasn't set.
    # (We check via WHERE name IN fixtures list could be added, but module-scoping should be enough.)
    # Example for Custom Field missing module:
    if "app" in frappe.get_meta("Custom Field").get_valid_columns():
        _delete_all("Custom Field", {"app": APP})

    # 2) Safety net: delete any doctypes that were created inside our module
    _delete_app_doctypes()

    frappe.db.commit()

def after_uninstall():
    # Optionally remove the Module Def record itself (harmless if it stays)
    if frappe.db.exists("Module Def", MODULE):
        try:
            frappe.delete_doc("Module Def", MODULE, force=True, ignore_permissions=True, delete_permanently=True)
        except Exception:
            pass
    frappe.db.commit()

