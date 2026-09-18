"""CRM SPA privacy adapter, owned entirely by the clinic extension.

The existing CRM implementation retains record permissions and counting/navigation.
No global query monkey-patch or mutation of persisted view settings is used.
"""
from copy import deepcopy
import json
import frappe
from frappe.utils import cint
from privacy_shield.desk import enabled
from privacy_shield.policy import current_capabilities
from privacy_shield.registry import DISPLAY_FIELDS, EXTRA_SENSITIVE_FIELDS
from privacy_shield.listing import columns as query_columns, validate_query
from privacy_shield.projections import project_numbers

MAPPING = DISPLAY_FIELDS["CRM Lead"]
REVERSE = {v:k for k,v in MAPPING.items()}
ALIASES = EXTRA_SENSITIVE_FIELDS["CRM Lead"]
SENSITIVE = set(MAPPING) | set(REVERSE) | set(ALIASES)


def decoded(value, default):
    return deepcopy(json.loads(value) if isinstance(value,str) and value else value if value is not None else default)


def names(values):
    values = decoded(values, [])
    if not isinstance(values,list): raise frappe.ValidationError("Expected a field list")
    if not values: return []
    return query_columns("CRM Lead",values)[1]


def check_selector(value, full):
    if not value: return
    query_columns("CRM Lead",[value])
    if value in REVERSE or (not full and value in SENSITIVE):
        raise frappe.PermissionError("Phone fields cannot be used as privacy-pilot grouping or card titles")


def prepare(args, full, defaults, saved=None):
    args = deepcopy(args)
    view = decoded(args.get("view"), {})
    if not isinstance(view,dict): raise frappe.ValidationError("Invalid view")
    for value in (args.get("column_field"),args.get("title_field"),view.get("group_by_field")):
        check_selector(value, full)
    # Grouping of non-phone fields remains supported by CRM.
    validate_query("CRM Lead",args.get("filters"),args.get("default_filters"),None,args.get("order_by"),full)
    for key in ("page_length","page_length_count"):
        size=cint(args.get(key,20))
        if not 1 <= size <= 200: raise frappe.ValidationError("Privacy pilot page size must be between 1 and 200")
        args[key]=size
    selected_columns=decoded(args.get("columns"),[])
    selected_rows=decoded(args.get("rows"),[])
    if not selected_columns and not selected_rows:
        selected_columns=decoded((saved or defaults).get("columns"),[])
        selected_rows=decoded((saved or defaults).get("rows"),[])
    args["rows"]=names(selected_rows or defaults["rows"])
    if not isinstance(selected_columns,list): raise frappe.ValidationError("Invalid columns")
    for column in selected_columns:
        if not isinstance(column,dict): raise frappe.ValidationError("Invalid column")
        column["key"]=query_columns("CRM Lead",[column.get("key")])[1][0]
    args["columns"]=selected_columns
    args["kanban_fields"]=names(args.get("kanban_fields") or defaults.get("kanban_fields"))
    args["view"]=view
    buckets=decoded(args.get("kanban_columns"),[])
    if not isinstance(buckets,list) or len(buckets)>50:
        raise frappe.ValidationError("Privacy pilot supports up to 50 Kanban columns")
    for bucket in buckets:
        if not isinstance(bucket,dict): raise frappe.ValidationError("Invalid Kanban column")
        if not 1 <= cint(bucket.get("page_length",20)) <= 200:
            raise frappe.ValidationError("Invalid Kanban page length")
    args["kanban_columns"]=buckets
    return args


def project_layout(result, full):
    result=deepcopy(result)
    def field(value): return MAPPING.get(value,value) if not full else value
    def fields(values): return list(dict.fromkeys(field(v) for v in values if full or v not in ALIASES))
    def metadata(items,key):
        output=[];seen=set()
        for item in items:
            item=deepcopy(item);source=item.get(key)
            if not full and source in ALIASES: continue
            item[key]=field(source)
            if not full and source in MAPPING or source in REVERSE:
                item["label"]="Masked Mobile" if item[key]=="mask_mobile" else "Masked Phone"
                item["type"]="Data";item["fieldtype"]="Data";item["options"]=None
                item["read_only"]=1
            if item[key] not in seen: output.append(item);seen.add(item[key])
        return output
    def row(value): return project_numbers(value,MAPPING,full,ALIASES)
    if result.get("view_type")=="kanban":
        for bucket in result.get("data",[]):
            bucket["data"]=[row(value) for value in bucket.get("data",[])]
            bucket["fields"]=fields(bucket.get("fields",[]))
    else: result["data"]=[row(value) for value in result.get("data",[])]
    for key in ("rows","kanban_fields"):
        result[key]=fields(result.get(key,[]))
    result["columns"]=metadata(result.get("columns",[]),"key")
    result["fields"]=metadata(result.get("fields",[]),"fieldname")
    # Saved-view definitions may contain literal phone filter values. Exclude such
    # views for restricted users rather than silently broadening their filters.
    views=[]
    for original in result.get("views",[]):
        item=deepcopy(original)
        try:
            validate_query("CRM Lead",item.get("filters"),None,None,item.get("order_by"),full)
            for key in ("column_field","title_field","group_by_field"): check_selector(item.get(key),full)
        except (frappe.ValidationError,frappe.PermissionError,ValueError):
            continue
        for key in ("rows","kanban_fields"):
            if item.get(key): item[key]=json.dumps(fields(decoded(item[key],[])))
        if item.get("columns"): item["columns"]=json.dumps(metadata(decoded(item["columns"],[]),"key"))
        views.append(item)
    result["views"]=views
    return result


