# sriaas_clinic/setup/sales_invoice.py
import frappe
from .utils import create_cf_with_module, upsert_property_setter, upsert_title_field, ensure_field_after

PARENT = "Sales Invoice"
CHILD = "Sales Invoice Item"

RIGHT_COL_CB = "column_break1"


def apply():
    _make_invoice_fields()
    if frappe.db.exists("DocType", PARENT) and frappe.db.exists("DocType", CHILD):
        _setup_cost_section()
        _setup_invoice_item_fields()
    _setup_invoice_calculation_section()
    _apply_invoice_ui_customizations()


def _lead_source_dt() -> str:
    if frappe.db.exists("DocType", "SR Lead Source"):
        return "SR Lead Source"
    if frappe.db.exists("DocType", "CRM Lead Source"):
        return "CRM Lead Source"
    return "Lead Source"


def _make_invoice_fields():
    lead_source_dt = _lead_source_dt()

    create_cf_with_module({
        PARENT: [
            {"fieldname": "sr_si_patient_id", "label": "Patient ID", "fieldtype": "Data", "read_only": 1, "fetch_from": "patient.sr_patient_id", "insert_after": "customer_name"},
            {"fieldname": "sr_si_patient_department", "label": "Patient Department", "fieldtype": "Link", "options": "Medical Department", "in_list_view": 1, "in_standard_filter": 1, "read_only": 1, "fetch_from": "patient.sr_medical_department", "insert_after": "sr_si_patient_id"},
            {"fieldname": "sr_si_track_sb", "label": "Order Tracking Details", "fieldtype": "Section Break", "collapsible": 1, "insert_after": "gst_breakup_table"},
            {"fieldname": "sr_si_order_source", "label": "Order Source", "fieldtype": "Link", "options": lead_source_dt, "in_list_view": 1, "in_standard_filter": 1, "insert_after": "sr_si_track_sb"},
            {"fieldname": "sr_si_encounter_place", "label": "Encounter Place", "fieldtype": "Data", "in_list_view": 1, "in_standard_filter": 1, "insert_after": "sr_si_order_source"},
            {"fieldname": "sr_si_sales_type", "label": "Sales Type", "fieldtype": "Link", "options": "SR Sales Type", "in_list_view": 1, "in_standard_filter": 1, "insert_after": "sr_si_encounter_place"},
            {"fieldname": "sr_si_delivery_type", "label": "Delivery Type", "fieldtype": "Link", "options": "SR Delivery Type", "in_list_view": 1, "in_standard_filter": 1, "allow_on_submit": 1, "insert_after": "sr_si_sales_type"},
            {"fieldname": "created_by_agent", "label": "Created By", "fieldtype": "Link", "options": "User", "read_only": 1, "insert_after": "due_date"},
        ]
    })


def _setup_invoice_calculation_section():
    create_cf_with_module({
        PARENT: [
            {"fieldname": "sr_invoice_calc_sb", "label": "Invoice Calculation", "fieldtype": "Section Break", "insert_after": "ignore_pricing_rule"},
            {"fieldname": "sr_kit_name", "label": "Kit Name", "fieldtype": "Data", "read_only": 1, "insert_after": "sr_invoice_calc_sb"},
            {"fieldname": "sr_kit_total_price", "label": "Kit Total Price", "fieldtype": "Currency", "read_only": 1, "insert_after": "sr_kit_name"},
            {"fieldname": "sr_non_kit_total_price", "label": "Non Kit Total Price", "fieldtype": "Currency", "read_only": 1, "insert_after": "sr_kit_total_price"},
        ]
    })


def _setup_cost_section():
    create_cf_with_module({
        PARENT: [
            {"fieldname": "sr_cost_section", "label": "Cost (Admin)", "fieldtype": "Section Break", "insert_after": "disable_rounded_total"},
            {"fieldname": "sr_total_cost", "label": "Total Cost", "fieldtype": "Currency", "read_only": 1, "insert_after": "sr_cost_section"},
            {"fieldname": "sr_cost_pct_overall", "label": "Cost % Overall", "fieldtype": "Percent", "read_only": 1, "insert_after": "sr_total_cost", "description": "Total Cost / Grand Total * 100"},
            {"fieldname": "sr_cost_col_break", "fieldtype": "Column Break", "insert_after": "sr_cost_pct_overall"},
            {"fieldname": "sr_margin_overall", "label": "Margin %", "fieldtype": "Percent", "read_only": 1, "insert_after": "sr_cost_col_break", "description": "(Grand Total - Total Cost) / Grand Total * 100"},
        ]
    })


