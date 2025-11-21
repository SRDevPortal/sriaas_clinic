# sriaas_clinic/api/encounter_flow/handlers.py

"""
Event handlers for Patient Encounter doctype:
- set_created_by_agent
- Encounter -> create Draft Sales Invoice + Draft Payment Entry(s)
- helpers for tax, warehouse, customer resolution, etc.
"""

from typing import Optional, List, Dict, Any
import frappe
from frappe.utils import flt, nowdate
from erpnext.accounts.party import get_party_account

# ----------------------------------
# small helper: set_created_by_agent
# ----------------------------------
def set_created_by_agent(doc, method):
    """Populate created_by_agent on insert only (so edits don't override)."""
    if not getattr(doc, "created_by_agent", None):
        doc.created_by_agent = frappe.session.user

# ---------------- CONFIG (matches your schema) ----------------

# Encounter
F_ENCOUNTER_TYPE = "sr_encounter_type" # "Followup" / "Order"
F_ENCOUNTER_PLACE = "sr_encounter_place" # "Online" / "OPD"
F_SALES_TYPE = "sr_sales_type" # Link SR Sales Type
F_SOURCE = "sr_encounter_source" # Link Lead Source
F_DELIVERY_TYPE = "sr_delivery_type" # Link SR Delivery Type (in Draft Invoice tab)
# F_MOP = "sr_pe_mode_of_payment" # Link Mode of Payment
# F_PAID_AMT = "sr_pe_paid_amount" # Currency
# F_REF_NO = "sr_pe_payment_reference_no" # Data
# F_REF_DATE = "sr_pe_payment_reference_date" # Date
ORDER_ITEMS_TABLE = "sr_pe_order_items" # Table → SR Order Item

# Sales Invoice (your custom fields)
SI_F_ORDER_SOURCE = "sr_si_order_source"
SI_F_ENCOUNTER_PLACE = "sr_si_encounter_place"
SI_F_SALES_TYPE = "sr_si_sales_type"
SI_F_DELIVERY_TYPE = "sr_si_delivery_type"

SI_F_PAYMENT_TERM = "sr_si_payment_term" # Select: Unpaid/Partially Paid/Paid in Full
SI_F_PAID_AMOUNT = "sr_si_paid_amount"
SI_F_MOP = "sr_si_mode_of_payment"
SI_F_OUTSTANDING = "sr_si_outstanding_amount"

# Optional back-link on SI (create if you like)
SI_F_SOURCE_ENCOUNTER = "source_encounter" # Link → Patient Encounter (optional)


# Tax templates (adjust names if yours differ)
TAX_TEMPLATE_INTRASTATE = "Output GST In-state"
TAX_TEMPLATE_INTERSTATE = "Output GST Out-state"

# If True also writes to SI POS payments (GL on submit) — keep False if you use PEs
USE_POS_PAYMENTS_ROW = False


# Optional fallback warehouse for stock items (must belong to same company)
DEFAULT_FALLBACK_WAREHOUSE: Optional[str] = None # e.g., "Main - SR"

ROW_KEYS = {
    "item_code": ["sr_item_code", "item_code"],
    "item_name": ["sr_item_name", "item_name"],
    "uom": ["sr_item_uom", "uom"],
    "qty": ["sr_item_qty", "qty"],
    "rate": ["sr_item_rate", "rate"],
}

def _row_get(row: Dict[str, Any], key: str, default=None):
    for k in ROW_KEYS.get(key, []):
        val = row.get(k)
        if val not in (None, ""):
            return val
    return default


# ----------------------- Event handlers -----------------------
def before_save_patient_encounter(doc, method):
    """Clean invalid warehouses in Encounter order items; compute amount fallback."""
    rows = _find_item_rows(doc)
    company = doc.company
    for it in rows:
        item_code = _row_get(it, "item_code")
        if not item_code:
            continue

        qty = flt(_row_get(it, "qty") or 0)
        rate = flt(_row_get(it, "rate") or 0)
        it.amount = qty * rate  # harmless if child doesn’t have 'amount'

        wh = _row_get(it, "warehouse")
        if not _is_stock_item(item_code):
            if wh:
                it["warehouse"] = None
        else:
            if wh and not _valid_warehouse(wh, company):
                it["warehouse"] = None


def clear_advance_dependent_fields(doc, method):
    """
    Clear enc_multi_payments unless Encounter is Order + (Online or OPD).

    Note: If you want to treat an empty place as allowed (to match the JS's
    `|| !place` behaviour), change the `place_allowed` logic to include `not place`.
    """
    etype = (str(doc.get(F_ENCOUNTER_TYPE) or "")).strip().lower()
    place = (str(doc.get(F_ENCOUNTER_PLACE) or "")).strip().lower()

    # Option A: strict — require Order AND place in ("online","opd")
    place_allowed = place in ("online", "opd")

    # Option B (if you want to match JS which shows when place is empty too):
    # place_allowed = (place in ("online", "opd")) or (place == "")

    is_order_for_any_place = (etype == "order" and place_allowed)

    if not is_order_for_any_place:
        # clear child table so payments don't persist accidentally
        if getattr(doc, "enc_multi_payments", None):
            doc.enc_multi_payments = []


