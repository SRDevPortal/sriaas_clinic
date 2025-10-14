frappe.ui.form.on('Patient Encounter', {
  refresh(frm) {
    // just toggle visibility; no reset on existing docs
    toggle_draft_invoice_ui(frm);
  },

  onload_post_render(frm) {
    toggle_draft_invoice_ui(frm);

    // if it's a brand-new Encounter, start clean once
    if (frm.is_new()) {
      reset_draft_invoice_fields(frm);
      frm.refresh_field('sr_pe_order_items');
    }
  },

  // When type changes:
  // - if NEW doc => reset (fresh start)
  // - if EXISTING doc => only toggle, don't wipe user data
  sr_encounter_type(frm) {
    const is_new = frm.is_new();
    toggle_draft_invoice_ui(frm);
    if (is_new) {
      reset_draft_invoice_fields(frm);
      frm.refresh_field('sr_pe_order_items');
    }
  },
});

function toggle_draft_invoice_ui(frm) {
  const is_order = (frm.doc.sr_encounter_type || '').toLowerCase() === 'order';

  // keep the tab visible; toggle the contents
  const sections = ['sr_items_list_sb', 'sr_advance_payment_sb', 'sr_payment_receipt_sb'];
  const fields = [
    'sr_delivery_type',
    'sr_pe_order_items',
    'sr_pe_mode_of_payment',
    'sr_pe_paid_amount',
    'sr_pe_payment_reference_no',
    'sr_pe_payment_reference_date',
    // 'sr_pe_payment_proof',
  ];

  [...sections, ...fields].forEach(f => frm.toggle_display(f, is_order));
}

function reset_draft_invoice_fields(frm) {
  const is_order = (frm.doc.sr_encounter_type || '').toLowerCase() === 'order';

  // always clear everything once for new docs,
  // then (optionally) user can add items if type == Order
  frm.set_value('sr_delivery_type', null);
  frm.set_value('sr_pe_order_items', []);
  frm.set_value('sr_pe_mode_of_payment', null);
  frm.set_value('sr_pe_paid_amount', 0);
  frm.set_value('sr_pe_payment_reference_no', null);
  frm.set_value('sr_pe_payment_reference_date', null);
  // frm.set_value('sr_pe_payment_proof', null);

  // make sure UI matches current type after clearing
  toggle_draft_invoice_ui(frm);
}
