# apps/sriaas_clinic/sriaas_clinic/setup/utils.py
import json
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

def ensure_field_before(doctype: str, fieldname: str, before: str):
    meta = frappe.get_meta(doctype)
    fields = [df.fieldname for df in meta.fields]
    if fieldname not in fields or before not in fields:
        return
    fields.remove(fieldname)
    idx = fields.index(before)
    fields.insert(idx, fieldname)
    # WRITE JSON, not comma-string
    upsert_property_setter(doctype, None, "field_order", json.dumps(fields), "Text")
    frappe.clear_cache(doctype=doctype)

def ensure_field_after(doctype: str, fieldname: str, after: str):
    meta = frappe.get_meta(doctype)
    fields = [df.fieldname for df in meta.fields]
    if fieldname not in fields or after not in fields:
        return
    fields.remove(fieldname)
    idx = fields.index(after)
    fields.insert(idx + 1, fieldname)
    upsert_property_setter(doctype, None, "field_order", json.dumps(fields), "Text")
    frappe.clear_cache(doctype=doctype)

def set_full_field_order(doctype: str, ordered_fieldnames: list[str]):
    upsert_property_setter(doctype, None, "field_order", json.dumps(ordered_fieldnames), "Text")
    frappe.clear_cache(doctype=doctype)
