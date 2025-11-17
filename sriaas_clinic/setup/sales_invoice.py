# sriaas_clinic/setup/sales_invoice.py
import frappe
from .utils import create_cf_with_module, upsert_property_setter, upsert_title_field

PARENT = "Sales Invoice"
CHILD = "Sales Invoice Item"

RIGHT_COL_CB = "column_break1"

def apply():
    _make_invoice_fields()
    _setup_payment_history_section()
    _setup_advance_payment_tab()
    if frappe.db.exists("DocType", PARENT) and frappe.db.exists("DocType", CHILD):
        _setup_cost_section()
        _setup_invoice_item_fields()
    _apply_invoice_ui_customizations()

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
    meta = frappe.get_meta(PARENT)
    insert_anchor = RIGHT_COL_CB if meta.get_field(RIGHT_COL_CB) else "posting_date"  # safe fallback
    
    create_cf_with_module({
        PARENT: [
            {"fieldname": "sr_si_patient_id","label": "Patient ID","fieldtype": "Data","read_only": 1,"insert_after": "customer_name","fetch_from": "patient.sr_patient_id"},
            {"fieldname": "sr_si_patient_department","label": "Department","fieldtype": "Link","options": "Medical Department","in_list_view":1,"in_standard_filter":1,"read_only": 1,"insert_after": "sr_si_patient_id","fetch_from": "patient.sr_medical_department"},

            {"fieldname": "sr_si_order_source","label": "Order Source","fieldtype": "Link","options": lead_source_dt,"in_list_view":1,"in_standard_filter":1,"insert_after": insert_anchor},
            {"fieldname": "sr_si_sales_type","label": "Sales Type","fieldtype": "Link","options": "SR Sales Type","in_list_view":1,"in_standard_filter":1,"insert_after": "sr_si_order_source",},
            {"fieldname": "sr_si_delivery_type","label": "Delivery Type","fieldtype": "Link","options": "SR Delivery Type","in_list_view":1,"in_standard_filter":1,"allow_on_submit":1,"insert_after": "sr_si_sales_type"},

            {
                "fieldname": "created_by_agent",
                "label": "Created By",
                "fieldtype": "Link",
                "options": "User",
                "read_only": 1,
                # do NOT set default here — we populate per-doc in before_insert
                "insert_after": "due_date"
            },
        ]
    })

def _setup_payment_history_section():
    """
    Add 'Payment History' section after 'advances' with read-only summary fields.
    """
    create_cf_with_module({
        PARENT: [
            {"fieldname": "sr_si_payment_history_sb","label": "Payment History","fieldtype": "Section Break","insert_after": "advances"},
            {"fieldname": "sr_si_payment_term","label": "Payment Term","fieldtype": "Select","options": "\nUnpaid\nPartially Paid\nPaid in Full","in_list_view":1,"in_standard_filter":1,"read_only": 1,"insert_after": "sr_si_payment_history_sb"},
            {"fieldname": "sr_si_paid_amount","label": "Paid Amount","fieldtype": "Currency","read_only": 1,"insert_after": "sr_si_payment_term"},
            {"fieldname": "sr_si_payment_history_cb","fieldtype": "Column Break","insert_after": "sr_si_paid_amount"},
            {"fieldname": "sr_si_mode_of_payment","label": "Mode of Payment","fieldtype": "Link","options": "Mode of Payment","read_only": 1,"insert_after": "sr_si_payment_history_cb"},
            {"fieldname": "sr_si_outstanding_amount","label": "Outstanding Amount","fieldtype": "Currency","read_only": 1,"insert_after": "sr_si_mode_of_payment"},
        ]
    })

def _setup_advance_payment_tab():
    """
    Add 'Draft Payment' tab on Sales Invoice to capture an intended advance.
    - Tab is always visible (so user can enter the amount).
    - Inner fields become visible/required when amount > 0.
    """
    create_cf_with_module({
        PARENT: [
            # The tab itself (always visible – lets user enter amount)
            {"fieldname": "si_draft_payment_tab", "label": "Payment Entry", "fieldtype": "Tab Break",
             "insert_after": "connections_tab"},

            # Section + fields
            {"fieldname": "si_dp_section", "label": "Advance Details", "fieldtype": "Section Break",
             "insert_after": "si_draft_payment_tab"},

            {"fieldname": "si_dp_paid_amount", "label": "Paid Amount", "fieldtype": "Currency",
             "insert_after": "si_dp_section"},

            {"fieldname": "si_dp_cb", "fieldtype": "Column Break", "insert_after": "si_dp_paid_amount"},

            {"fieldname": "si_dp_mode_of_payment", "label": "Mode of Payment", "fieldtype": "Link", "options": "Mode of Payment",
             "insert_after": "si_dp_cb"},

            {"fieldname": "si_dp_receipt_section", "label": "Receipt / Proof", "fieldtype": "Section Break",
             "insert_after": "si_dp_mode_of_payment"},

            {"fieldname": "si_dp_reference_no", "label": "Reference No", "fieldtype": "Data",
             "insert_after": "si_dp_receipt_section"},

            {"fieldname": "si_dp_cb2", "fieldtype": "Column Break", "insert_after": "si_dp_reference_no"},

            {"fieldname": "si_dp_reference_date", "label": "Reference Date", "fieldtype": "Date",
             "insert_after": "si_dp_cb2"},

            {"fieldname": "si_dp_payment_proof", "label": "Payment Proof", "fieldtype": "Attach Image",
             "insert_after": "si_dp_reference_date"},
        ]
    })

    # Show / Require inner fields ONLY if amount > 0
    for f in ["si_dp_mode_of_payment", "si_dp_receipt_section", "si_dp_reference_no",
              "si_dp_reference_date", "si_dp_payment_proof", "si_dp_cb", "si_dp_cb2"]:
        upsert_property_setter(PARENT, f, "depends_on", "eval:doc.si_dp_paid_amount>0", "Data")

    for f in ["si_dp_mode_of_payment", "si_dp_reference_date"]:
        upsert_property_setter(PARENT, f, "mandatory_depends_on", "eval:doc.si_dp_paid_amount>0", "Data")

    # Keep hard reqd OFF so autosaves don’t fail
    for f in ["si_dp_mode_of_payment", "si_dp_reference_date"]:
        upsert_property_setter(PARENT, f, "reqd", "0", "Check")

