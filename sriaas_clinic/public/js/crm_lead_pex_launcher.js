// CRM Lead: Add PEX launcher + Patient Appointment launcher
const SR_CRM_LEAD_META_FIELDS = [
  'sr_ip_address',
  'sr_vpn_status',
  'sr_landing_page',
  'sr_remote_location',
  'sr_user_agent',
  'sr_utm_source',
  'sr_utm_campaign',
  'sr_utm_campaign_id',
  'sr_gclid',
  'sr_utm_medium',
  'sr_utm_term',
  'sr_utm_adgroup_id',
  'sr_f_ad_id',
  'sr_f_ad_name',
  'sr_f_adset_id',
  'sr_f_adset_name',
  'sr_f_campaign_id',
  'sr_f_campaign_name',
  'sr_f_utm_medium',
  'sr_fbclid',
  'sr_w_source_id',
  'sr_w_source_url',
  'sr_w_ctwa_clid',
  'sr_w_team_id',
  'sr_w_team_user',
];

function get_crm_lead_meta_route_options(frm) {
  const meta_values = {};

  SR_CRM_LEAD_META_FIELDS.forEach((fieldname) => {
    meta_values[fieldname] = frm.doc[fieldname] || '';
  });

  return meta_values;
}

function apply_patient_encounter_route_options(doc, route_options) {
  Object.keys(route_options).forEach((fieldname) => {
    if (frappe.meta.has_field('Patient Encounter', fieldname)) {
      doc[fieldname] = route_options[fieldname];
    }
  });
}

function get_crm_lead_notes(frm) {
  const notes = [];

  if (frm.doc.sr_lead_message) {
    notes.push(`Lead Message:\n${frm.doc.sr_lead_message}`);
  }

  if (frm.doc.sr_lead_notes) {
    notes.push(`Lead Notes:\n${frm.doc.sr_lead_notes}`);
  }

  return notes.join('\n\n');
}

frappe.ui.form.on('CRM Lead', {
  refresh(frm) {
    if (!frm.is_new() && typeof window.sriaas_intercept_s3_attachments === 'function') {
      window.sriaas_intercept_s3_attachments(frm);
    }
    
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
          const meta_values = get_crm_lead_meta_route_options(frm);

          const pe_route_options = {
            __from_pex: 1,
            company: frm.doc.company || frappe.defaults.get_default('company'),
            practitioner: frm.doc.primary_healthcare_practitioner || '',
            pex_copy_forward: $w.find('#pex_copy_forward').is(':checked') ? 1 : 0,
            pex_fill_draft: $w.find('#pex_fill_draft').is(':checked') ? 1 : 0,
            sr_encounter_type: "Order",
            sr_encounter_source: frm.doc.source || '',
            sr_source_crm_lead: frm.doc.name || '',
            sr_notes: get_crm_lead_notes(frm),
            ...meta_values,
          };
          frappe.new_doc('Patient Encounter', pe_route_options, (doc) => {
            apply_patient_encounter_route_options(doc, pe_route_options);
          });
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
