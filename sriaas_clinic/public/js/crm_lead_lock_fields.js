// Lock a few fields after first save. TL can edit them only while creating.
frappe.ui.form.on('CRM Lead', {
  refresh(frm) {
    const is_new = frm.is_new();
    const is_tl  = frappe.user.has_role('Team Leader');

    const lock = (f) => frm.set_df_property(f, 'read_only', !(is_new && is_tl));
    ['source', 'sr_lead_pipeline', 'mobile_no'].forEach(lock);
  }
});