def _has_any_attachment(doc) -> bool:
    """True if the doc has any File attached via the sidebar."""
    return bool(frappe.get_all(
        "File",
        filters={"attached_to_doctype": doc.doctype, "attached_to_name": doc.name},
        limit=1
    ))


def validate_required_before_submit(doc, method):
    """
    Validate multi-mode payments when submitting the Encounter.

    Rules:
      - Only validates for Orders. Change to check place if you want to restrict to Online/OPD.
      - For each enc_multi_payments row with positive mmp_paid_amount:
          * mmp_mode_of_payment required
          * mmp_reference_date required
          * proof required: either mmp_payment_proof OR any sidebar attachment on the Encounter
    """
    try:
        # Only validate for Orders — switch to `_is_order_online(doc)` if you want Online/OPD only
        if str(doc.get(F_ENCOUNTER_TYPE) or "").strip().lower() != "order":
            return

        multi = getattr(doc, "enc_multi_payments", []) or []

        # Collect rows that have positive amount (only these must be validated)
        rows_to_check = []
        for idx, r in enumerate(multi, start=1):
            # r may be dict-like (from UI) or object-like (frappe doc)
            try:
                amt = flt(r.get("mmp_paid_amount") if isinstance(r, dict) else getattr(r, "mmp_paid_amount", 0) or 0)
            except Exception:
                amt = flt((getattr(r, "mmp_paid_amount", 0) if not isinstance(r, dict) else r.get("mmp_paid_amount", 0)) or 0)
            if amt > 0:
                rows_to_check.append((idx, r))

        if not rows_to_check:
            return

        missing_msgs = []
        for idx, r in rows_to_check:
            if isinstance(r, dict):
                mop = (r.get("mmp_mode_of_payment") or "").strip()
                ref_date = r.get("mmp_reference_date")
                proof = r.get("mmp_payment_proof")
                ref_no = r.get("mmp_reference_no")
            else:
                mop = (getattr(r, "mmp_mode_of_payment", None) or "").strip()
                ref_date = getattr(r, "mmp_reference_date", None)
                proof = getattr(r, "mmp_payment_proof", None)
                ref_no = getattr(r, "mmp_reference_no", None)

            row_missing = []

            # --- NEW LOGIC ---
            # If mode is Cash → no reference fields or proof required
            if mop.lower() == "cash":
                pass  # nothing required

            else:
                # Mode ≠ Cash → all reference fields required
                if not ref_no:
                    row_missing.append("Reference No")
                if not ref_date:
                    row_missing.append("Reference Date")

                # Proof required: either row-level OR sidebar attachment
                has_proof = bool(proof) or _has_any_attachment(doc)
                if not has_proof:
                    row_missing.append("Payment Proof")

            if row_missing:
                missing_msgs.append(f"Row {idx}: " + ", ".join(row_missing))

        if missing_msgs:
            frappe.throw("Please complete payment rows before submit: " + " ; ".join(missing_msgs))

    except Exception:
        frappe.log_error(frappe.get_traceback(), "validate_required_before_submit_error")
        # Re-raise to block submit if validation code itself fails.
        raise


def _is_order_online(doc) -> bool:
    # Treat Encounter as billable when type == "Order" AND place is either "online" or "opd"
    return (
        str(doc.get(F_ENCOUNTER_TYPE) or "").strip().lower() == "order"
        and str(doc.get(F_ENCOUNTER_PLACE) or "").strip().lower() in ("online", "opd")
    )


def create_billing_on_submit(doc, method):
    """Run on Patient Encounter submit and create DRAFT SI (+ DRAFT PE if advance)."""
    if doc.docstatus != 1:
        return
    if not _is_order_online(doc):
        return
    _create_billing_drafts_from_encounter(doc)


# def _create_billing_drafts_from_encounter(doc):
#     """The old create_billing_on_save body, but callable from on_submit."""
#     # import frappe
#     # from frappe.utils import flt, nowdate

#     # Don’t duplicate
#     if getattr(doc, "sales_invoice", None):
#         return
#     existing = frappe.get_all(
#         "Sales Invoice",
#         filters={"docstatus": 0, "remarks": ["like", f"%Patient Encounter: {doc.name}%"]},
#         pluck="name",
#         limit=1,
#     )
#     if existing:
#         return

#     # Build SI (DRAFT)
#     customer = _get_or_create_customer_from_patient(doc)
#     item_rows = _find_item_rows(doc)
#     if not item_rows:
#         return  # no items → skip

