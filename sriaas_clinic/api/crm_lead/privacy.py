"""CRM number integration owned by Sriaas Clinic."""
import frappe


@frappe.whitelist()
def get_number_details(name):
    from privacy_shield.api import get_numbers
    return get_numbers("CRM Lead", name)


@frappe.whitelist()
def desk_getdoc(doctype, name):
    from privacy_shield.desk import getdoc
    return getdoc(doctype, name)


@frappe.whitelist(methods=["POST", "PUT"])
def desk_savedocs(doc, action):
    from privacy_shield.desk import savedocs
    return savedocs(doc, action)


@frappe.whitelist()
def client_get(doctype, name=None, filters=None, parent=None):
    from privacy_shield.desk import get
    return get(doctype, name, filters, parent)


@frappe.whitelist(methods=["POST", "PUT"])
def client_save(doc):
    from privacy_shield.desk import save
    return save(doc)


@frappe.whitelist(methods=["POST", "PUT"])
def client_set_value(doctype, name, fieldname, value=None):
    from privacy_shield.desk import set_value
    return set_value(doctype, name, fieldname, value)


@frappe.whitelist()
def client_get_list(doctype, fields=None, filters=None, group_by=None, order_by=None,
                    limit_start=None, limit_page_length=20, parent=None, debug=False,
                    as_dict=True, or_filters=None):
    from privacy_shield.listing import get_list
    return get_list(doctype, fields, filters, group_by, order_by, limit_start,
                    limit_page_length, parent, debug, as_dict, or_filters)


@frappe.whitelist()
def client_get_value(doctype, fieldname, filters=None, as_dict=True, debug=False, parent=None):
    from privacy_shield.listing import get_value
    return get_value(doctype,fieldname,filters,as_dict,debug,parent)


@frappe.whitelist()
def search_widget(doctype, txt, query=None, searchfield=None, start=0, page_length=10,
                  filters=None, filter_fields=None, as_dict=False,
                  reference_doctype=None, ignore_user_permissions=False):
    from privacy_shield.listing import search_widget as adapter
    return adapter(doctype,txt,query,searchfield,start,page_length,filters,filter_fields,
                   as_dict,reference_doctype,ignore_user_permissions)


@frappe.whitelist()
def search_link(doctype, txt, query=None, filters=None, page_length=10, searchfield=None,
                reference_doctype=None, ignore_user_permissions=False):
    from privacy_shield.listing import search_link as adapter
    return adapter(doctype,txt,query,filters,page_length,searchfield,reference_doctype,ignore_user_permissions)


@frappe.whitelist()
def reportview_get():
    from privacy_shield.listing import reportview_get as adapter
    return adapter()


@frappe.whitelist()
def reportview_get_list():
    from privacy_shield.listing import reportview_get_list as adapter
    return adapter()


@frappe.whitelist(methods=["POST", "PUT"])
def lifecycle_insert(doc=None):
    from privacy_shield.lifecycle import insert
    return insert(doc)


@frappe.whitelist(methods=["POST", "PUT"])
def lifecycle_insert_many(docs=None):
    from privacy_shield.lifecycle import insert_many
    return insert_many(docs)


@frappe.whitelist(methods=["POST", "PUT"])
def lifecycle_submit(doc):
    from privacy_shield.lifecycle import submit
    return submit(doc)


@frappe.whitelist(methods=["POST", "PUT"])
def lifecycle_cancel(doctype, name):
    from privacy_shield.lifecycle import cancel
    return cancel(doctype, name)


@frappe.whitelist(methods=["POST", "PUT"])
def lifecycle_bulk_update(docs):
    from privacy_shield.lifecycle import bulk_update
    return bulk_update(docs)


@frappe.whitelist(methods=["POST", "PUT"])
def lifecycle_desk_cancel(doctype=None, name=None, workflow_state_fieldname=None, workflow_state=None):
    from privacy_shield.lifecycle import desk_cancel
    return desk_cancel(doctype, name, workflow_state_fieldname, workflow_state)
