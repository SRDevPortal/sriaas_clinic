// sriaas_clinic/public/js/pe_draft_invoice.js
// ------------------------------
// Draft Invoice UI for Patient Encounter (multi-payments only)
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
  // show for Order + (Online OR OPD). Allow empty place while user types.
  return type === 'order' && (place === 'online' || place === 'opd' || !place);
}

function toggle_draft_invoice_ui(frm) {
  // Tab visibility is controlled server-side via depends_on;
  // here we toggle inner sections/fields (multi-payments only)
  const show = is_order_for_any_place(frm);

  // Sections to show/hide.
  const sections = [
    'sr_items_list_sb',
    'enc_mmp_sb' // new section (Payments) that contains enc_multi_payments
  ];

  // Fields to show/hide. prefer the new multi-payments table
  const fields = [
    'sr_delivery_type',
    'sr_pe_order_items',
    'enc_multi_payments' // new table field (SR Multi Mode Payment)
  ];

  // Toggle sections (ignore missing fields)
  sections.forEach(f => {
    try { frm.toggle_display(f, show); } catch (e) { /* ignore if missing */ }
  });

  // Toggle fields (show new multi-payments when show=true)
  fields.forEach(f => {
    try { frm.toggle_display(f, show); } catch (e) { /* ignore if missing */ }
  });
}

function reset_draft_invoice_fields(frm) {
  // Clear once for new docs so user starts clean
  frm.set_value('sr_delivery_type', null);
  frm.set_value('sr_pe_order_items', []);
  // Clear new multi-payments table
  frm.set_value('enc_multi_payments', []);

  // No legacy single-advance fields are set anymore.

  toggle_draft_invoice_ui(frm);
}