#     si = frappe.new_doc("Sales Invoice")
#     si.update({
#         "customer": customer,
#         "company": doc.company,
#         "posting_date": nowdate(),
#         "due_date": nowdate(),
#         "remarks": f"Created from Patient Encounter: {doc.name}",
#     })

#     si_meta = frappe.get_meta("Sales Invoice")
#     if si_meta.has_field("patient") and doc.get("patient"):
#         si.patient = doc.patient
#         if si_meta.has_field("patient_name"):
#             si.patient_name = frappe.db.get_value("Patient", doc.patient, "patient_name")

#     if si_meta.has_field(SI_F_SOURCE_ENCOUNTER):
#         setattr(si, SI_F_SOURCE_ENCOUNTER, doc.name)

#     addr = _get_company_primary_address(doc.company)
#     if addr:
#         si.company_address = addr

#     if hasattr(si, "set_warehouse"):
#         si.set_warehouse = None

#     added = 0
#     for it in item_rows:
#         item_code = _row_get(it, "item_code")
#         if not item_code:
#             continue

#         qty = flt(_row_get(it, "qty") or 1)
#         rate = flt(_row_get(it, "rate") or 0)
#         uom = _row_get(it, "uom")
#         name = _row_get(it, "item_name")
#         req_wh = _row_get(it, "warehouse")

#         safe_wh = _coalesce_warehouse(
#             requested_wh=req_wh,
#             company=doc.company,
#             item_code=item_code,
#         )

#         row = {
#             "item_code": item_code,
#             "item_name": name,
#             "description": it.get("description"),
#             "uom": uom,
#             "qty": qty,
#             "rate": rate,
#             "conversion_factor": it.get("conversion_factor") or 1,
#             "income_account": it.get("income_account"),
#             "cost_center": it.get("cost_center"),
#         }
#         if safe_wh:
#             row["warehouse"] = safe_wh

#         si.append("items", row)
#         added += 1

#     if added == 0:
#         frappe.throw("No valid items found in Draft Invoice → Items List. Please enter Item Code, Qty and Rate.")

#     # Map Encounter → SI custom fields
#     if si_meta.has_field(SI_F_ORDER_SOURCE) and doc.get(F_SOURCE):
#         setattr(si, SI_F_ORDER_SOURCE, doc.get(F_SOURCE))
#     if si_meta.has_field(SI_F_SALES_TYPE) and doc.get(F_SALES_TYPE):
#         setattr(si, SI_F_SALES_TYPE, doc.get(F_SALES_TYPE))
#     if si_meta.has_field(SI_F_DELIVERY_TYPE) and doc.get(F_DELIVERY_TYPE):
#         setattr(si, SI_F_DELIVERY_TYPE, doc.get(F_DELIVERY_TYPE))

#     # Taxes & totals
#     _set_tax_template_by_state(si, customer)
#     _apply_company_tax_template(si)
#     si.set_missing_values()
#     si.calculate_taxes_and_totals()
#     _company_safe_tax_rows(si)
#     si.calculate_taxes_and_totals()
#     _sanitize_si_warehouses(si, doc.company)

#     # UI summary (non-GL)
#     pre_amt = flt(doc.get(F_PAID_AMT) or 0)
#     mop = (doc.get(F_MOP) or "").strip()
#     total = flt(si.rounded_total or si.grand_total or 0)

#     if si_meta.has_field(SI_F_PAID_AMOUNT):
#         setattr(si, SI_F_PAID_AMOUNT, pre_amt)
#     if si_meta.has_field(SI_F_MOP):
#         setattr(si, SI_F_MOP, mop)
#     if si_meta.has_field(SI_F_PAYMENT_TERM):
#         if pre_amt <= 0:
#             setattr(si, SI_F_PAYMENT_TERM, "Unpaid")
#         elif total > 0 and pre_amt + 1e-6 < total:
#             setattr(si, SI_F_PAYMENT_TERM, "Partially Paid")
#         else:
#             setattr(si, SI_F_PAYMENT_TERM, "Paid in Full")
#     if si_meta.has_field(SI_F_OUTSTANDING):
#         setattr(si, SI_F_OUTSTANDING, max(total - pre_amt, 0))

#     # Final guard on warehouses
#     for r in si.items:
#         if r.warehouse and not _valid_warehouse(r.warehouse, doc.company):
#             r.warehouse = None

#     si.flags.ignore_permissions = True
#     si.insert(ignore_permissions=True)  # KEEP DRAFT

#     # Optional: Draft PE (no references yet) if advance present
#     # pe_name = None
#     # if pre_amt > 0 and mop:
#     #     pe_name = _create_draft_payment_entry(doc, customer, mop, pre_amt, si.name)

#     # Optional: create Draft Payment Entries from enc_multi_payments (one PE per row)
#     pe_names = []
#     # enc_multi_payments is the table field you added; adjust if your fieldname differs
#     multi_rows = getattr(doc, "enc_multi_payments", []) or []

