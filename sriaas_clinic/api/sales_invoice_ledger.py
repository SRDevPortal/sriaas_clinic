import frappe


def repair_sales_invoice_ledger_links(doc, method=None):
    """Repair ledger rows when stale DocField metadata drops Dynamic Link values."""
    if doc.docstatus != 1:
        return

    if not _has_linked_gl_entries(doc):
        if not _has_unlinked_gl_entries(doc):
            doc.make_gl_entries()
        _link_unlinked_gl_entries(doc)

    if not _has_linked_payment_ledger_entries(doc):
        _link_unlinked_payment_ledger_entries(doc)


def _has_linked_gl_entries(doc):
    return frappe.db.exists(
        "GL Entry",
        {
            "voucher_type": doc.doctype,
            "voucher_no": doc.name,
            "is_cancelled": 0,
        },
    )


def _has_unlinked_gl_entries(doc):
    return bool(
        frappe.db.sql(
            """
            select name
            from `tabGL Entry`
            where voucher_type = %s
              and (voucher_no is null or voucher_no = '')
              and company = %s
              and posting_date = %s
              and ifnull(remarks, '') = %s
            limit 1
            """,
            (doc.doctype, doc.company, doc.posting_date, doc.get("remarks") or ""),
        )
    )


def _link_unlinked_gl_entries(doc):
    frappe.db.sql(
        """
        update `tabGL Entry`
        set voucher_no = %s,
            against_voucher = case
                when account = %s and (against_voucher is null or against_voucher = '') then %s
                else against_voucher
            end
        where voucher_type = %s
          and (voucher_no is null or voucher_no = '')
          and company = %s
          and posting_date = %s
          and ifnull(remarks, '') = %s
        """,
        (
            doc.name,
            doc.get("debit_to"),
            doc.name,
            doc.doctype,
            doc.company,
            doc.posting_date,
            doc.get("remarks") or "",
        ),
    )


def _has_linked_payment_ledger_entries(doc):
    return frappe.db.exists(
        "Payment Ledger Entry",
        {
            "voucher_type": doc.doctype,
            "voucher_no": doc.name,
            "delinked": 0,
        },
    )


def _link_unlinked_payment_ledger_entries(doc):
    frappe.db.sql(
        """
        update `tabPayment Ledger Entry`
        set voucher_no = %s,
            against_voucher_no = %s,
            party_type = 'Customer',
            party = %s
        where voucher_type = %s
          and (voucher_no is null or voucher_no = '')
          and company = %s
          and posting_date = %s
          and account = %s
          and ifnull(remarks, '') = %s
          and delinked = 0
        """,
        (
            doc.name,
            doc.name,
            doc.customer,
            doc.doctype,
            doc.company,
            doc.posting_date,
            doc.debit_to,
            doc.get("remarks") or "",
        ),
    )
