// public/js/sales_invoice_draft_payment.js
frappe.ui.form.on('Sales Invoice', {
  onload_post_render(frm) {
    if (frm.is_new()) {
      frm.set_value('si_dp_paid_amount', 0);
      frm.set_value('si_dp_mode_of_payment', null);
      frm.set_value('si_dp_reference_no', null);
      frm.set_value('si_dp_reference_date', null);
      frm.set_value('si_dp_payment_proof', null);
    }
  },
});