#     # patient display name for nicer party_name on Payment Entry
#     patient_name = None
#     try:
#         patient_name = frappe.db.get_value("Patient", doc.get("patient"), "patient_name") or getattr(doc, "patient_name", None) or getattr(doc, "patient", None)
#     except Exception:
#         patient_name = getattr(doc, "patient_name", None) or getattr(doc, "patient", None)

#     # If the encounter has the legacy single-advance fields still set (pre_amt/mop),
#     # we can also create a PE for that single amount (optional). Here we prioritize multi rows.
#     # Create a PE per multi payment row where amount > 0
#     for m in multi_rows:
#         try:
#             m_amt = flt(getattr(m, "mmp_paid_amount", 0) or 0)
#             if m_amt <= 0:
#                 continue
#             m_mop = getattr(m, "mmp_mode_of_payment", None) or (doc.get(F_MOP) or None)
            
#             # create draft PE for this row
#             pe_name = _create_draft_payment_entry(doc, customer, m_mop, m_amt, si.name)

#             if not pe_name:
#                 continue

#             # ensure readable party_name on the PE
#             try:
#                 if patient_name:
#                     frappe.db.set_value("Payment Entry", pe_name, "party_name", patient_name, update_modified=False)
#             except Exception:
#                 # non-fatal
#                 pass

#             pe_names.append(pe_name)

#             # record created PE back on the child row (SR Multi Mode Payment)
#             try:
#                 frappe.db.set_value("SR Multi Mode Payment", m.name, {
#                     "mmp_payment_entry": pe_name,
#                     "mmp_posting_date": frappe.db.get_value("Payment Entry", pe_name, "posting_date")
#                 }, update_modified=False)
#             except Exception:
#                 frappe.log_error(frappe.get_traceback(),
#                                  f"Failed linking PE {pe_name} back to encounter child row {m.name}")
#         except Exception:
#             frappe.log_error(frappe.get_traceback(), "Failed creating PE from encounter multi payment row")

#     # commit DB changes if any PEs created
#     if pe_names:
#         frappe.db.commit()

#     # Back-links on Encounter, if fields exist
#     if hasattr(doc, "sales_invoice"):
#         doc.db_set("sales_invoice", si.name, update_modified=False)

#     # set encounter.payment_entry to first created PE (if you still use that field)
#     if pe_names and hasattr(doc, "payment_entry"):
#         doc.db_set("payment_entry", pe_names[0], update_modified=False)

#     # show message
#     if pe_names:
#         frappe.msgprint(
#             f"Created Draft Sales Invoice <b>{si.name}</b> and Draft Payment Entry(s) <b>{', '.join(pe_names)}</b>",
#             alert=True
#         )
#     else:
#         frappe.msgprint(f"Created Draft Sales Invoice <b>{si.name}</b>", alert=True)


