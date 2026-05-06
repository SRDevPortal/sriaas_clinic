# apps/sriaas_clinic/sriaas_clinic/api/payment_entry.py
import json
import frappe
from frappe.utils import flt, nowdate
from frappe import _


def hydrate_missing_party_and_reference_fields(doc, method=None):
    """
    Restore standard Payment Entry fields that can be missing from the form payload
    when local DocField metadata is stale, before ERPNext/HRMS validation runs.
    """
    if doc.get("party"):
        _hydrate_missing_reference_fields(doc)
        return

    party = None
    intended_si = doc.get("intended_sales_invoice")

    if not doc.is_new() and frappe.db.has_column("Payment Entry", "party"):
        party = frappe.db.get_value("Payment Entry", doc.name, "party")

    if not party and intended_si:
        party = frappe.db.get_value("Sales Invoice", intended_si, "customer")

    if not party:
        party = _get_party_from_reference_rows(doc)

    if party:
        doc.party_type = doc.get("party_type") or "Customer"
        doc.party = party

        if not doc.get("party_name"):
            doc.party_name = frappe.db.get_value("Customer", party, "customer_name") or party

        if doc.name and frappe.db.has_column("Payment Entry", "party") and not frappe.db.get_value("Payment Entry", doc.name, "party"):
            frappe.db.set_value("Payment Entry", doc.name, "party", party, update_modified=False)

    _hydrate_missing_reference_fields(doc)


def _get_party_from_reference_rows(doc):
    for row in doc.get("references") or []:
        if row.get("reference_doctype") == "Sales Invoice" and row.get("reference_name"):
            return frappe.db.get_value("Sales Invoice", row.reference_name, "customer")
    return None


def _hydrate_missing_reference_fields(doc):
    intended_si = doc.get("intended_sales_invoice")
    for row in doc.get("references") or []:
        for fieldname in (
            "payment_term",
            "payment_request",
            "advance_voucher_type",
            "advance_voucher_no",
        ):
            if not hasattr(row, fieldname):
                setattr(row, fieldname, None)

        if not hasattr(row, "reference_name") or not row.get("reference_name"):
            reference_name = None
            if not row.is_new() and frappe.db.has_column("Payment Entry Reference", "reference_name"):
                reference_name = frappe.db.get_value("Payment Entry Reference", row.name, "reference_name")

            if not reference_name and row.get("reference_doctype") == "Sales Invoice":
                reference_name = intended_si

            if reference_name:
                row.reference_name = reference_name


def repair_payment_entry_ledger_links(doc, method=None):
    """Repair ledger rows when stale DocField metadata drops Dynamic Link values."""
    if doc.docstatus != 1:
        return

    remarks = doc.get("remarks") or ""
    if frappe.db.has_column("GL Entry", "voucher_no"):
        frappe.db.sql(
            """
            update `tabGL Entry`
            set voucher_no = %s,
                party = case
                    when account = %s and (party is null or party = '') then %s
                    else party
                end
            where voucher_type = 'Payment Entry'
              and (voucher_no is null or voucher_no = '')
              and company = %s
              and ifnull(remarks, '') = %s
            """,
            (doc.name, doc.get("paid_from"), doc.get("party"), doc.company, remarks),
        )

    for row in doc.get("references") or []:
        if row.get("reference_doctype") != "Sales Invoice" or not row.get("reference_name"):
            continue

        if frappe.db.has_column("Payment Ledger Entry", "voucher_no"):
            frappe.db.sql(
                """
                update `tabPayment Ledger Entry`
                set voucher_no = %s,
                    against_voucher_no = %s,
                    party = %s
                where voucher_type = 'Payment Entry'
                  and (voucher_no is null or voucher_no = '')
                  and company = %s
                  and account = %s
                  and ifnull(remarks, '') = %s
                  and delinked = 0
                """,
                (
                    doc.name,
                    row.reference_name,
                    doc.get("party"),
                    doc.company,
                    doc.get("paid_from"),
                    remarks,
                ),
            )

        _refresh_sales_invoice_outstanding(row.reference_name, doc)


