// crm_lead_disposition_filter.js

// --- Lead Disposition rules for CRM Lead (app-bundled) ---
frappe.ui.form.on('CRM Lead', {
  refresh(frm) {
    frm.trigger('apply_lead_disposition_rules');
  },

  status(frm) {
    // Clear on status change
    if (frm.doc.sr_lead_disposition) {
      frm.set_value('sr_lead_disposition', null);
    }
    frm.trigger('apply_lead_disposition_rules');
  },

  apply_lead_disposition_rules(frm) {
    const status = (frm.doc.status || '').trim();

    // If no status, hide + not required
    if (!status) {
      frm.toggle_display('sr_lead_disposition', false);
      frm.toggle_reqd('sr_lead_disposition', false);
      return;
    }

    // Keep query in sync with chosen status
    frm.set_query('sr_lead_disposition', () => ({
      filters: {
        sr_lead_status: status,  // field on SR Lead Disposition
        is_active: 1
      }
    }));

    // Check if any dispositions exist for this status
    frappe.db.count('SR Lead Disposition', {
      filters: { sr_lead_status: status, is_active: 1 }
    }).then(count => {
      const show = count > 0;

      // Show/hide
      frm.toggle_display('sr_lead_disposition', show);

      // Make mandatory only when options exist
      frm.toggle_reqd('sr_lead_disposition', show);

      // If hiding, clear any stale value
      if (!show && frm.doc.sr_lead_disposition) {
        frm.set_value('sr_lead_disposition', null);
      }
    });
  }
});
