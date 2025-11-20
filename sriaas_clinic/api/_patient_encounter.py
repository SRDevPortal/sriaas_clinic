# apps/sriaas_clinic/sriaas_clinic/api/patient_encounter.py

import frappe
from frappe.utils import nowdate, flt

def set_created_by_agent(doc, method):
    """Set created_by_agent for new encounters."""
    if not getattr(doc, "created_by_agent", None):
        doc.created_by_agent = frappe.session.user


def create_payment_entries_from_encounter_child_table(doc, method=None):
    """
    Create one Payment Entry per child row in doc.enc_multi_payments (SR Multi Mode Payment).
    Safe to call multiple times — skips rows that already have mmp_payment_entry.
    """
    try:
        rows = getattr(doc, "enc_multi_payments", None)
        if not rows:
            return

        # prefer patient's display name for party_name
        patient_name = getattr(doc, "patient_name", None) or getattr(doc, "patient", None)

        for row in rows:
            # Skip already processed rows
            if getattr(row, "mmp_payment_entry", None):
                continue

            amount = flt(getattr(row, "mmp_paid_amount", 0))
            if amount <= 0:
                continue

            # ------------------------------
            # Resolve Customer
            # ------------------------------
            customer = None

            # 1) exact match by doc.patient (if some installs use patient as customer)
            if getattr(doc, "patient", None) and frappe.db.exists("Customer", doc.patient):
                customer = doc.patient

            # 2) match by customer_name == patient_name
            if not customer and patient_name:
                cust = frappe.get_all("Customer", filters={"customer_name": patient_name}, limit=1)
                if cust:
                    customer = cust[0].name

            # 3) fallback: customer_name == doc.patient
            if not customer and getattr(doc, "patient", None):
                cust = frappe.get_all("Customer", filters={"customer_name": doc.patient}, limit=1)
                if cust:
                    customer = cust[0].name

            # 4) create minimal Customer using patient_name
            if not customer:
                try:
                    cust_doc = frappe.get_doc({
                        "doctype": "Customer",
                        "customer_name": patient_name or f"Patient {doc.name}",
                        "customer_group": frappe.db.get_value("Customer Group", {}, "name") or "All Customer Groups",
                        "territory": frappe.db.get_value("Territory", {}, "name") or "All Territories",
                    })
                    cust_doc.insert(ignore_permissions=True)
                    customer = cust_doc.name
                except Exception:
                    frappe.log_error(frappe.get_traceback(),
                                     f"Failed creating Customer for encounter {doc.name}")
                    continue

            # ------------------------------
            # Resolve paid_to_account (robust)
            # ------------------------------
            paid_to_account = None

            # 1) If child row has an explicit account field (mmp_account) use it
            if getattr(row, "mmp_account", None):
                paid_to_account = row.mmp_account

            # 2) Lookup via Mode of Payment -> Mode of Payment Account
            if not paid_to_account:
                mop = getattr(row, "mmp_mode_of_payment", None)
                if mop and frappe.db.exists("Mode of Payment", mop):
                    mop_accounts = frappe.get_all(
                        "Mode of Payment Account",
                        filters={"parent": mop, "company": doc.company},
                        fields=["default_account"],
                        limit=1
                    )
                    if mop_accounts:
                        paid_to_account = mop_accounts[0].default_account

            # 3) Use company's default cash/bank account
            if not paid_to_account and getattr(doc, "company", None):
                paid_to_account = (
                    frappe.get_value("Company", doc.company, "default_cash_account")
                    or frappe.get_value("Company", doc.company, "default_bank_account")
                )

            # 4) Fallback: any Cash/Bank account for company
            if not paid_to_account and getattr(doc, "company", None):
                acct = frappe.get_all(
                    "Account",
                    filters={
                        "company": doc.company,
                        "is_group": 0,
                        "account_type": ["in", ["Cash", "Bank"]]
                    },
                    fields=["name"],
                    limit=1
                )
                if acct:
                    paid_to_account = acct[0].name

            # 5) If still no account -> log and skip
            if not paid_to_account:
                frappe.log_error(
                    f"No paid_to account resolved for Encounter {doc.name}, row {row.name}",
                    "Payment Entry creation skipped (Encounter)"
                )
                continue

            # ------------------------------
            # Build Payment Entry
            # ------------------------------
            pe_doc = frappe.get_doc({
                "doctype": "Payment Entry",
                "payment_type": "Receive",
                "company": doc.company,
                "party_type": "Customer",
                "party": customer,
                "party_name": patient_name,
                "paid_amount": amount,
                "received_amount": amount,
                "paid_to": paid_to_account,
                "mode_of_payment": getattr(row, "mmp_mode_of_payment", None),
                "posting_date": getattr(row, "mmp_posting_date", None) or nowdate(),
                "reference_no": getattr(row, "mmp_reference_no", None) or doc.name,
                "reference_date": getattr(row, "mmp_reference_date", None) or nowdate(),
                "reference_doctype": doc.doctype,
                "reference_name": doc.name,
                "remarks": f"Encounter payment for {doc.name}"
            })

            # Insert (draft)
            try:
                pe_doc.insert(ignore_permissions=True)
            except Exception:
                frappe.log_error(frappe.get_traceback(),
                                 f"Failed INSERT Payment Entry for Encounter {doc.name}")
                continue

            # Try to auto-submit — if submit fails keep draft and log
            try:
                pe_doc.submit()
            except Exception:
                frappe.log_error(frappe.get_traceback(),
                                 f"Failed SUBMIT Payment Entry {pe_doc.name}")
                pass

            pe_doc.reload()

            # ------------------------------
            # Update child row with created PE
            # ------------------------------
            try:
                frappe.db.set_value("SR Multi Mode Payment", row.name, {
                    "mmp_payment_entry": pe_doc.name,
                    "mmp_posting_date": pe_doc.posting_date
                })
            except Exception:
                frappe.log_error(frappe.get_traceback(),
                                 f"Failed saving PE link back to encounter child row {doc.name}")

        frappe.db.commit()

    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"Fatal error: create_payment_entries_from_encounter_child_table() for {doc.name}")


def on_update_create_payments(doc, method=None):
    """
    Hook: Patient Encounter on_update
    Create Payment Entries when status/workflow_state becomes 'Confirmed'.
    """
    try:
        status = (getattr(doc, "status", None) or getattr(doc, "workflow_state", None) or "").strip().lower()
        if status != "confirmed":
            return

        # If any row already has a linked PE we treat as done to avoid duplicates
        has_any = False
        for row in getattr(doc, "enc_multi_payments", []) or []:
            if getattr(row, "mmp_payment_entry", None):
                has_any = True
                break

        if has_any:
            return

        create_payment_entries_from_encounter_child_table(doc, method)

    except Exception:
        frappe.log_error(frappe.get_traceback(), "on_update_create_payments (encounter) failed")


@frappe.whitelist()
def create_payment_entries_for_encounter(encounter_name):
    """Manual trigger: create PEs for an encounter"""
    doc = frappe.get_doc("Patient Encounter", encounter_name)
    create_payment_entries_from_encounter_child_table(doc)
    return {"status": "ok"}
