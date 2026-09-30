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
    const optionsFor = (primary) => {
      const current = state.rows.find(row => row[primary]);
      const options = [{label: current ? `${current.number} (${__('current')})` : __('Not set'), value: ''}];
      if (state.can_add) options.push({label: __('New number'), value: '@new:0'});
      const counts = {};
      state.rows.forEach(row => { counts[row.number] = (counts[row.number] || 0) + 1; });
      state.rows.forEach((row, i) => {
        if (row !== current) options.push({
          label: row.number + (counts[row.number] > 1 ? ` (${__('row')} ${i + 1})` : ''), value: row.id
        });
      });
      return options;
    };
    let dialog;
    const exclusiveNew = (field, other) => () => {
      if (!state.bypass_privacy && dialog && dialog.get_value(field) === '@new:0' && dialog.get_value(other) === '@new:0') {
        dialog.set_value(other, '');
      }
    };
    dialog = new frappe.ui.Dialog({
      title: __('Contact Numbers'),
      fields: [
        {fieldtype: 'Data', fieldname: 'number', label: __('New number'), hidden: !state.can_add,
          placeholder: __('Enter mobile or phone')},
        {fieldtype: 'Section Break'},
        {fieldtype: 'Select', fieldname: 'primary_mobile', label: __('Primary mobile'),
          options: optionsFor('primary_mobile'), default: '', read_only: !state.can_primary,
          onchange: exclusiveNew('primary_mobile', 'primary_phone')},
        {fieldtype: 'Column Break'},
        {fieldtype: 'Select', fieldname: 'primary_phone', label: __('Primary phone'),
          options: optionsFor('primary_phone'), default: '', read_only: !state.can_primary,
          onchange: exclusiveNew('primary_phone', 'primary_mobile')},
        {fieldtype: 'Section Break'},
        {fieldtype: 'HTML', fieldname: 'privacy_note'}
      ],
      secondary_action_label: __('Cancel'),
      secondary_action() { dialog.hide(); },
      primary_action_label: __('Save'),
      async primary_action(values) {
        if (!values.number && !values.primary_mobile && !values.primary_phone) return;
        if ((values.primary_mobile === '@new:0' || values.primary_phone === '@new:0') && !values.number) {
          frappe.msgprint(__('Enter the new customer-provided number first.'));
          return;
        }
        if (!state.bypass_privacy && values.primary_mobile === '@new:0' && values.primary_phone === '@new:0') {
          frappe.msgprint(__('Choose Primary mobile or Primary phone, not both.'));
          return;
        }
        dialog.get_primary_btn().prop('disabled', true);
        try {
          await frappe.call({method: api + 'update_numbers', args: {
            doctype, name, modified: state.modified,
            additions: values.number ? [values.number] : [],
            ...(values.primary_mobile ? {primary_mobile: values.primary_mobile} : {}),
            ...(values.primary_phone ? {primary_phone: values.primary_phone} : {})
          }});
          dialog.set_value('number', '');
          dialog.hide();
          if (frm.doctype === 'Patient Encounter' && (frm.is_new() || frm.is_dirty())) {
            await frm.trigger('patient');
          } else { await frm.reload_doc(); }
          frappe.show_alert({message: __('Contact numbers updated'), indicator: 'green'});
        } catch (error) {
          // Frappe displays server messages; keep the dialog open for correction.
          if (!error?.responseJSON?._server_messages) {
            frappe.msgprint(__('Could not update contact numbers. Check your selection and try again.'));
          }
        } finally { dialog.get_primary_btn().prop('disabled', false); }
      }
    });
    dialog.fields_dict.privacy_note.$wrapper.text(state.bypass_privacy ? '' : __('Saved numbers stay masked.'))
      .css({color: 'var(--text-muted)', fontSize: '12px'});
    dialog.$wrapper.find('.modal-dialog').css('max-width', '540px');
    dialog.$wrapper.find('.form-section').css({marginTop: '0', paddingTop: '0', paddingBottom: '0', borderTop: '0'});
    dialog.show();
    if (!state.can_add && !state.can_primary) dialog.get_primary_btn().hide();
  }
  async function refresh_number_button(frm) {
    const label = __('Update Contact Numbers');
    frm.remove_custom_button(label);
    const request = (frm.__number_button_request || 0) + 1;
    frm.__number_button_request = request;
    const doctype = frm.doctype === 'Patient Encounter' ? 'Patient' : frm.doctype;
    const name = frm.doctype === 'Patient Encounter' ? frm.doc.patient : (!frm.is_new() && frm.doc.name);
    if (!name) return;
    try {
      const {message: actions} = await frappe.call({method: api + 'get_actions', args: {doctype, name}});
      if (request !== frm.__number_button_request) return;
      if (actions?.can_add || actions?.can_primary) {
        frm.add_custom_button(label, () => manage(frm));
      }
    } catch (error) {
      // Leave the action hidden when permissions cannot be established.
    }
  }
  for (const doctype of ['Patient', 'Contact', 'Patient Encounter']) {
    frappe.ui.form.on(doctype, {refresh: refresh_number_button});
  }
  frappe.ui.form.on('Patient Encounter', {patient: refresh_number_button});
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
