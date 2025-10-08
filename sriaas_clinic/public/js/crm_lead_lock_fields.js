// Client Script on "CRM Lead"
frappe.ui.form.on('CRM Lead', {
  refresh(frm) {
    const is_new = frm.is_new();
    const is_tl  = frappe.user.has_role('Team Leader');
    const is_sys = frappe.user.has_role('System Manager') || frappe.session.user === 'Administrator';
    if (is_sys) return; // <-- never lock for privileged

    const lock = (f) => frm.set_df_property(f, 'read_only', !(is_new && is_tl));
    ['source','sr_lead_pipeline','mobile_no'].forEach(lock);
    // lead_owner stays governed server-side
  }
});
