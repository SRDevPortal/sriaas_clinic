// Loaded Client Script via hooks doctype_js for on "CRM Lead"
frappe.ui.form.on('CRM Lead', {
  refresh(frm) {
    const is_new = frm.is_new();

    frappe.call({
      method: 'sriaas_clinic.api.crm_lead.controller.get_crm_lead_role_context',
      callback(r) {
        const context = r.message || {};
        if (context.is_privileged) return;

        // Lock field unless this is a new lead and the current user is a configured Team Leader.
        const is_tl = !!context.has_team_leader_role;
        const lock = (f) => frm.set_df_property(f, 'read_only', !(is_new && is_tl));
        (context.lock_after_insert_fields || []).forEach(lock);
      }
    });
  }
});
