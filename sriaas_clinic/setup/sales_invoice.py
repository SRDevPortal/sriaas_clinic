# sriaas_clinic/setup/sales_invoice.py
import frappe
from .utils import create_cf_with_module, upsert_property_setter

DT = "Sales Invoice"
RIGHT_COL_CB = "column_break1"

def apply():
    _make_invoice_fields()
    _setup_payment_history_section()
    _setup_order_tracking_tab()
    _hide_invoice_fields()

def _lead_source_dt() -> str:
    if frappe.db.exists("DocType", "SR Lead Source"):
        return "SR Lead Source"
    if frappe.db.exists("DocType", "CRM Lead Source"):
        return "CRM Lead Source"
    return "Lead Source"

def _make_invoice_fields():
    """
    Put these three at the very top of the right column (after column_break1):
      - Order Source (Link to SR/CRM/Lead Source)
      - Sales Type (Link SR Sales Type)
      - Delivery Type (Link SR Delivery Type, allow_on_submit)
    """
    # Determine which Lead Source doctype to link to
    lead_source_dt = _lead_source_dt()

    # Determine where to insert new fields (after right column CB if present)
    meta = frappe.get_meta(DT)
    insert_anchor = RIGHT_COL_CB if meta.get_field(RIGHT_COL_CB) else "posting_date"  # safe fallback
    
    create_cf_with_module({
        DT: [
            # Patient snapshots (read-only, fetched from the linked Patient on SI)
            {"fieldname": "sr_si_patient_id","label": "Patient ID","fieldtype": "Data","read_only": 1,"insert_after": "customer_name","fetch_from": "patient.sr_patient_id"},
            {"fieldname": "sr_si_patient_department","label": "Department","fieldtype": "Link","options": "Medical Department","in_list_view":1,"in_standard_filter":1,"read_only": 1,"insert_after": "sr_si_patient_id","fetch_from": "patient.sr_medical_department"},

            # Order meta
            {"fieldname": "sr_si_order_source","label": "Order Source","fieldtype": "Link","options": lead_source_dt,"in_list_view":1,"in_standard_filter":1,"insert_after": insert_anchor},
            {"fieldname": "sr_si_sales_type","label": "Sales Type","fieldtype": "Link","options": "SR Sales Type","in_list_view":1,"in_standard_filter":1,"insert_after": "sr_si_order_source",},
            {"fieldname": "sr_si_delivery_type","label": "Delivery Type","fieldtype": "Link","options": "SR Delivery Type","in_list_view":1,"in_standard_filter":1,"allow_on_submit":1,"insert_after": "sr_si_sales_type"},
        ]
    })

def _setup_payment_history_section():
    """
    Add 'Payment History' section after 'advances' with read-only summary fields.
    """
    create_cf_with_module({
        DT: [
            {"fieldname": "sr_si_payment_history_sb","label": "Payment History","fieldtype": "Section Break","insert_after": "advances"},

            # First colmn
            {"fieldname": "sr_si_payment_term","label": "Payment Term","fieldtype": "Select","options": "\nUnpaid\nPartially Paid\nPaid in Full","in_list_view":1,"in_standard_filter":1,"read_only": 1,"insert_after": "sr_si_payment_history_sb"},
            {"fieldname": "sr_si_paid_amount","label": "Paid Amount","fieldtype": "Currency","read_only": 1,"insert_after": "sr_si_payment_term"},

            # Roght column
            {"fieldname": "sr_si_payment_history_cb","fieldtype": "Column Break","insert_after": "sr_si_paid_amount"},

            {"fieldname": "sr_si_mode_of_payment","label": "Mode of Payment","fieldtype": "Link","options": "Mode of Payment","read_only": 1,"insert_after": "sr_si_payment_history_cb"},
            {"fieldname": "sr_si_outstanding_amount","label": "Outstanding Amount","fieldtype": "Currency","read_only": 1,"insert_after": "sr_si_mode_of_payment"},
        ]
    })

def _setup_order_tracking_tab():
    """
    Adds a new tab 'Order Tracking' with two columns:
      Left column:  sr_si_shipping_status (Data, RO), sr_si_delivery_date (Datetime, RO)
      Right column: sr_si_courier_partner (Data, RO), sr_si_awb_no (Data, RO)
    """

    create_cf_with_module({
        DT: [
            {"fieldname": "sr_si_order_tracking_tab","label": "Order Tracking","fieldtype": "Tab Break","insert_after": "connections_tab"},

            {"fieldname": "sr_si_order_tracking_sb","label": "Tracking Details","fieldtype": "Section Break","insert_after": "sr_si_order_tracking_tab"},

            # Left column
            {"fieldname": "sr_si_shipping_status","label": "Shipping Status","fieldtype": "Data","read_only": 1,"insert_after": "sr_si_order_tracking_sb"},
            {"fieldname": "sr_si_delivery_date","label": "Delivery Date","fieldtype": "Datetime","read_only": 1,"insert_after": "sr_si_shipping_status"},

            # Right column
            {"fieldname": "sr_si_order_tracking_cb","fieldtype": "Column Break","insert_after": "sr_si_delivery_date"},

            {"fieldname": "sr_si_courier_partner","label": "Courier Partner","fieldtype": "Data","read_only": 1,"insert_after": "sr_si_order_tracking_cb"},
            {"fieldname": "sr_si_awb_no","label": "AWB No","fieldtype": "Data","read_only": 1,"insert_after": "sr_si_courier_partner"},
        ]
    })

def _hide_invoice_fields():
    # Standard fields you want invisible everywhere + not filterable
    targets = ("customer", "customer_name", "ref_practitioner", "service_unit", "allocate_advances_automatically", "get_advances", "advances", "redeem_loyalty_points")

    meta = frappe.get_meta(DT)
    for f in targets:
        if not meta.get_field(f):
            continue  # skip if field doesn't exist on this site
        upsert_property_setter(DT, f, "hidden", "1", "Check")
        upsert_property_setter(DT, f, "print_hide", "1", "Check")
        upsert_property_setter(DT, f, "in_list_view", "0", "Check")
        upsert_property_setter(DT, f, "in_standard_filter", "0", "Check")

    # Tweak list/standard filter visibility
    if meta.get_field("company"):
        upsert_property_setter(DT, "company", "in_standard_filter", "0", "Check")  # hide from filters
    if meta.get_field("contact_mobile"):
        upsert_property_setter(DT, "contact_mobile", "in_list_view", "1", "Check")  # show in list
        upsert_property_setter(DT, "contact_mobile", "in_standard_filter", "1", "Check")  # show in filters