def _setup_invoice_item_fields():
    create_cf_with_module({
        CHILD: [
            {"fieldname": "sr_cost_price", "label": "Cost Price", "fieldtype": "Currency", "read_only": 1, "insert_after": "rate"},
            {"fieldname": "sr_cost_amount", "label": "Cost Amount", "fieldtype": "Currency", "read_only": 1, "insert_after": "sr_cost_price", "description": "qty * sr_cost_price"},
            {"fieldname": "sr_cost_pct", "label": "Cost %", "fieldtype": "Percent", "read_only": 1, "insert_after": "sr_cost_amount", "description": "Cost Price / Rate * 100"},
        ]
    })

    meta = frappe.get_meta(CHILD)
    field_props = {
        "batch_no": {"hidden": "1", "in_list_view": "0", "columns": "1"},
        "price_list_rate": {"hidden": "0", "in_list_view": "1", "columns": "1", "precision": "6"},
        "rate": {"hidden": "0", "in_list_view": "1", "columns": "1", "precision": "6"},
        "discount_percentage": {"hidden": "0", "in_list_view": "1", "columns": "1"},
        "discount_amount": {"hidden": "0", "in_list_view": "1", "columns": "1", "precision": "6"},
        "item_tax_template": {"hidden": "0", "in_list_view": "1", "columns": "2"},
        "item_tax_rate": {"hidden": "0", "in_list_view": "1", "columns": "2"},
        "net_rate": {"hidden": "0", "in_list_view": "1", "columns": "1", "precision": "6"},
        "sr_row_tax_amount": {"hidden": "0", "in_list_view": "1", "columns": "1"},
        "net_amount": {"hidden": "0", "in_list_view": "1", "columns": "1"},
        "amount": {"hidden": "1", "in_list_view": "0"},
    }
    for fieldname, props in field_props.items():
        if not meta.get_field(fieldname):
            continue
        for prop, value in props.items():
            property_type = "Check" if prop in {"hidden", "in_list_view"} else "Int"
            upsert_property_setter(CHILD, fieldname, prop, value, property_type)


def _apply_invoice_ui_customizations():
    ensure_field_after(PARENT, "sr_si_order_source", "sr_si_track_sb")
    ensure_field_after(PARENT, "sr_si_encounter_place", "sr_si_order_source")
    ensure_field_after(PARENT, "sr_si_sales_type", "sr_si_encounter_place")
    ensure_field_after(PARENT, "sr_si_delivery_type", "sr_si_sales_type")
    ensure_field_after(PARENT, "sr_invoice_calc_sb", "ignore_pricing_rule")
    ensure_field_after(PARENT, "sr_kit_name", "sr_invoice_calc_sb")
    ensure_field_after(PARENT, "sr_kit_total_price", "sr_kit_name")
    ensure_field_after(PARENT, "sr_non_kit_total_price", "sr_kit_total_price")

    # Standard batch_no is retained for historical/legacy rows but hidden by
    # default. The hybrid scanner reveals it only for a legacy Batch scan.
    ensure_field_after(CHILD, "price_list_rate", "qty")
    ensure_field_after(CHILD, "rate", "price_list_rate")
    ensure_field_after(CHILD, "discount_percentage", "rate")
    ensure_field_after(CHILD, "discount_amount", "discount_percentage")
    ensure_field_after(CHILD, "item_tax_template", "discount_amount")
    ensure_field_after(CHILD, "item_tax_rate", "item_tax_template")
    ensure_field_after(CHILD, "net_rate", "item_tax_rate")
    ensure_field_after(CHILD, "sr_row_tax_amount", "net_rate")
    ensure_field_after(CHILD, "net_amount", "sr_row_tax_amount")

    targets = (
        "customer", "ref_practitioner", "customer_name", "service_unit", "ewaybill", "e_waybill_status",
        "allocate_advances_automatically", "get_advances", "advances", "redeem_loyalty_points",
        "sr_si_payment_history_sb", "sr_si_payment_term", "sr_si_paid_amount", "sr_si_payment_history_cb",
        "sr_si_mode_of_payment", "sr_si_outstanding_amount", "apply_discount_on", "additional_discount_percentage",
        "discount_amount", "base_discount_amount",
    )

    meta = frappe.get_meta(PARENT)
    for fieldname in targets:
        if not meta.get_field(fieldname):
            continue
        upsert_property_setter(PARENT, fieldname, "hidden", "1", "Check")
        upsert_property_setter(PARENT, fieldname, "print_hide", "1", "Check")
        upsert_property_setter(PARENT, fieldname, "in_list_view", "0", "Check")
        upsert_property_setter(PARENT, fieldname, "in_standard_filter", "0", "Check")

    if meta.get_field("company"):
        upsert_property_setter(PARENT, "company", "in_standard_filter", "0", "Check")

    if meta.get_field("contact_mobile"):
        upsert_property_setter(PARENT, "contact_mobile", "in_list_view", "1", "Check")
        upsert_property_setter(PARENT, "contact_mobile", "in_standard_filter", "1", "Check")

    _delete_custom_field(PARENT, "sent_to_shipkia")

    if meta.get_field("created_by_agent"):
        upsert_property_setter(PARENT, "created_by_agent", "hidden", "0", "Check")
        upsert_property_setter(PARENT, "created_by_agent", "in_list_view", "0", "Check")
        upsert_property_setter(PARENT, "created_by_agent", "in_standard_filter", "0", "Check")
        upsert_property_setter(PARENT, "created_by_agent", "print_hide", "1", "Check")

    upsert_property_setter(PARENT, "update_stock", "default", "1", "Check")
    upsert_property_setter(PARENT, "disable_rounded_total", "default", "1", "Check")
    upsert_property_setter(PARENT, "sr_kit_name", "read_only", "1", "Check")
    upsert_property_setter(PARENT, "sr_kit_total_price", "read_only", "1", "Check")
    upsert_property_setter(PARENT, "sr_non_kit_total_price", "read_only", "1", "Check")
    upsert_title_field(PARENT, "patient_name")


def _delete_custom_field(doctype: str, fieldname: str):
    name = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": fieldname}, "name")
    if not name:
        return
    frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)
    frappe.clear_cache(doctype=doctype)
    frappe.db.commit()




