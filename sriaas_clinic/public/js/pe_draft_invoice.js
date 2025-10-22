frappe.ui.form.on('Patient Encounter', {
  refresh(frm) {
    toggle_draft_invoice_ui(frm);
  },

  onload_post_render(frm) {
    toggle_draft_invoice_ui(frm);

    // If brand-new Encounter, clear once
    if (frm.is_new()) {
      reset_draft_invoice_fields(frm);
      frm.refresh_field('sr_pe_order_items');
    }
  },

  // When type changes:
  sr_encounter_type(frm) {
    const is_new = frm.is_new();
    toggle_draft_invoice_ui(frm);
    if (is_new) {
      reset_draft_invoice_fields(frm);
      frm.refresh_field('sr_pe_order_items');
    }
  },

  // NEW: also react when place changes
  sr_encounter_place(frm) {
    const is_new = frm.is_new();
    toggle_draft_invoice_ui(frm);
    if (is_new) {
      reset_draft_invoice_fields(frm);
      frm.refresh_field('sr_pe_order_items');
    }
  },
});

function is_order_online(frm) {
  const type  = (frm.doc.sr_encounter_type  || '').toLowerCase();
  const place = (frm.doc.sr_encounter_place || '').toLowerCase();
  return type === 'order' && place === 'online';
}

function toggle_draft_invoice_ui(frm) {
  // Tab visibility is controlled server-side via depends_on;
  // here we only toggle inner sections/fields
  const show = is_order_online(frm);

  const sections = ['sr_items_list_sb', 'sr_advance_payment_sb', 'sr_payment_receipt_sb'];
  const fields = [
    'sr_delivery_type',
    'sr_pe_order_items',
    'sr_pe_mode_of_payment',
    'sr_pe_paid_amount',
    'sr_pe_payment_reference_no',
    'sr_pe_payment_reference_date',
    'sr_pe_payment_proof',
  ];

  [...sections, ...fields].forEach(f => frm.toggle_display(f, show));
}

function reset_draft_invoice_fields(frm) {
  // Clear once for new docs so user starts clean
  frm.set_value('sr_delivery_type', null);
  frm.set_value('sr_pe_order_items', []);
  frm.set_value('sr_pe_paid_amount', 0);
  frm.set_value('sr_pe_mode_of_payment', null);
  frm.set_value('sr_pe_payment_reference_no', null);
  frm.set_value('sr_pe_payment_reference_date', null);
  frm.set_value('sr_pe_payment_proof', null);

  toggle_draft_invoice_ui(frm);
}
