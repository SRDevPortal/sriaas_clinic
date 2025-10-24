# sriaas_clinic/api/si_payment_flow/pe_lookup.py
import frappe

@frappe.whitelist()
def get_payment_entries_for_invoice(si_name: str):
    """Return Payment Entries linked to this Sales Invoice.
    Includes:
      - Submitted PEs that reference this SI (via Payment Entry Reference)
      - Draft PEs that intended to pay this SI (your custom field `intended_sales_invoice`)
    """
    if not si_name:
        return []

    # Submitted PEs via references
    submitted = frappe.db.sql(
        """
        select pe.name, pe.docstatus, pe.posting_date, pe.party, pe.party_type,
               pe.mode_of_payment, pe.received_amount, pe.paid_amount, pe.status
        from `tabPayment Entry` pe
        join `tabPayment Entry Reference` per on per.parent = pe.name
        where per.reference_doctype = 'Sales Invoice'
          and per.reference_name = %s
          and pe.docstatus = 1
        order by pe.posting_date desc, pe.creation desc
        """,
        (si_name,),
        as_dict=True,
    )

    # Draft PEs that intend to pay this SI (optional, your custom field)
    drafts = []
    if frappe.get_meta("Payment Entry").has_field("intended_sales_invoice"):
        drafts = frappe.db.sql(
            """
            select name, docstatus, posting_date, party, party_type,
                   mode_of_payment, received_amount, paid_amount, status
            from `tabPayment Entry`
            where intended_sales_invoice = %s and docstatus = 0
            order by posting_date desc, creation desc
            """,
            (si_name,),
            as_dict=True,
        )

    # Prefer submitted first, then drafts
    return submitted + drafts


@frappe.whitelist()
def get_sales_invoices_for_payment_entry(pe_name: str):
    """Return Sales Invoices linked to a Payment Entry.
    Includes:
      - Submitted SIs via Payment Entry Reference rows
      - Also the intended SI if your PE has custom field `intended_sales_invoice`
    Returns: [{name, docstatus, status, posting_date, customer, patient}] (patient if SI has it)
    """
    if not pe_name:
        return []

    # SIs linked via references
    via_refs = frappe.db.sql(
        """
        select si.name, si.docstatus, si.status, si.posting_date, si.customer,
               si.patient
        from `tabPayment Entry Reference` per
        join `tabSales Invoice` si on si.name = per.reference_name
        where per.parent = %s and per.reference_doctype = 'Sales Invoice'
        order by si.posting_date desc, si.creation desc
        """,
        (pe_name,),
        as_dict=True,
    )

    # Optional: intended_sales_invoice (Draft PEs typically)
    extra = []
    if frappe.get_meta("Payment Entry").has_field("intended_sales_invoice"):
        intended = frappe.db.get_value(
            "Payment Entry", pe_name, "intended_sales_invoice"
        )
        if intended and frappe.db.exists("Sales Invoice", intended):
            row = frappe.db.get_value(
                "Sales Invoice",
                intended,
                ["name", "docstatus", "status", "posting_date", "customer", "patient"],
                as_dict=True,
            )
            if row:
                # avoid duplicate if already in via_refs
                if not any(r["name"] == row["name"] for r in via_refs):
                    extra.append(row)

    return via_refs + extra