def _create_billing_drafts_from_encounter(doc):
    """The old create_billing_on_save body, but callable from on_submit."""

    # Don’t duplicate
    if getattr(doc, "sales_invoice", None):
        return
    existing = frappe.get_all(
        "Sales Invoice",
        filters={"docstatus": 0, "remarks": ["like", f"%Patient Encounter: {doc.name}%"]},
        pluck="name",
        limit=1,
    )
    if existing:
        return

    # Build SI (DRAFT)
    customer = _get_or_create_customer_from_patient(doc)
    item_rows = _find_item_rows(doc)
    if not item_rows:
        return  # no items → skip

    si = frappe.new_doc("Sales Invoice")
    si.update({
        "customer": customer,
        "company": doc.company,
        "posting_date": nowdate(),
        "due_date": nowdate(),
        "remarks": f"Created from Patient Encounter: {doc.name}",
    })

    si_meta = frappe.get_meta("Sales Invoice")
    if si_meta.has_field("patient") and doc.get("patient"):
        si.patient = doc.patient
        if si_meta.has_field("patient_name"):
            si.patient_name = frappe.db.get_value("Patient", doc.patient, "patient_name")

    if si_meta.has_field(SI_F_SOURCE_ENCOUNTER):
        setattr(si, SI_F_SOURCE_ENCOUNTER, doc.name)

    addr = _get_company_primary_address(doc.company)
    if addr:
        si.company_address = addr

    if hasattr(si, "set_warehouse"):
        si.set_warehouse = None

    added = 0
    for it in item_rows:
        item_code = _row_get(it, "item_code")
        if not item_code:
            continue

        qty = flt(_row_get(it, "qty") or 1)
        rate = flt(_row_get(it, "rate") or 0)
        uom = _row_get(it, "uom")
        name = _row_get(it, "item_name")
        req_wh = _row_get(it, "warehouse")

        safe_wh = _coalesce_warehouse(
            requested_wh=req_wh,
            company=doc.company,
            item_code=item_code,
        )

        row = {
            "item_code": item_code,
            "item_name": name,
            "description": it.get("description"),
            "uom": uom,
            "qty": qty,
            "rate": rate,
            "conversion_factor": it.get("conversion_factor") or 1,
            "income_account": it.get("income_account"),
            "cost_center": it.get("cost_center"),
        }
        if safe_wh:
            row["warehouse"] = safe_wh

        si.append("items", row)
        added += 1

    if added == 0:
        frappe.throw("No valid items found in Draft Invoice → Items List. Please enter Item Code, Qty and Rate.")

    # Map Encounter → SI custom fields
    if si_meta.has_field(SI_F_ORDER_SOURCE) and doc.get(F_SOURCE):
        setattr(si, SI_F_ORDER_SOURCE, doc.get(F_SOURCE))
    if si_meta.has_field(SI_F_ENCOUNTER_PLACE) and doc.get(F_ENCOUNTER_PLACE):
        setattr(si, SI_F_ENCOUNTER_PLACE, doc.get(F_ENCOUNTER_PLACE))
    if si_meta.has_field(SI_F_SALES_TYPE) and doc.get(F_SALES_TYPE):
        setattr(si, SI_F_SALES_TYPE, doc.get(F_SALES_TYPE))
    if si_meta.has_field(SI_F_DELIVERY_TYPE) and doc.get(F_DELIVERY_TYPE):
        setattr(si, SI_F_DELIVERY_TYPE, doc.get(F_DELIVERY_TYPE))

    # Taxes & totals
    _set_tax_template_by_state(si, customer)
    _apply_company_tax_template(si)
    si.set_missing_values()
    si.calculate_taxes_and_totals()
    _company_safe_tax_rows(si)
    si.calculate_taxes_and_totals()
    _sanitize_si_warehouses(si, doc.company)

    # --- NEW: compute advance summary from enc_multi_payments child table ---
    multi_rows = getattr(doc, "enc_multi_payments", []) or []
    total_advance = 0.0
    mop_list = []
    for m in multi_rows:
        try:
            amt = flt(getattr(m, "mmp_paid_amount", 0) or 0)
        except Exception:
            amt = flt((m.get("mmp_paid_amount") if isinstance(m, dict) else getattr(m, "mmp_paid_amount", 0)) or 0)
        if amt > 0:
            total_advance += amt
            # collect mode of payment strings (skip empty)
            mop_val = (getattr(m, "mmp_mode_of_payment", None) if not isinstance(m, dict) else m.get("mmp_mode_of_payment")) or None
            if mop_val:
                mop_list.append(str(mop_val).strip())

    # Set SI UI summary fields from the multi-payments (if fields exist)
    # if si_meta.has_field(SI_F_PAID_AMOUNT):
    #     setattr(si, SI_F_PAID_AMOUNT, total_advance)
    # if si_meta.has_field(SI_F_MOP):
    #     # store comma-joined MOPs (or None)
    #     setattr(si, SI_F_MOP, ", ".join(dict.fromkeys([m for m in mop_list if m])) or None)

    # Payment term determination using total_advance
    # pre_amt = total_advance
    # mop = None  # no single mop at encounter level anymore
    # total = flt(si.rounded_total or si.grand_total or 0)

    # if si_meta.has_field(SI_F_PAYMENT_TERM):
    #     if pre_amt <= 0:
    #         setattr(si, SI_F_PAYMENT_TERM, "Unpaid")
    #     elif total > 0 and pre_amt + 1e-6 < total:
    #         setattr(si, SI_F_PAYMENT_TERM, "Partially Paid")
    #     else:
    #         setattr(si, SI_F_PAYMENT_TERM, "Paid in Full")
    # if si_meta.has_field(SI_F_OUTSTANDING):
    #     setattr(si, SI_F_OUTSTANDING, max(total - pre_amt, 0))

    # Final guard on warehouses
    for r in si.items:
        if r.warehouse and not _valid_warehouse(r.warehouse, doc.company):
            r.warehouse = None

    si.flags.ignore_permissions = True
    si.insert(ignore_permissions=True)  # KEEP DRAFT

    # --- CREATE DRAFT PAYMENT ENTRY PER enc_multi_payments ROW (one PE per row) ---
    pe_names = []
    patient_name = None
    try:
        patient_name = frappe.db.get_value("Patient", doc.get("patient"), "patient_name") or getattr(doc, "patient_name", None) or getattr(doc, "patient", None)
    except Exception:
        patient_name = getattr(doc, "patient_name", None) or getattr(doc, "patient", None)

    for m in multi_rows:
        try:
            m_amt = flt(getattr(m, "mmp_paid_amount", 0) or 0)
            if m_amt <= 0:
                continue
            # prefer row-level mop, fallback to None (no doc-level mop)
            m_mop = getattr(m, "mmp_mode_of_payment", None) or None

            # row-level reference fields (if present)
            m_ref_no = getattr(m, "mmp_reference_no", None) or (m.get("mmp_reference_no") if isinstance(m, dict) else None)
            m_ref_date = getattr(m, "mmp_reference_date", None) or (m.get("mmp_reference_date") if isinstance(m, dict) else None)

            # create draft PE for this row, pass row-level references
            pe_name = _create_draft_payment_entry(doc, customer, m_mop, m_amt, si.name, reference_no=m_ref_no, reference_date=m_ref_date)

            pe_name = _create_draft_payment_entry(
                doc,
                customer,
                m_mop,
                m_amt,
                si.name,
                reference_no=m_ref_no,
                reference_date=m_ref_date,
                order_source=doc.get(F_SOURCE),
                encounter_place=doc.get(F_ENCOUNTER_PLACE),
                sales_type=doc.get(F_SALES_TYPE),
                delivery_type=doc.get(F_DELIVERY_TYPE),
            )

            if not pe_name:
                continue

            # ensure readable party_name on the PE
            try:
                if patient_name:
                    frappe.db.set_value("Payment Entry", pe_name, "party_name", patient_name, update_modified=False)
            except Exception:
                # non-fatal
                pass

            pe_names.append(pe_name)

            # record created PE back on the child row (SR Multi Mode Payment)
            try:
                # m.name should be the child row name (frappe child doc)
                frappe.db.set_value("SR Multi Mode Payment", m.name, {
                    "mmp_payment_entry": pe_name,
                    "mmp_posting_date": frappe.db.get_value("Payment Entry", pe_name, "posting_date")
                }, update_modified=False)
            except Exception:
                frappe.log_error(frappe.get_traceback(),
                                 f"Failed linking PE {pe_name} back to encounter child row {getattr(m,'name', '<no-name>')}")
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Failed creating PE from encounter multi payment row")

    # commit DB changes if any PEs created
    if pe_names:
        frappe.db.commit()

    # Back-links on Encounter, if fields exist
    if hasattr(doc, "sales_invoice"):
        doc.db_set("sales_invoice", si.name, update_modified=False)

    # set encounter.payment_entry to first created PE (if you still use that field)
    if pe_names and hasattr(doc, "payment_entry"):
        doc.db_set("payment_entry", pe_names[0], update_modified=False)

    # show message
    if pe_names:
        frappe.msgprint(
            f"Created Draft Sales Invoice <b>{si.name}</b> and Draft Payment Entry(s) <b>{', '.join(pe_names)}</b>",
            alert=True
        )
    else:
        frappe.msgprint(f"Created Draft Sales Invoice <b>{si.name}</b>", alert=True)