def _refresh_sales_invoice_outstanding(invoice_name, doc):
    try:
        from erpnext.accounts.utils import update_voucher_outstanding

        update_voucher_outstanding(
            voucher_type="Sales Invoice",
            voucher_no=invoice_name,
            account=doc.get("paid_from"),
            party_type="Customer",
            party=doc.get("party"),
        )
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            f"Failed refreshing outstanding for Sales Invoice {invoice_name}",
        )


# before_insert handler to set created_by_agent if not provided
def set_created_by_agent(doc, method):
    """
    Hook: before_insert on Payment Entry
    Populate created_by_agent with current session user if empty.
    """
    try:
        if not getattr(doc, "created_by_agent", None):
            doc.created_by_agent = frappe.session.user
    except Exception:
        # don't block creation for non-critical failure
        frappe.log_error(f"set_created_by_agent failed for Payment Entry {getattr(doc, 'name', '')}")


# before_save handler to sync parent mode_of_payment based on child sr_payment_modes
# def sync_parent_mode_from_children_server(doc, method):
#     # if single child -> set parent; if multiple -> set to 'Multiple' if exists
#     rows = getattr(doc, "sr_payment_modes", []) or []
#     if not rows:
#         return

#     modes = list({r.sr_mode_of_payment for r in rows if getattr(r, "sr_mode_of_payment", None)})
#     if len(modes) == 1:
#         doc.mode_of_payment = modes[0]
#     elif len(modes) > 1:
#         # prefer Mode of Payment named 'Multiple' if exists
#         multiple = frappe.db.exists("Mode of Payment", "Multiple")
#         if multiple:
#             doc.mode_of_payment = "Multiple"
#         else:
#             # leave parent as-is or set to comma-joined (unsafe if Link)
#             # doc.mode_of_payment = ", ".join(modes)
#             pass


# validate handler to ensure sum of sr_payment_modes.sr_amount equals doc.paid_amount
# def validate_payment_modes_total(doc, method):
#     """
#     Ensure sum(sr_payment_modes.sr_amount) == doc.paid_amount
#     Attach this function in hooks.py:
#       "Payment Entry": { "validate": "sriaas_clinic.api.payment_entry.validate_payment_modes_total" }
#     """
#     try:
#         rows = doc.sr_payment_modes or []
#         total = flt(sum([flt(getattr(r, "sr_amount", 0)) for r in rows]))
#         if flt(doc.paid_amount) != total:
#             frappe.throw(_("Sum of Payment Modes ({0}) must equal Paid Amount ({1}).").format(total, doc.paid_amount))
#     except frappe.ValidationError:
#         raise
#     except Exception as e:
#         frappe.log_error(f"validate_payment_modes_total error for Payment Entry {getattr(doc,'name', '')}: {str(e)}")
#         # rethrow as validation to be safe
#         frappe.throw(_("Unable to validate payment modes total. See error log."))


# on_submit handler to create Journal Entry based on sr_payment_modes
# def create_journal_for_payment_modes(doc, method):
#     """
#     Create a Journal Entry on submit with:
#       - Debit: each sr_payment_modes.sr_account = sr_amount
#       - Credit: party_account (or configured clearing account) = total
#     Attach this function in hooks.py:
#       "Payment Entry": { "on_submit": "sriaas_clinic.api.payment_entry.create_journal_for_payment_modes" }
#     Notes:
#       - Ensure Payment Entry has proper party_account or configure a clearing account.
#       - Avoid duplicate JE creation by checking existing Journal Entries with
#         sr_auto_created_from_payment_entry == doc.name
#     """
#     try:
#         rows = doc.sr_payment_modes or []
#         if not rows:
#             return

#         total = flt(sum([flt(getattr(r, "sr_amount", 0)) for r in rows]))
#         if total <= 0:
#             frappe.throw(_("Total of payment mode amounts must be greater than zero."))

#         # Prevent duplicate JE creation: check if JE already exists with flag
#         existing_je = frappe.db.get_value(
#             "Journal Entry", {"sr_auto_created_from_payment_entry": doc.name}
#         )
#         if existing_je:
#             # JE already created earlier; nothing to do.
#             return

