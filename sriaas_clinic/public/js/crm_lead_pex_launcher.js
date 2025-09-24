// CRM Lead: Add PEX launcher
frappe.ui.form.on('CRM Lead', {
  refresh(frm) {
    // Mount only if the HTML field exists
    const html_field = frm.get_field('sr_lead_pex_launcher_html');
    if (!html_field) return;

    const $w = html_field.$wrapper;
    if ($w.hasClass('pex-mounted')) return;
    $w.addClass('pex-mounted');

    // Render launcher UI
    $w.html(`
      <div class="flex" style="align-items:center; justify-content:space-between; margin:12px 0;">
        <div>
          <h4 style="margin:0 0 4px;">Create Patient Encounter (PEX)</h4>
          <div class="text-muted">Open full PE with all fields, pre-filled.</div>
        </div>
        <div>
          <button class="btn btn-primary" id="open_full_pe">Open Full PE</button>
        </div>
      </div>
    `);

    // Button handler
    $w.find('#open_full_pe').on('click', () => {
      frappe.route_options = {
        __from_pex: 1,
        company: frm.doc.company || frappe.defaults.get_default('company'),
        practitioner: frm.doc.primary_healthcare_practitioner || '',        
        pex_copy_forward: $w.find('#pex_copy_forward').is(':checked') ? 1 : 0,
        pex_fill_draft: $w.find('#pex_fill_draft').is(':checked') ? 1 : 0,
        // fixed encounter type
        sr_encounter_type: "Order",
        // If you map Lead → Patient elsewhere, set patient here accordingly
        patient: frm.doc.name,
      };
      frappe.new_doc('Patient Encounter');
    });
  }
});