def link_pending_payment_entries(si, method):
    """On SI submit, auto-append reference in any Draft PE that intended to pay this SI."""
    if si.docstatus != 1:
        return

    pe_names = frappe.get_all(
        "Payment Entry",
        filters={
            "docstatus": 0,
            "company": si.company,
            "party_type": "Customer",
            "party": si.customer,
            "intended_sales_invoice": si.name,
        },
        pluck="name",
    )
    if not pe_names:
        return

    outstanding = flt(si.get("outstanding_amount") or si.get("grand_total") or 0)
    if outstanding <= 0:
        return

    for pe_name in pe_names:
        if outstanding <= 0:
            break

        pe = frappe.get_doc("Payment Entry", pe_name)
        already_alloc = sum(flt(r.allocated_amount) for r in (pe.get("references") or []))
        pay_total = flt(pe.get("received_amount") or pe.get("paid_amount") or 0)
        unallocated = max(pay_total - already_alloc, 0)
        if unallocated <= 0:
            continue

        alloc = min(unallocated, outstanding)
        pe.append("references", {
            "reference_doctype": "Sales Invoice",
            "reference_name": si.name,
            "due_date": si.get("due_date") or si.get("posting_date"),
            "allocated_amount": alloc,
        })
        pe.set_missing_values()
        pe.flags.ignore_permissions = True
        pe.save(ignore_permissions=True)

        outstanding -= alloc


