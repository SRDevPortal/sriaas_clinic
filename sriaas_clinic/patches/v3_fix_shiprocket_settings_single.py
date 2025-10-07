import frappe

DT = "Shiprocket Settings"
MODULE = "SRIAAS Clinic"

FIELDS = [
    {"fieldname": "api_email",       "fieldtype": "Data",     "label": "API Email",       "options": "Email", "reqd": 1},
    {"fieldname": "api_password",    "fieldtype": "Password", "label": "API Password",    "reqd": 1},
    {"fieldname": "pickup_location", "fieldtype": "Data",     "label": "Pickup Location", "reqd": 1},
    {"fieldname": "enable_sync",     "fieldtype": "Check",    "label": "Enable Sync",     "default": "0", "reqd": 1},
]

PERMS = [
    {"role": "System Manager", "read": 1, "write": 1},
    {"role": "Administrator",  "read": 1, "write": 1},
]

def _delete_reports_pointing_to_doctype():
    reports = frappe.get_all("Report", filters={"ref_doctype": DT}, pluck="name")
    for r in reports:
        frappe.delete_doc("Report", r, ignore_permissions=True, force=1)

def _create_single():
    doc = frappe.get_doc({
        "doctype": "DocType",
        "name": DT,
        "module": MODULE,
        "is_single": 1,
        "custom": 0,
        "track_changes": 1,
        "fields": FIELDS,
        "permissions": PERMS,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

def _convert_existing_to_single():
    dt = frappe.get_doc("DocType", DT)

    # Remove reports attached to this doctype (Singles cannot have reports)
    _delete_reports_pointing_to_doctype()

    # Clear conflicting flags for Singles
    dt.is_single = 1
    dt.is_submittable = 0
    dt.is_tree = 0
    dt.istable = 0
    dt.is_virtual = 0
    dt.allow_rename = 0
    if hasattr(dt, "has_web_view"): dt.has_web_view = 0
    if hasattr(dt, "index_web_pages"): dt.index_web_pages = 0

    # Clear naming fields (Singles have no naming)
    dt.autoname = ""
    dt.naming_rule = ""
    dt.title_field = ""

    # Ensure module and standardness
    dt.custom = 0
    if dt.module != MODULE:
        dt.module = MODULE

    # Ensure required fields exist
    existing = {f.fieldname for f in dt.fields}
    for f in FIELDS:
        if f["fieldname"] not in existing:
            dt.append("fields", f)

    # Ensure basic perms
    have = {(p.role, int(bool(p.read)), int(bool(p.write))) for p in dt.permissions}
    for p in PERMS:
        key = (p["role"], p.get("read", 0), p.get("write", 0))
        if key not in have:
            dt.append("permissions", p)

    dt.save(ignore_permissions=True)
    frappe.db.commit()

def _seed_defaults():
    def _setdefault(key, val):
        cur = frappe.db.get_single_value(DT, key)
        if cur in (None, "", 0):
            frappe.db.set_value(DT, key, val)
    _setdefault("enable_sync", 0)

def execute():
    if not frappe.db.exists("DocType", DT):
        _create_single()
    else:
        meta = frappe.get_meta(DT)
        if not getattr(meta, "issingle", 0):
            _convert_existing_to_single()
    frappe.clear_cache(doctype=DT)
    _seed_defaults()