#         # Determine credit target: prefer doc.party_account, else fallback to configured clearing account
#         party_account = getattr(doc, "party_account", None)
#         if not party_account:
#             # Try site single doctype SRIAAS Clinic Settings -> clearing_account (optional)
#             try:
#                 party_account = frappe.get_single("SRIAAS Clinic Settings").get("clearing_account")
#             except Exception:
#                 # no site setting - leave None
#                 party_account = None

#         if not party_account:
#             frappe.throw(_(
#                 "Payment Entry missing party_account and no clearing account configured. "
#                 "Cannot create Journal Entry for payment modes."
#             ))

#         # Build JE accounts: debit each sr_account; credit single party_account
#         je_accounts = []
#         for r in rows:
#             sr_account = getattr(r, "sr_account", None)
#             sr_amount = flt(getattr(r, "sr_amount", 0))
#             if not sr_account:
#                 frappe.throw(_("Payment Mode row missing Account for mode {0}").format(getattr(r, "sr_mode_of_payment", "")))
#             if sr_amount <= 0:
#                 frappe.throw(_("Each Payment Mode row must have an amount greater than zero."))

#             je_accounts.append({
#                 "account": sr_account,
#                 "debit_in_account_currency": sr_amount,
#                 "credit_in_account_currency": 0.0,
#                 "remarks": getattr(r, "description", None) or _("Payment mode {0}").format(getattr(r, "sr_mode_of_payment", "")),
#             })

#         # Single credit line to party_account (party info optional)
#         credit_line = {
#             "account": party_account,
#             "debit_in_account_currency": 0.0,
#             "credit_in_account_currency": total,
#             "remarks": _("Payment Entry {0} - combined modes").format(doc.name)
#         }
#         # include party info if available (helps reconciliation)
#         if getattr(doc, "party_type", None) and getattr(doc, "party", None):
#             credit_line["party_type"] = doc.party_type
#             credit_line["party"] = doc.party

#         je_accounts.append(credit_line)

#         # Determine voucher_type
#         voucher_type = "Bank Entry" if (getattr(doc, "payment_type", "") == "Receive") else "Journal Entry"

#         je = frappe.get_doc({
#             "doctype": "Journal Entry",
#             "voucher_type": voucher_type,
#             "company": doc.company,
#             "posting_date": getattr(doc, "posting_date", nowdate()),
#             "user_remark": _("Auto-generated for Payment Entry {0}").format(doc.name),
#             "accounts": je_accounts,
#             "sr_auto_created_from_payment_entry": doc.name
#         })

#         je.insert(ignore_permissions=True)
#         je.submit()

#         # store the linked JE on the Payment Entry if custom field exists
#         try:
#             meta = frappe.get_meta("Payment Entry")
#             if meta.get_field("sr_linked_journal_entry"):
#                 frappe.db.set_value("Payment Entry", doc.name, "sr_linked_journal_entry", je.name)
#         except Exception:
#             # log but don't block
#             frappe.log_error(f"Failed to set sr_linked_journal_entry for Payment Entry {doc.name}")

#     except frappe.ValidationError:
#         raise
#     except Exception as e:
#         frappe.log_error(f"create_journal_for_payment_modes error for Payment Entry {getattr(doc,'name','')}: {str(e)}")
#         frappe.throw(_("Failed to create Journal Entry for payment modes. See error log."))


# on_cancel handler to cancel linked Journal Entry if exists
# def cancel_linked_journal_entries(doc, method):
#     """
#     Cancel linked Journal Entry created earlier (if any).
#     Attach in hooks.py:
#       "Payment Entry": { "on_cancel": "sriaas_clinic.api.payment_entry.cancel_linked_journal_entries" }
#     """
#     try:
#         # Prefer custom linked field if exists
#         je_name = None
#         meta = frappe.get_meta("Payment Entry")
#         if meta.get_field("sr_linked_journal_entry"):
#             je_name = frappe.db.get_value("Payment Entry", doc.name, "sr_linked_journal_entry")
#         # fallback: find JE with sr_auto_created_from_payment_entry
#         if not je_name:
#             je_name = frappe.db.get_value("Journal Entry", {"sr_auto_created_from_payment_entry": doc.name})

