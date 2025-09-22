// Payment Entry — pick outstanding invoices into references table
// Shows a dialog with outstanding invoices when Party is selected (non–Internal Transfer)

frappe.ui.form.on('Payment Entry', {
  party(frm) {
    if (
      frm.doc.party_type &&
      frm.doc.party &&
      frm.doc.payment_type !== "Internal Transfer"
    ) {
      frappe.call({
        method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_outstanding_reference_documents",
        args: {
          args: {
            party_type: frm.doc.party_type,
            party: frm.doc.party,
            payment_type: frm.doc.payment_type,
            company: frm.doc.company,
            party_account: frm.doc.paid_from || frm.doc.paid_to,
            party_account_currency: frm.doc.paid_from_account_currency || frm.doc.paid_to_account_currency,
            outstanding_amt_greater_than_zero: 1
          }
        },
        callback(r) {
          const rows = (r && r.message) || [];
          if (!Array.isArray(rows) || rows.length === 0) return;

          const d = new frappe.ui.Dialog({
            title: __("Select Invoices"),
            fields: [
              {
                fieldtype: "Table",
                fieldname: "references",
                label: __("Outstanding Invoices"),
                cannot_add_rows: true,
                in_place_edit: true,
                data: rows,
                get_data: () => rows,
                fields: [
                  { fieldtype: "Data",     fieldname: "voucher_no",        label: __("Invoice No"),  in_list_view: true, read_only: 1 },
                  { fieldtype: "Data",     fieldname: "voucher_type",      label: __("Type"),        in_list_view: true, read_only: 1 },
                  { fieldtype: "Date",     fieldname: "posting_date",      label: __("Posting Date"),in_list_view: true, read_only: 1 },
                  { fieldtype: "Date",     fieldname: "due_date",          label: __("Due Date"),    in_list_view: true, read_only: 1 },
                  { fieldtype: "Currency", fieldname: "invoice_amount",    label: __("Invoice Amt"), in_list_view: true, read_only: 1 },
                  { fieldtype: "Currency", fieldname: "outstanding_amount",label: __("Outstanding"), in_list_view: true, read_only: 1 },
                  { fieldtype: "Currency", fieldname: "allocated_amount",  label: __("Allocate"),    in_list_view: true }
                ]
              }
            ],
            primary_action_label: __("Add"),
            primary_action(values) {
              const selected_rows = d.fields_dict.references.grid.get_selected_children() || [];
              selected_rows.forEach(row => {
                const ref = frm.add_child("references");
                ref.reference_doctype   = row.voucher_type;
                ref.reference_name      = row.voucher_no;
                ref.due_date            = row.due_date;
                ref.posting_date        = row.posting_date;
                ref.total_amount        = row.invoice_amount;
                ref.outstanding_amount  = row.outstanding_amount;
                // default allocate full outstanding (user can edit later)
                ref.allocated_amount    = row.allocated_amount || row.outstanding_amount;
              });
              frm.refresh_field("references");
              d.hide();
            }
          });

          d.show();
        }
      });
    }
  }
});
