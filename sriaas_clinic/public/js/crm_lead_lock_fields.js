// Loaded Client Script via hooks doctype_js for on "CRM Lead"
frappe.ui.form.on('CRM Lead', {
  refresh(frm) {
    const is_new = frm.is_new();
    const is_tl  = frappe.user.has_role('Team Leader');
    const is_sys = frappe.user.has_role('System Manager') || frappe.session.user === 'Administrator';
    if (is_sys) return; // never lock for privileged

    // lock field unless: it's new AND TL is creating
    const lock = (f) => frm.set_df_property(f, 'read_only', !(is_new && is_tl));
    ['sr_lead_pipeline','sr_lead_platform','source','mobile_no'].forEach(lock);

    // 'lead_owner' is enforced server-side; TL permissions at permlevel 2 via RPM
  }
});