# ---------------- Helpers ----------------
# def _create_draft_payment_entry(encounter, customer, mop, amount, intended_si_name, reference_no=None, reference_date=None) -> str:
def _create_draft_payment_entry(
    encounter,
    customer,
    mop,
    amount,
    intended_si_name,
    reference_no=None,
    reference_date=None,
    order_source=None,
    encounter_place=None,
    sales_type=None,
    delivery_type=None,
) -> str:
    """
    Create a draft Payment Entry (ignore_permissions) and return name.
    Now accepts optional reference_no and reference_date (from multi-payment row).
    """
    pe = frappe.new_doc("Payment Entry")
    pe.update({
        "payment_type": "Receive",
        "company": encounter.company,
        "posting_date": nowdate(),
        "mode_of_payment": mop,
        "party_type": "Customer",
        "party": customer,
        # set readable party_name so list view shows friendly name
        "party_name": getattr(encounter, "patient_name", None) or (
            frappe.db.get_value("Patient", encounter.get("patient"), "patient_name")
            if encounter.get("patient") else None
        ),
        "paid_amount": amount,
        "received_amount": amount,
        "reference_no": reference_no,
        "reference_date": reference_date,
    })

    # HRMS override expects party_account prefilled
    party_acc = _party_account(encounter.company, "Customer", customer) \
        or frappe.db.get_value("Company", encounter.company, "default_receivable_account")
    if party_acc:
        pe.party_account = party_acc
        pe.paid_from = party_acc  # for Receive

    paid_to_acc = _mop_account(encounter.company, mop)
    if paid_to_acc:
        pe.paid_to = paid_to_acc

    # store intended SI id so we can auto-link on SI submit
    if hasattr(pe, "intended_sales_invoice"):
        pe.intended_sales_invoice = intended_si_name
    
    # --- NEW: map Encounter custom fields onto Payment Entry IF those fields exist ---
    try:
        pe_meta = frappe.get_meta("Payment Entry")
        if order_source and pe_meta.has_field("sr_pe_order_source"):
            pe.sr_pe_order_source = order_source
        if encounter_place and pe_meta.has_field("sr_pe_encounter_place"):
            pe.sr_pe_encounter_place = encounter_place
        if sales_type and pe_meta.has_field("sr_pe_sales_type"):
            pe.sr_pe_sales_type = sales_type
        if delivery_type and pe_meta.has_field("sr_pe_delivery_type"):
            pe.sr_pe_delivery_type = delivery_type
    except Exception:
        # non-fatal if meta lookup fails
        frappe.log("Failed to map encounter meta fields to Payment Entry (non-fatal)")

    pe.set_missing_values()
    pe.flags.ignore_permissions = True
    pe.insert(ignore_permissions=True)
    return pe.name


def _find_item_rows(doc) -> List[Dict[str, Any]]:
    rows = doc.get(ORDER_ITEMS_TABLE)
    return rows or []


def _get_or_create_customer_from_patient(doc) -> str:
    if not doc.get("patient"):
        frappe.throw("Patient is required on the Encounter to create billing documents.")
    customer = frappe.db.get_value("Patient", doc.patient, "customer")
    if customer:
        return customer
    patient_name = frappe.db.get_value("Patient", doc.patient, "patient_name") or doc.patient
    return _ensure_customer(patient_name, doc.company)


def _ensure_customer(customer_name: str, company: str) -> str:
    existing = frappe.db.get_value("Customer", {"customer_name": customer_name})
    if existing:
        return existing
    c = frappe.new_doc("Customer")
    c.customer_name = customer_name
    c.customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups"
    c.territory = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
    c.company = company
    c.flags.ignore_permissions = True
    c.insert(ignore_permissions=True)
    return c.name


def _is_stock_item(item_code: str) -> int:
    return frappe.db.get_value("Item", item_code, "is_stock_item") or 0


def _valid_warehouse(wh_name: Optional[str], company: str) -> bool:
    if not wh_name or not frappe.db.exists("Warehouse", wh_name):
        return False
    return frappe.db.get_value("Warehouse", wh_name, "company") == company


def _coalesce_warehouse(requested_wh: Optional[str], company: str, item_code: str) -> Optional[str]:
    if not _is_stock_item(item_code):
        return None
    if _valid_warehouse(requested_wh, company):
        return requested_wh

    wh = frappe.db.get_value("Item Default", {"parent": item_code, "company": company}, "default_warehouse")
    if _valid_warehouse(wh, company):
        return wh

    wh = frappe.db.get_single_value("Stock Settings", "default_warehouse")
    if _valid_warehouse(wh, company):
        return wh

    if DEFAULT_FALLBACK_WAREHOUSE and _valid_warehouse(DEFAULT_FALLBACK_WAREHOUSE, company):
        return DEFAULT_FALLBACK_WAREHOUSE
    return None


def _sanitize_si_warehouses(si, company: str) -> None:
    for row in si.items:
        if not _is_stock_item(row.item_code):
            row.warehouse = None
        elif not _valid_warehouse(row.warehouse, company):
            wh = frappe.db.get_value("Item Default", {"parent": row.item_code, "company": company}, "default_warehouse")
            if not _valid_warehouse(wh, company):
                wh = DEFAULT_FALLBACK_WAREHOUSE if (DEFAULT_FALLBACK_WAREHOUSE and _valid_warehouse(DEFAULT_FALLBACK_WAREHOUSE, company)) else None
            row.warehouse = wh


