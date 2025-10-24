# sriaas_clinic/api/si_payment_flow/handlers.py

from typing import Optional, Set, Tuple
import frappe
from frappe.utils import nowdate, flt
from erpnext.accounts.party import get_party_account

# -----------------------------
# Draft Payment (input) fields
# -----------------------------
F_AMT   = "si_dp_paid_amount"
F_MOP   = "si_dp_mode_of_payment"
F_REFNO = "si_dp_reference_no"
F_REFD  = "si_dp_reference_date"
F_PROOF = "si_dp_payment_proof"


# -----------------------------
# Utilities
# -----------------------------

def _has_any_attachment(doc) -> bool:
    """True if the doc has any File attached via the sidebar."""
    return bool(
        frappe.get_all(
            "File",
            filters={"attached_to_doctype": doc.doctype, "attached_to_name": doc.name},
            limit=1,
        )
    )


# -----------------------------------------
# Draft Payment (input) field validations
# -----------------------------------------

def clear_dp_when_blank(si, method):
    """If amount is blank/zero, clear dependent fields to avoid stale data."""
    amt = flt(si.get(F_AMT) or 0)
    if amt <= 0:
        for f in (F_MOP, F_REFNO, F_REFD, F_PROOF):
            if getattr(si, f, None):
                setattr(si, f, None)


# def validate_dp_before_submit(si, method):
#     """If amount > 0, enforce minimal details before submit."""
#     amt = flt(si.get(F_AMT) or 0)
#     if amt <= 0:
#         return

#     missing = []
#     if not (si.get(F_MOP) or "").strip():
#         missing.append("Mode of Payment")
#     if not si.get(F_REFD):
#         missing.append("Reference Date")

#     has_proof = bool(si.get(F_PROOF)) or _has_any_attachment(si)
#     if not has_proof:
#         missing.append("Payment Proof (upload in field or via Attachments)")

#     if missing:
#         frappe.throw("Please complete Draft Payment: " + ", ".join(missing))

def validate_dp_before_submit(si, method):
    """If amount > 0, enforce minimal details before submit."""
    amt = flt(si.get(F_AMT) or 0)
    if amt <= 0:
        return

    missing = []
    if not (si.get(F_MOP) or "").strip():
        missing.append("Mode of Payment")
    if not si.get(F_REFD):
        missing.append("Reference Date")

    # PROOF OPTIONAL: remove hard requirement
    # If you still want to *nudge* the user, show a non-blocking message:
    if not (si.get(F_PROOF) or _has_any_attachment(si)):
        frappe.msgprint(
            "No Payment Proof attached. You can add one later from Attachments.",
            alert=True,
        )

    if missing:
        frappe.throw("Please complete Draft Payment: " + ", ".join(missing))


# -----------------------------
# Accounts helpers
# -----------------------------

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
    acc = frappe.db.get_value(
        "Mode of Payment Account", {"parent": mop, "company": company}, "default_account"
    )
    if not acc:
        acc = frappe.db.get_value(
            "Mode of Payment Account", {"parent": mop, "company": company}, "account"
        )
    return acc


# ---------------------------------------------------
# Create Draft Payment Entry from SI Draft Payment UI
# ---------------------------------------------------

def create_pe_from_si_dp(si, method):
    """
    On Sales Invoice submit:
      - If Draft Payment fields indicate an advance, create a DRAFT Payment Entry.
      - Append a reference row to this submitted SI (allocated up to outstanding).
      - Keep PE as Draft (consistent with Encounter flow).
      - Refresh Payment History on the SI.
    """
    if si.docstatus != 1:
        return

    amt = flt(si.get(F_AMT) or 0)
    mop = (si.get(F_MOP) or "").strip()
    if amt <= 0 or not mop:
        # Nothing to create; still refresh the history so the panel shows final state
        refresh_payment_history(si)
        return

    # Create Payment Entry (Draft)
    pe = frappe.new_doc("Payment Entry")
    pe.update({
        "payment_type": "Receive",
        "company": si.company,
        "posting_date": nowdate(),
        "mode_of_payment": mop,
        "party_type": "Customer",
        "party": si.customer,
        "paid_amount": amt,
        "received_amount": amt,
        "reference_no": si.get(F_REFNO),
        "reference_date": si.get(F_REFD),
    })

    # Accounts
    party_acc = _party_account(si.company, "Customer", si.customer) \
        or frappe.db.get_value("Company", si.company, "default_receivable_account")
    if party_acc:
        pe.party_account = party_acc
        pe.paid_from = party_acc  # for Receive

    paid_to_acc = _mop_account(si.company, mop)
    if paid_to_acc:
        pe.paid_to = paid_to_acc

    # Optional helper field to mark intent, if present on your PE doctype
    if hasattr(pe, "intended_sales_invoice"):
        pe.intended_sales_invoice = si.name

    pe.set_missing_values()
    pe.flags.ignore_permissions = True
    pe.insert(ignore_permissions=True)  # keep Draft

    # Link reference to this submitted SI
    outstanding = flt(si.get("outstanding_amount") or 0)
    if outstanding > 0:
        alloc = min(outstanding, amt)
        pe.append("references", {
            "reference_doctype": "Sales Invoice",
            "reference_name": si.name,
            "due_date": si.get("due_date") or si.get("posting_date"),
            "allocated_amount": alloc,
        })
        pe.set_missing_values()
        pe.save(ignore_permissions=True)

    frappe.msgprint(
        f"Draft Payment Entry <b>{pe.name}</b> prepared for this invoice.",
        alert=True
    )

    # Update the Payment History summary panel on SI right away
    refresh_payment_history(si)


