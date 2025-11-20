// sriaas_clinic/public/js/pe_draft_invoice.js
// ------------------------------
// Draft Invoice UI for Patient Encounter
// ------------------------------
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

  // Also react when place changes
  sr_encounter_place(frm) {
    const is_new = frm.is_new();
    toggle_draft_invoice_ui(frm);
    if (is_new) {
      reset_draft_invoice_fields(frm);
      frm.refresh_field('sr_pe_order_items');
    }
  },
});

function is_order_for_any_place(frm) {
  const type  = (frm.doc.sr_encounter_type  || '').toLowerCase();
  const place = (frm.doc.sr_encounter_place || '').toLowerCase();
  // show for Order + (Online OR OPD)
  return type === 'order' && (place === 'online' || place === 'opd' || !place);
  // note: we allow !place (empty) to avoid hiding UI while user types — remove "|| !place" if you don't want that
}

function toggle_draft_invoice_ui(frm) {
  // Tab visibility is controlled server-side via depends_on;
  // here we only toggle inner sections/fields
  const show = is_order_for_any_place(frm);

  // Sections to show/hide.
  const sections = [
    'sr_items_list_sb',
    // 'sr_advance_payment_sb', <-- old, intentionally not shown by default
    // 'sr_payment_receipt_sb',  <-- old, intentionally not shown by default
    'enc_mmp_sb'                // new section (Payments) that contains enc_multi_payments
  ];

  // Fields to show/hide. prefer the new multi-payments table
  const fields = [
    'sr_delivery_type',
    'sr_pe_order_items',
    'enc_multi_payments',      // new table field (SR Multi Mode Payment)
    // keep old fields for backward compatibility but hidden in UI
    'sr_pe_mode_of_payment',
    'sr_pe_paid_amount',
    'sr_pe_payment_reference_no',
    'sr_pe_payment_reference_date',
    'sr_pe_payment_proof',
  ];

  // [...sections, ...fields].forEach(f => frm.toggle_display(f, show));

  // Toggle sections
  sections.forEach(f => {
    try { frm.toggle_display(f, show); } catch (e) { /* ignore if missing */ }
  });

  // Toggle fields (show new multi-payments when show=true; keep legacy fields hidden so user uses multi-payments)
  fields.forEach(f => {
    try {
      // For legacy single-advance fields we hide them to encourage multi-payments use.
      if (['sr_pe_mode_of_payment','sr_pe_paid_amount','sr_pe_payment_reference_no','sr_pe_payment_reference_date','sr_pe_payment_proof'].includes(f)) {
        // show legacy fields only when explicitly configured (you can flip this if you want them visible)
        frm.toggle_display(f, false);
      } else {
        frm.toggle_display(f, show);
      }
    } catch (e) { /* ignore missing fields */ }
  });
}

function reset_draft_invoice_fields(frm) {
  // Clear once for new docs so user starts clean
  frm.set_value('sr_delivery_type', null);
  frm.set_value('sr_pe_order_items', []);
  // Clear new multi-payments table
  frm.set_value('enc_multi_payments', []);
  // Also clear legacy single-advance fields (won't be shown, but safe to reset)
  frm.set_value('sr_pe_paid_amount', 0);
  frm.set_value('sr_pe_mode_of_payment', null);
  frm.set_value('sr_pe_payment_reference_no', null);
  frm.set_value('sr_pe_payment_reference_date', null);
  frm.set_value('sr_pe_payment_proof', null);

  toggle_draft_invoice_ui(frm);
}