# ---- Tax helpers ----
def _get_primary_address_for(doctype: str, name: str) -> Optional[str]:
    if doctype == "Customer":
        addr = frappe.db.get_value("Customer", name, "customer_primary_address")
        if addr and frappe.db.exists("Address", addr):
            return addr
    links = frappe.get_all("Dynamic Link", filters={"parenttype": "Address", "link_doctype": doctype, "link_name": name}, fields=["parent"], order_by="modified desc", limit=20)
    if not links:
        return None
    for dl in links:
        if frappe.db.get_value("Address", dl.parent, "is_primary_address"):
            return dl.parent
    return links[0]["parent"]


def _get_address_state(addr_name: Optional[str]) -> Optional[str]:
    return frappe.db.get_value("Address", addr_name, "state") if addr_name else None


def _get_customer_state(customer: str) -> Optional[str]:
    return _get_address_state(_get_primary_address_for("Customer", customer))


def _get_company_state(company: str) -> Optional[str]:
    return _get_address_state(_get_primary_address_for("Company", company))


def _get_company_primary_address(company: str) -> Optional[str]:
    links = frappe.get_all("Dynamic Link", filters={"parenttype": "Address", "link_doctype": "Company", "link_name": company}, fields=["parent"], limit=100)
    if not links:
        return None
    addr_names = [dl.parent for dl in links if dl.parent]
    primary = frappe.get_all("Address", filters={"name": ["in", addr_names], "is_primary_address": 1}, fields=["name"], limit=1)
    if primary:
        return primary[0]["name"]
    recent = frappe.get_all("Address", filters={"name": ["in", addr_names]}, fields=["name"], order_by="modified desc", limit=1)
    return recent[0]["name"] if recent else None


def _choose_tax_template_by_state(company: str, customer: str) -> Optional[str]:
    cust_state = (_get_customer_state(customer) or "").strip().lower()
    comp_state = (_get_company_state(company) or "").strip().lower()
    if not cust_state or not comp_state:
        return None
    intrastate = cust_state == comp_state
    prefer_name = TAX_TEMPLATE_INTRASTATE if intrastate else TAX_TEMPLATE_INTERSTATE
    tmpl = frappe.db.get_value("Sales Taxes and Charges Template", {"company": company, "disabled": 0, "name": prefer_name}, "name")
    if tmpl:
        return tmpl
    keyword = "In-state" if intrastate else "Out-state"
    tmpl = frappe.db.get_value("Sales Taxes and Charges Template", {"company": company, "disabled": 0, "name": ["like", f"%{keyword}%"]}, "name") \
        or frappe.db.get_value("Sales Taxes and Charges Template", {"company": company, "disabled": 0, "title": ["like", f"%{keyword}%"]}, "name")
    return tmpl


def _set_tax_template_by_state(si, customer: str) -> None:
    tmpl = _choose_tax_template_by_state(si.company, customer)
    if tmpl:
        si.taxes_and_charges = tmpl
        si.set("taxes", [])


def _apply_company_tax_template(si) -> None:
    if si.taxes_and_charges:
        return
    tmpl = frappe.db.get_value("Sales Taxes and Charges Template", {"company": si.company, "is_default": 1, "disabled": 0}, "name")
    if not tmpl:
        tmpl = frappe.db.get_value("Sales Taxes and Charges Template", {"company": si.company, "disabled": 0}, "name")
    if tmpl:
        si.taxes_and_charges = tmpl
        si.set("taxes", [])


def _company_safe_tax_rows(si) -> None:
    fixed = []
    for t in list(si.get("taxes") or []):
        acc = getattr(t, "account_head", None)
        if not acc:
            continue
        acc_doc = frappe.db.get_value("Account", acc, ["company", "account_name", "account_number"], as_dict=True)
        if not acc_doc:
            continue
        if acc_doc.company == si.company:
            fixed.append(t);
            continue
        mapped = frappe.db.get_value("Account", {"company": si.company, "account_name": acc_doc.account_name, "is_group": 0}, "name")
        if not mapped and acc_doc.account_number:
            mapped = frappe.db.get_value("Account", {"company": si.company, "account_number": acc_doc.account_number, "is_group": 0}, "name")
        if mapped:
            t.account_head = mapped
            fixed.append(t)
    si.set("taxes", fixed)


# ---- Accounts helpers ----
def _party_account(company: str, party_type: str, party: str) -> Optional[str]:
    try:
        return get_party_account(party_type, party, company)
    except TypeError:
        try:
            return get_party_account(company, party_type, party)
        except Exception:
            return None
    except Exception:
        return None


def _mop_account(company: str, mop: str) -> Optional[str]:
    acc = frappe.db.get_value("Mode of Payment Account", {"parent": mop, "company": company}, "default_account")
    if not acc:
        acc = frappe.db.get_value("Mode of Payment Account", {"parent": mop, "company": company}, "account")
    return acc