@frappe.whitelist()
def get_data(doctype, filters, order_by, page_length=20, page_length_count=20,
             column_field=None, title_field=None, columns=None, rows=None,
             kanban_columns=None, kanban_fields=None, view=None, default_filters=None):
    from crm.api.doc import get_data as original
    if "crm_lead_dedupe" in frappe.get_installed_apps():
        from crm_lead_dedupe.api.crm_doc_guard import get_data as original
    args=dict(doctype=doctype,filters=filters,order_by=order_by,page_length=page_length,
        page_length_count=page_length_count,column_field=column_field,title_field=title_field,
        columns=columns or [],rows=rows or [],kanban_columns=kanban_columns or [],
        kanban_fields=kanban_fields or [],view=view,default_filters=default_filters)
    if doctype!="CRM Lead" or not enabled(doctype): return original(**args)
    from frappe.model.document import get_controller
    controller=get_controller(doctype)
    defaults=deepcopy(controller.default_list_data())
    defaults.update(controller.default_kanban_settings())
    full=current_capabilities().view_full
    saved=None
    decoded_view=decoded(view,{})
    if not decoded(columns,[]) and not decoded(rows,[]) and decoded_view.get("view_type")!="kanban":
        criteria={"dt":doctype,"type":decoded_view.get("view_type") or "list","is_standard":1,"user":frappe.session.user}
        if frappe.db.exists("CRM View Settings",criteria):
            config=frappe.get_doc("CRM View Settings",criteria)
            saved={"columns":config.columns,"rows":config.rows}
    desired_columns=decoded(columns,[]) or decoded((saved or defaults).get("columns"),[])
    desired_kanban=decoded(kanban_fields,[]) or decoded(defaults.get("kanban_fields"),[])
    args=prepare(args,full,defaults,saved)
    if args["view"].get("view_type")=="kanban":
        args["column_field"]=args["column_field"] or defaults["column_field"]
        args["title_field"]=args["title_field"] or defaults["title_field"]
        check_selector(args["column_field"],full);check_selector(args["title_field"],full)
        if not args["kanban_columns"]:
            df=frappe.get_meta(doctype).get_field(args["column_field"])
            if not df or df.fieldtype!="Select":
                raise frappe.ValidationError("Choose explicit Kanban columns for non-Select grouping")
            options=[value for value in (df.options or "").split("\n") if value]
            if len(options)>50: raise frappe.ValidationError("Too many Kanban columns")
            args["kanban_columns"]=[{"name":value} for value in options]
    result=project_layout(original(**args),full)
    if full:
        # An explicitly selected virtual field remains masked for full viewers too.
        if any(item.get("key") in REVERSE for item in desired_columns):
            result["columns"]=desired_columns
            for item in result["columns"]:
                if item.get("key") in REVERSE:
                    item.update(type="Data",options=None,label="Masked Mobile" if item["key"]=="mask_mobile" else "Masked Phone")
        if any(field in REVERSE for field in desired_kanban):
            result["kanban_fields"]=desired_kanban
            for bucket in result.get("data",[]) if result.get("view_type")=="kanban" else []:
                bucket["fields"]=desired_kanban

    if not decoded(columns,[]) and not decoded(rows,[]) and not decoded_view.get("custom_view_name"):
        result["is_default"]=not bool(saved)
    return result


def project_sidepanel(layout):
    """Use the projected document keys without changing saved CRM layouts."""
    result = deepcopy(layout)
    for section in result:
        for column in section.get("columns") or []:
            projected = []
            for field in column.get("fields") or []:
                if not isinstance(field, dict):
                    projected.append(field)
                    continue
                source = field.get("fieldname")
                if source in ALIASES:
                    continue
                if source in MAPPING or source in REVERSE:
                    target = MAPPING.get(source, source)
                    field.update(
                        fieldname=target,
                        label="Masked Mobile" if target == "mask_mobile" else "Masked Phone",
                        fieldtype="Data", options=None, read_only=1, reqd=0,
                        fetch_from=None, default=None,
                        mandatory_depends_on=None, read_only_depends_on=None,
                        tooltip="Your role can view only the masked number.",
                    )
                projected.append(field)
            column["fields"] = projected
    return result


@frappe.whitelist()
def get_sidepanel_sections(doctype):
    from crm.fcrm.doctype.crm_fields_layout.crm_fields_layout import get_sidepanel_sections as original
    layout = original(doctype)
    if doctype != "CRM Lead" or not enabled(doctype) or current_capabilities().view_full:
        return layout
    return project_sidepanel(layout)