def _setup_cost_section():
    create_cf_with_module({
        PARENT: [
            {
                "fieldname": "sr_cost_section",
                "label": "Cost (Admin)",
                "fieldtype": "Section Break",
                "insert_after": "disable_rounded_total",
            },
            {
                "fieldname": "sr_total_cost",
                "label": "Total Cost",
                "fieldtype": "Currency",
                "read_only": 1,
                "insert_after": "sr_cost_section",
            },
            {
                "fieldname": "sr_cost_pct_overall",
                "label": "Cost % Overall",
                "fieldtype": "Percent",
                "read_only": 1,
                "insert_after": "sr_total_cost",
                "description": "Total Cost / Grand Total * 100",
            },
            {
                "fieldname": "sr_cost_col_break",
                "fieldtype": "Column Break",
                "insert_after": "sr_cost_pct_overall",
            },
            {
                "fieldname": "sr_margin_overall",
                "label": "Margin %",
                "fieldtype": "Percent",
                "read_only": 1,
                "insert_after": "sr_cost_col_break",
                "description": "(Grand Total - Total Cost) / Grand Total * 100",
            },
        ]
    })

def _setup_invoice_item_fields():
    create_cf_with_module({
        CHILD: [
            {
                "fieldname": "sr_cost_price",
                "label": "Cost Price",
                "fieldtype": "Currency",
                "read_only": 1,
                "insert_after": "rate",
            },
            {
                "fieldname": "sr_cost_amount",
                "label": "Cost Amount",
                "fieldtype": "Currency",
                "read_only": 1,
                "insert_after": "sr_cost_price",
                "description": "qty * sr_cost_price",
            },
            {
                "fieldname": "sr_cost_pct",
                "label": "Cost %",
                "fieldtype": "Percent",
                "read_only": 1,
                "insert_after": "sr_cost_amount",
                "description": "Cost Price / Rate * 100",
            },
        ]
    })

def _apply_invoice_ui_customizations():
    """Apply various UI customizations to Sales Invoice"""

    # Hide unwanted flags/fields
    targets = (
        "customer",
        "ref_practitioner",
        "customer_name",
        "service_unit",
        "ewaybill",
        "e_waybill_status",
        "allocate_advances_automatically",
        "get_advances",
        "advances",
        "redeem_loyalty_points"
    )

    meta = frappe.get_meta(PARENT)
    for f in targets:
        if not meta.get_field(f):
            continue  # skip if field doesn't exist on this site
        upsert_property_setter(PARENT, f, "hidden", "1", "Check")
        upsert_property_setter(PARENT, f, "print_hide", "1", "Check")
        upsert_property_setter(PARENT, f, "in_list_view", "0", "Check")
        upsert_property_setter(PARENT, f, "in_standard_filter", "0", "Check")

    # Tweak list/standard filter visibility
    if meta.get_field("company"):
        upsert_property_setter(PARENT, "company", "in_standard_filter", "0", "Check")  # hide from filters
    if meta.get_field("contact_mobile"):
        upsert_property_setter(PARENT, "contact_mobile", "in_list_view", "1", "Check")  # show in list
        upsert_property_setter(PARENT, "contact_mobile", "in_standard_filter", "1", "Check")  # show in filters

    # ensure created_by_agent is hidden and not shown in list/filter
    if meta.get_field("created_by_agent"):
        upsert_property_setter(PARENT, "created_by_agent", "hidden", "0", "Check")
        upsert_property_setter(PARENT, "created_by_agent", "in_list_view", "0", "Check")
        upsert_property_setter(PARENT, "created_by_agent", "in_standard_filter", "0", "Check")
        upsert_property_setter(PARENT, "created_by_agent", "print_hide", "1", "Check")

    # Set title field to patient_name
    upsert_title_field(PARENT, "patient_name")
