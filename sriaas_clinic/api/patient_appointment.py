# apps/sriaas_clinic/sriaas_clinic/api/patient_appointment.py

import frappe
from frappe.utils import nowdate, flt

def set_created_by_agent(doc, method):
    # only set if empty (so it doesn't overwrite later edits)
    if not getattr(doc, "created_by_agent", None):
        doc.created_by_agent = frappe.session.user


def create_payment_entries_from_child_table(doc, method=None):
    """
    Create one Payment Entry per child row in doc.apt_payments.
    Safe to call multiple times — skips rows that already have sr_payment_entry.
    """
    try:
        if not getattr(doc, "apt_payments", None):
            return

        # prefer patient's display name for Customer / Party Name
        patient_name = getattr(doc, "patient_name", None) or getattr(doc, "patient", None)

        for row in doc.apt_payments:

            # Skip already processed rows
            if getattr(row, "sr_payment_entry", None):
                continue

            amount = flt(getattr(row, "sr_paid_amount", 0))
            if amount <= 0:
                continue

            # ------------------------------
            # Resolve Customer (prefer patient_name)
            # ------------------------------
            customer = None

            # Try several lookups to find an existing Customer:
            # 1) exact match by doc.patient (some installs used patient id as customer name)
            if getattr(doc, "patient", None) and frappe.db.exists("Customer", doc.patient):
                customer = doc.patient

            # 2) match by customer_name == patient_name
            if not customer and patient_name:
                cust = frappe.get_all("Customer", filters={"customer_name": patient_name}, limit=1)
                if cust:
                    customer = cust[0].name

            # 3) fallback: if patient stored as customer name earlier (customer_name == doc.patient)
            if not customer and getattr(doc, "patient", None):
                cust = frappe.get_all("Customer", filters={"customer_name": doc.patient}, limit=1)
                if cust:
                    customer = cust[0].name

            # Create minimal Customer using patient_name (so Party Name shows correctly)
            if not customer:
                try:
                    cust_doc = frappe.get_doc({
                        "doctype": "Customer",
                        # Use patient display name for customer_name to show as Party Name
                        "customer_name": patient_name or f"Patient {doc.name}",
                        "customer_group": frappe.db.get_value("Customer Group", {}, "name") or "All Customer Groups",
                        "territory": frappe.db.get_value("Territory", {}, "name") or "All Territories",
                    })
                    cust_doc.insert(ignore_permissions=True)
                    customer = cust_doc.name
                except Exception:
                    frappe.log_error(frappe.get_traceback(),
                                     f"Failed creating Customer for appointment {doc.name}")
                    continue

            # ------------------------------
            # Resolve paid_to_account (robust)
            # ------------------------------
            paid_to_account = None

            # 1) If child row has an explicit account
            if getattr(row, "sr_account", None):
                paid_to_account = row.sr_account

            # 2) Lookup via Mode of Payment → Mode of Payment Account table
            if not paid_to_account:
                mop = getattr(row, "sr_mode_of_payment", None)
                if mop and frappe.db.exists("Mode of Payment", mop):
                    mop_accounts = frappe.get_all(
                        "Mode of Payment Account",
                        filters={"parent": mop, "company": doc.company},
                        fields=["default_account"],
                        limit=1
                    )
                    if mop_accounts:
                        paid_to_account = mop_accounts[0].default_account

            # 3) Use company's default cash or bank account
            if not paid_to_account and getattr(doc, "company", None):
                paid_to_account = (
                    frappe.get_value("Company", doc.company, "default_cash_account") or
                    frappe.get_value("Company", doc.company, "default_bank_account")
                )

            # 4) Last fallback: find any Cash/Bank account
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

            # 5) Still empty → log error and skip row
            if not paid_to_account:
                frappe.log_error(
                    f"No paid_to account resolved for Appointment {doc.name}, row {row.name}",
                    "Payment Entry creation skipped"
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
                # set party_name explicitly so List shows proper display name
                "party_name": patient_name,
                "paid_amount": amount,
                "received_amount": amount,
                "paid_to": paid_to_account,
                "mode_of_payment": getattr(row, "sr_mode_of_payment", None),
                "posting_date": getattr(row, "sr_posting_date", None) or nowdate(),
                "reference_no": getattr(row, "sr_reference_no", None) or doc.name,
                "reference_date": getattr(row, "sr_reference_date", None) or nowdate(),
                "reference_doctype": doc.doctype,
                "reference_name": doc.name,
                "remarks": f"Appointment payment for {doc.name}"
            })

            # Create draft Payment Entry
            try:
                pe_doc.insert(ignore_permissions=True)
            except Exception:
                frappe.log_error(frappe.get_traceback(),
                                 f"Failed INSERT Payment Entry for Appointment {doc.name}")
                continue

            # Auto-submit
            try:
                pe_doc.submit()
            except Exception:
                frappe.log_error(frappe.get_traceback(),
                                 f"Failed SUBMIT Payment Entry {pe_doc.name}")
                # Keep in Draft, continue
                pass

            pe_doc.reload()  # refresh final values

            # ------------------------------
            # Update child row
            # ------------------------------
            try:
                frappe.db.set_value("SR Patient Payment View", row.name, {
                    "sr_payment_entry": pe_doc.name,
                    "sr_posting_date": pe_doc.posting_date
                })
            except Exception:
                frappe.log_error(frappe.get_traceback(),
                                 f"Failed saving PE link back to child row for {doc.name}")

        frappe.db.commit()

    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"Fatal error: create_payment_entries_from_child_table() for {doc.name}")


def on_update_create_payments(doc, method=None):
    """
    Hook: Patient Appointment on_update
    Create Payment Entries when status/workflow_state becomes 'Confirmed'.
    This avoids relying on on_submit (doc is not submittable due to workflow).
    """
    try:
        # adjust field name if you use workflow_state instead of status
        status = (getattr(doc, "status", None) or getattr(doc, "workflow_state", None) or "").strip().lower()
        # only run for confirmed appointments
        if status != "confirmed":
            return

        # Quick duplicate-safety: if at least one child row already has a PE, assume done.
        has_any = False
        for row in getattr(doc, "apt_payments", []) or []:
            if getattr(row, "sr_payment_entry", None):
                has_any = True
                break

        if has_any:
            # If you prefer to re-sync or create missing ones, skip this check.
            # Here we skip to avoid duplicate PEs on multiple updates.
            return

        # call the creator
        create_payment_entries_from_child_table(doc, method)

    except Exception:
        frappe.log_error(frappe.get_traceback(), "on_update_create_payments failed")


@frappe.whitelist()
def create_payment_entries_for_appointment(appointment_name):
    """
    Whitelisted helper to manually trigger creation for an appointment.
    Useful for testing or manual sync.
    """
    doc = frappe.get_doc("Patient Appointment", appointment_name)
    create_payment_entries_from_child_table(doc)
    return {"status": "ok"}
