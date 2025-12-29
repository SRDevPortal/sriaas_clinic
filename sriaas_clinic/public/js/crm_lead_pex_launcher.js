// CRM Lead: Add PEX launcher + Patient Appointment launcher
frappe.ui.form.on('CRM Lead', {
  refresh(frm) {
    
    // =====================================================
    // 🔹 PEX Launcher
    // =====================================================
    const pex_field = frm.get_field('sr_lead_pex_launcher_html');
    if (pex_field) {
      const $w = pex_field.$wrapper;
      if (!$w.hasClass('pex-mounted')) {
        $w.addClass('pex-mounted');

        $w.html(`
          <div class="flex" style="align-items:center; justify-content:space-between; margin:12px 0;">
            <div>
              <h4 style="margin:0 0 4px;">Create Patient Encounter</h4>
              <div class="text-muted">Open full Patient Encounter with all fields, pre-filled.</div>
            </div>
            <div>
              <button class="btn btn-primary" id="open_full_pe">
                Create Encounter
              </button>
            </div>
          </div>
        `);

        $w.find('#open_full_pe').on('click', () => {
          frappe.route_options = {
            __from_pex: 1,
            company: frm.doc.company || frappe.defaults.get_default('company'),
            practitioner: frm.doc.primary_healthcare_practitioner || '',
            pex_copy_forward: $w.find('#pex_copy_forward').is(':checked') ? 1 : 0,
            pex_fill_draft: $w.find('#pex_fill_draft').is(':checked') ? 1 : 0,
            sr_encounter_type: "Order",
            patient: frm.doc.name, // mapping Lead → Patient if applicable
          };
          frappe.new_doc('Patient Encounter');
        });
      }
    }

    // =====================================================
    // 🔹 Patient Appointment Launcher
    // =====================================================
    const pa_field = frm.get_field('sr_lead_pa_launcher_html');
    if (pa_field) {
      const $w = pa_field.$wrapper;
      if (!$w.hasClass('pa-mounted')) {
        $w.addClass('pa-mounted');

        $w.html(`
          <div class="flex" style="align-items:center; justify-content:space-between; margin:12px 0;">
            <div>
              <h4 style="margin:0 0 4px;">Create Patient Appointment</h4>
              <div class="text-muted">Book appointment directly from this lead.</div>
            </div>
            <div>
              <button class="btn btn-primary" id="open_patient_appointment">
                Create Appointment
              </button>
            </div>
          </div>
        `);

        $w.find('#open_patient_appointment').on('click', () => {
          frappe.route_options = {
            company: frm.doc.company || frappe.defaults.get_default('company'),
            practitioner: frm.doc.primary_healthcare_practitioner || '',
            patient_name: frm.doc.lead_name || frm.doc.first_name || frm.doc.name,
            mobile_no: frm.doc.mobile_no,
            // sr_source_lead: frm.doc.name // optional: link back to CRM Lead
          };
          frappe.new_doc('Patient Appointment');
        });
      }
    }
  }
});