#         if not je_name:
#             return

#         je = frappe.get_doc("Journal Entry", je_name)
#         if je.docstatus == 1:
#             je.cancel()
#     except Exception as e:
#         frappe.log_error(f"Failed to cancel JE for Payment Entry {doc.name}: {str(e)}")


# ----------------------------------------------------------------------
# Whitelisted API: create Payment Entry from payload
# ----------------------------------------------------------------------
# @frappe.whitelist()
# def create_payment_entry_from_payload(payload):
#     """
#     Whitelisted endpoint to create (and optionally submit) a Payment Entry with sr_payment_modes.
#     Call via:
#       /api/method/sriaas_clinic.api.payment_entry.create_payment_entry_from_payload
#     payload: JSON string or dict. Example:
#     {
#       "company": "My Company",
#       "party_type": "Customer",
#       "party": "CUST-0001",
#       "posting_date": "2025-11-14",
#       "payment_type": "Receive",
#       "paid_amount": 10000,
#       "mode_of_payment": "Cash",
#       "reference_no": "",
#       "reference_date": "",
#       "sr_payment_modes": [
#         {"sr_mode_of_payment": "Cash", "sr_amount": 5000, "sr_account": "Cash - Main - ABC"},
#         {"sr_mode_of_payment": "Card", "sr_amount": 5000, "sr_account": "Bank - Card - ABC"}
#       ],
#       "created_by_agent": "user@example.com",
#       "intended_sales_invoice": "SINV-0001",
#       "submit": 1   # optional, submit after create
#     }
#     Returns Payment Entry name string on success.
#     """
#     try:
#         if isinstance(payload, str):
#             payload = json.loads(payload)

#         # Basic required validation
#         if not payload.get("company"):
#             frappe.throw(_("company is required"))

#         sr_rows = payload.get("sr_payment_modes", []) or []
#         total = flt(sum([flt(r.get("sr_amount", 0)) for r in sr_rows]))
#         paid_amount = flt(payload.get("paid_amount", 0))

#         if paid_amount != total:
#             frappe.throw(_("Sum of payment modes ({0}) does not equal paid_amount ({1}).").format(total, paid_amount))

#         # Build Payment Entry doc
#         pe_doc = frappe.get_doc({
#             "doctype": "Payment Entry",
#             "company": payload.get("company"),
#             "party_type": payload.get("party_type"),
#             "party": payload.get("party"),
#             "posting_date": payload.get("posting_date") or nowdate(),
#             "payment_type": payload.get("payment_type") or "Receive",
#             "paid_amount": paid_amount,
#             "mode_of_payment": payload.get("mode_of_payment"),
#             "reference_no": payload.get("reference_no"),
#             "reference_date": payload.get("reference_date"),
#             "intended_sales_invoice": payload.get("intended_sales_invoice"),
#             "created_by_agent": payload.get("created_by_agent"),
#         })

#         for r in sr_rows:
#             if not r.get("sr_account"):
#                 frappe.throw(_("Each payment mode row must include sr_account. Row: {0}").format(str(r)))
#             pe_doc.append("sr_payment_modes", {
#                 "sr_mode_of_payment": r.get("sr_mode_of_payment"),
#                 "sr_amount": flt(r.get("sr_amount", 0)),
#                 "sr_account": r.get("sr_account"),
#                 "sr_reference_no": r.get("sr_reference_no"),
#                 "sr_reference_date": r.get("sr_reference_date"),
#                 "description": r.get("description")
#             })

#         pe_doc.insert(ignore_permissions=True)

#         # Submit if requested
#         if int(payload.get("submit", 0)):
#             pe_doc.submit()
#         else:
#             pe_doc.save()

#         return pe_doc.name

#     except frappe.ValidationError:
#         raise
#     except Exception as e:
#         frappe.log_error(f"create_payment_entry_from_payload error: {str(e)}")
#         frappe.throw(_("Failed to create Payment Entry. See error log."))
