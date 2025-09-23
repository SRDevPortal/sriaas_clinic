# sriaas_clinic/setup/utils.py
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields as _ccf

MODULE_DEF_NAME = "SRIAAS Clinic"   # Desk Module Def label
APP_PY_MODULE   = "sriaas_clinic"   # Python package

def ensure_module_def():
    """Make sure the Module Def row exists."""
    if not frappe.db.exists("Module Def", MODULE_DEF_NAME):
        frappe.get_doc({
            "doctype": "Module Def",
            "module_name": MODULE_DEF_NAME,
            "app_name": APP_PY_MODULE
        }).insert(ignore_permissions=True)

# def ensure_module_def(module_name: str, app_name: str):
#     """Make sure the Module Def row exists."""
#     if not frappe.db.exists("Module Def", module_name):
#         frappe.get_doc({
#             "doctype": "Module Def",
#             "module_name": module_name,
#             "app_name": app_name
#         }).insert(ignore_permissions=True)

def reload_local_json_doctypes(names: list[str]):
    """Reload DocTypes shipped as JSON under doctype/"""
    for dn in names or []:
        try:
            frappe.reload_doc(APP_PY_MODULE, "doctype", dn)
        except Exception:
            pass

def create_cf_with_module(mapping: dict, module: str = MODULE_DEF_NAME):
    """create_custom_fields but auto-injects `module` so fixtures & uninstall are clean."""
    for dt, fields in mapping.items():
        for f in fields:
            f.setdefault("module", module)
    _ccf(mapping, ignore_validate=True)

# def upsert_property_setter(doctype, fieldname, prop, value, property_type, module: str = MODULE_DEF_NAME):
#     """Idempotent PS with module tagging."""
#     name = f"{doctype}-{fieldname}-{prop}"
#     if frappe.db.exists("Property Setter", name):
#         ps = frappe.get_doc("Property Setter", name)
#         ps.value = value
#         ps.property_type = property_type
#         ps.module = module
#         ps.save(ignore_permissions=True)
#     else:
#         frappe.get_doc({
#             "doctype": "Property Setter",
#             "doctype_or_field": "DocField",
#             "doc_type": doctype,
#             "field_name": fieldname,
#             "property": prop,
#             "value": value,
#             "property_type": property_type,
#             "name": name,
#             "module": module,
#         }).insert(ignore_permissions=True)

def upsert_property_setter(doctype, fieldname, prop, value, property_type, module: str = MODULE_DEF_NAME):
    """Idempotent Property Setter with module tagging.
       If fieldname is falsy (None/""), create a DocType-level PS; else DocField-level.
    """
    is_dt_level = not fieldname
    ps_name = f"{doctype}-{prop}" if is_dt_level else f"{doctype}-{fieldname}-{prop}"

    if frappe.db.exists("Property Setter", ps_name):
        ps = frappe.get_doc("Property Setter", ps_name)
    else:
        ps = frappe.new_doc("Property Setter")
        ps.name = ps_name
        ps.doc_type = doctype
        ps.doctype_or_field = "DocType" if is_dt_level else "DocField"
        ps.field_name = None if is_dt_level else fieldname
        ps.module = module

    ps.property = prop
    ps.value = value
    ps.property_type = property_type
    ps.module = module
    ps.save(ignore_permissions=True)

def collapse_section(dt: str, fieldname: str, collapse: bool = True):
    if not frappe.get_meta(dt).get_field(fieldname):
        return
    upsert_property_setter(dt, fieldname, "collapsible", "1" if collapse else "0", "Check")

def set_label(dt: str, fieldname: str, new_label: str):
    if not frappe.get_meta(dt).get_field(fieldname):
        return
    upsert_property_setter(dt, fieldname, "label", new_label, "Data")
