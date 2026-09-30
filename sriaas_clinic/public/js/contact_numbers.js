/* Explicit masked-number maintenance; raw stored values never enter this dialog. */
(() => {
  const api = 'sriaas_clinic.api.contact_numbers.';
  async function manage(frm) {
    if (frm.is_dirty() && frm.doctype !== 'Patient Encounter') {
      frappe.msgprint(__('Save your current changes before managing contact numbers.'));
      return;
    }
    const doctype = frm.doctype === 'Patient Encounter' ? 'Patient' : frm.doctype;
    const name = frm.doctype === 'Patient Encounter' ? frm.doc.patient : frm.doc.name;
    if (!name) return;
    const state = (await frappe.call({method: api + 'get_context', args: {doctype, name}})).message;
    const options = [{label: __('Keep current selection'), value: ''}, ...state.rows.map((row, i) => ({
      label: `${i + 1}. ${row.number}${row.primary_mobile ? ' (Primary Mobile)' : ''}${row.primary_phone ? ' (Primary Phone)' : ''}`,
      value: row.id
    }))];
    if (state.can_add) options.push({label: __('New customer-provided number'), value: '@new:0'});
    const dialog = new frappe.ui.Dialog({
      title: __('Manage Contact Numbers'),
      fields: [
        {fieldtype: 'HTML', fieldname: 'existing'},
        {fieldtype: 'Data', fieldname: 'number', label: __('Add customer-provided number'), hidden: !state.can_add,
          description: __('Previously stored numbers remain masked. The new number is masked after saving.')},
        {fieldtype: 'Select', fieldname: 'primary_mobile', label: __('Primary Mobile'), options, hidden: !state.can_primary},
        {fieldtype: 'Select', fieldname: 'primary_phone', label: __('Primary Phone'), options, hidden: !state.can_primary}
      ],
      primary_action_label: __('Save contact numbers'),
      async primary_action(values) {
        if (!values.number && !values.primary_mobile && !values.primary_phone) return;
        dialog.get_primary_btn().prop('disabled', true);
        try {
          await frappe.call({method: api + 'update_numbers', args: {
            doctype, name, modified: state.modified,
            additions: values.number ? [values.number] : [],
            primary_mobile: values.primary_mobile || null,
            primary_phone: values.primary_phone || null
          }});
          dialog.set_value('number', '');
          dialog.hide();
          if (frm.doctype === 'Patient Encounter' && (frm.is_new() || frm.is_dirty())) {
            await frm.trigger('patient');
          } else { await frm.reload_doc(); }
          frappe.show_alert({message: __('Contact numbers updated'), indicator: 'green'});
        } finally { dialog.get_primary_btn().prop('disabled', false); }
      }
    });
    dialog.fields_dict.existing.$wrapper.text(state.rows.map((row, i) =>
      `${i + 1}. ${row.number}${row.primary_mobile ? ' - Primary Mobile' : ''}${row.primary_phone ? ' - Primary Phone' : ''}`
    ).join(' | '));
    dialog.show();
    if (!state.can_add && !state.can_primary) dialog.get_primary_btn().hide();
  }
  for (const doctype of ['Patient', 'Contact', 'Patient Encounter']) {
    frappe.ui.form.on(doctype, {
      refresh(frm) {
        if ((doctype === 'Patient Encounter' && frm.doc.patient) || (doctype !== 'Patient Encounter' && !frm.is_new())) {
          frm.add_custom_button(__('Manage Contact Numbers'), () => manage(frm));
        }
      }
    });
  }
  frappe.ui.form.on('Patient Encounter', {
    patient(frm) {
      if (frm.doc.patient) frm.add_custom_button(__('Manage Contact Numbers'), () => manage(frm));
    }
  });
  frappe.ui.form.on('Patient', {
    async refresh(frm) {
      if (!frm.is_new()) return;
      const policy = (await frappe.call({method: 'sriaas_clinic.api.patient_intake.get_context',
        args: {source: frm.doc.__privacy_source_lead || null}})).message;
      if (!frm.is_new() || !policy.add_contact_numbers) return;
      frm.add_custom_button(__('Add Customer-provided Numbers'), () => frappe.prompt([
        {fieldname: 'mobile', fieldtype: 'Data', label: __('Add Mobile'), default: frm.doc.__privacy_add_mobile || ''},
        {fieldname: 'primary_mobile', fieldtype: 'Check', label: __('Make primary Mobile'), hidden: !policy.change_primary_number,
          default: frm.doc.__privacy_primary_mobile || 0},
        {fieldname: 'phone', fieldtype: 'Data', label: __('Add Phone'), default: frm.doc.__privacy_add_phone || ''},
        {fieldname: 'primary_phone', fieldtype: 'Check', label: __('Make primary Phone'), hidden: !policy.change_primary_number,
          default: frm.doc.__privacy_primary_phone || 0}
      ], values => {
        for (const key of ['mobile', 'phone']) {
          frm.doc['__privacy_add_' + key] = values[key] || '';
          frm.doc['__privacy_primary_' + key] = values['primary_' + key] || 0;
        }
        frm.dirty();
        frappe.show_alert(__('New contact numbers will be added when you save the Patient.'));
      }, __('Customer-provided Numbers')));
    }
  });
})();