# -------------------------------------------------
# Payment History (read-only UI summary) updaters
# -------------------------------------------------

def _sum_pe_allocations_for_invoice(si_name: str, company: str, customer: str) -> Tuple[float, Set[str]]:
    """
    Sum allocated amounts from SUBMITTED Payment Entries that reference this SI.
    Returns (total_allocated, set_of_MOPs).
    """
    res = frappe.db.sql(
        """
        select per.allocated_amount, pe.mode_of_payment
        from `tabPayment Entry Reference` per
        join `tabPayment Entry` pe on pe.name = per.parent
        where per.reference_doctype = 'Sales Invoice'
          and per.reference_name = %s
          and pe.docstatus = 1
          and pe.company = %s
          and pe.party_type = 'Customer'
          and pe.party = %s
        """,
        (si_name, company, customer),
        as_dict=True,
    )
    total = 0.0
    mops: Set[str] = set()
    for r in res:
        total += flt(r.allocated_amount)
        mop = (r.mode_of_payment or "").strip()
        if mop:
            mops.add(mop)
    return total, mops


def _sum_pos_payments(si) -> Tuple[float, Set[str]]:
    """If SI uses POS payments table, include them for UI summary."""
    total = 0.0
    mops: Set[str] = set()
    if getattr(si, "is_pos", 0):
        for p in (si.get("payments") or []):
            total += flt(getattr(p, "amount", 0))
            mop = (getattr(p, "mode_of_payment", "") or "").strip()
            if mop:
                mops.add(mop)
    return total, mops


def refresh_payment_history(si, method=None):
    """
    Compute & write Payment History fields on Sales Invoice:
      - sr_si_paid_amount
      - sr_si_outstanding_amount
      - sr_si_mode_of_payment (single or 'Multiple')
      - sr_si_payment_term (Unpaid / Partially Paid / Paid in Full)
    """
    total = flt(si.get("rounded_total") or si.get("grand_total") or 0)
    outstanding = flt(si.get("outstanding_amount") or 0)

    # --- Gather Submitted Payment Entry data ---
    pe_paid, pe_mops = _sum_pe_allocations_for_invoice(si.name, si.company, si.customer)
    pos_paid, pos_mops = _sum_pos_payments(si)

    total_paid = pe_paid + pos_paid
    all_mops = pe_mops.union(pos_mops)

    # --- Fallback: use Draft Payment fields if no submitted PE ---
    dp_amt = flt(si.get("si_dp_paid_amount") or 0)
    dp_mop = (si.get("si_dp_mode_of_payment") or "").strip()
    if total_paid <= 0 and dp_amt > 0:
        total_paid = dp_amt
        if dp_mop:
            all_mops.add(dp_mop)

    # Mode of Payment summary
    mop_summary = ""
    if len(all_mops) == 1:
        mop_summary = list(all_mops)[0]
    elif len(all_mops) > 1:
        mop_summary = "Multiple"

    # Determine term
    eps = 0.005
    if total <= eps or abs(outstanding) <= eps or abs(total - total_paid) <= eps:
        term = "Paid in Full"
        outstanding_ui = 0.0
    elif total_paid <= eps:
        term = "Unpaid"
        outstanding_ui = total
    else:
        term = "Partially Paid"
        outstanding_ui = max(total - total_paid, 0)

    # Persist without recursion
    updates = {
        "sr_si_payment_term": term,
        "sr_si_paid_amount": total_paid,
        "sr_si_mode_of_payment": mop_summary,
        "sr_si_outstanding_amount": outstanding_ui,
    }
    for f, v in updates.items():
        if hasattr(si, f):
            si.db_set(f, v, update_modified=False)
