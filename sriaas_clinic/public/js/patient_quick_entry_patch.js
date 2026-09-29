/* sriaas_clinic/public/js/patient_quick_entry_patch.js
   Patch Healthcare's Patient Quick Entry to use an SR State link picker
   and always mirror it into the legacy `state` text submitted to the server.
*/
(function patchPatientQE() {
  const tryPatch = () => {
    const QE = frappe.ui.form && frappe.ui.form.PatientQuickEntryForm;
    if (!QE || !QE.prototype) return setTimeout(tryPatch, 60);
    if (QE.__sr_state_patched__) return;
    QE.__sr_state_patched__ = true;

    // --- 1) Replace "state" with "sr_state_link" (Link → SR State); keep hidden legacy "state"
    const orig_get = QE.prototype.get_standard_fields;
    QE.prototype.get_standard_fields = function () {
      const fields = orig_get.call(this) || [];
      const idx = fields.findIndex(f => f.fieldname === "state");
      if (idx > -1) {
        // show link to user
        fields.splice(idx, 1, {
          label: __("State/Province"),
          fieldname: "sr_state_link",
          fieldtype: "Link",
          options: "SR State"
        });
        // keep legacy "state" so payload includes it; hide from UI
        fields.splice(idx + 1, 0, {
          label: __("State Legacy"),
          fieldname: "state",
          fieldtype: "Data",
          hidden: 1
        });
      }
      return fields;
    };

    // --- 2) Wire behaviors after the dialog renders
    const orig_render = QE.prototype.render_dialog;
    QE.prototype.render_dialog = function () {
      orig_render.call(this);

      const d = this.dialog;
      const f = d.fields_dict || {};

      // Mirror link → legacy text
      const set_legacy = () => d.set_value("state", d.get_value("sr_state_link") || "");

      // Filter SR State by Country (adjust fieldname if your SR State uses a different link)
      if (f.sr_state_link) {
        f.sr_state_link.get_query = () => {
          const filters = {};
          const country = d.get_value("country");
          if (country) filters.sr_country = country;
          return { filters };
        };

        // Required only when Country = India
        const refresh_reqd = () => {
          const is_india = /india/i.test(String(d.get_value("country") || ""));
          f.sr_state_link.df.reqd = is_india;
          f.sr_state_link.refresh();
        };
        refresh_reqd();

        // When Country changes, update required + refresh query next open
        if (f.country) {
          const orig_onchange = f.country.df.onchange;
          f.country.df.onchange = () => {
            orig_onchange && orig_onchange();
            refresh_reqd();
            f.sr_state_link._filters = null; // force re-query on next open
          };
        }

        // Initial sync on open (covers defaulted Country=India)
        set_legacy();

        // Mirror on link change too
        const orig_change = f.sr_state_link.df.change;
        f.sr_state_link.df.change = () => {
          orig_change && orig_change();
          set_legacy();
        };
      }

      // Ensure mirror happens right before Save even if user didn't touch the link
      const $save = d.get_primary_btn && d.get_primary_btn();
      if ($save) {
        $save.off("click._sr_state_guard").on("click._sr_state_guard", set_legacy);
      }
    };
  };

  tryPatch();
})();


// Patient intake keeps source numbers on the server, including Edit Full Form.
(function patchPatientIntake() {
  const method = 'sriaas_clinic.api.patient_intake.get_context';
  const sourceKey = '__privacy_source_lead';
  const fetchContext = async source => (await frappe.call({method, args: {source: source || null}})).message;
  const canEnter = policy => policy.edit_original || policy.enter_new_numbers;
  const tryPatch = () => {
    const QE = frappe.ui.form?.PatientQuickEntryForm;
    if (!QE) return setTimeout(tryPatch, 60);
    if (QE.__privacy_intake_patched) return;
    QE.__privacy_intake_patched = true;
    const setup = QE.prototype.setup;
    QE.prototype.setup = async function () {
      // Existing records keep their existing save/visibility policy.
      if (this.doc?.name && !this.doc.__islocal) return setup.call(this);
      const link = frappe._from_link;
      const caller = link?.doc || link?.frm?.doc;
      const source = this.doc?.[sourceKey] ||
        (link?.df?.fieldname === 'patient' && caller?.doctype === 'Patient Encounter'
          ? caller.sr_source_crm_lead : null);
      this.intakePolicy = await fetchContext(source);
      if (this.intakePolicy.existing_patient && link) {
        frappe.ui.form.update_calling_link({doctype: 'Patient', name: this.intakePolicy.existing_patient});
        frappe.quick_entry = null;
        return this;
      }
      return setup.call(this);
    };
    const getFields = QE.prototype.get_standard_fields;
    QE.prototype.get_standard_fields = function () {
      const fields = getFields.call(this).map(df => ({...df}));
      const policy = this.intakePolicy;
      if (!policy?.enabled) return fields;
      const source = policy.source;
      if (!fields.some(df => df.fieldname === 'phone')) {
        const mobileIndex = fields.findIndex(df => df.fieldname === 'mobile');
        fields.splice(mobileIndex + 1, 0, {fieldname: 'phone', label: __('Phone'), fieldtype: 'Data', options: 'Phone'});
      }
      for (const df of fields) {
        if (['mobile', 'phone'].includes(df.fieldname)) {
          df.hidden = !!source || !canEnter(policy);
          df.reqd = df.fieldname === 'mobile' && !df.hidden ? 1 : 0;
        }
      }
      fields.push({fieldtype: 'Section Break', label: __('Number Source')},
        {fieldname: sourceKey, fieldtype: 'Link', options: 'CRM Lead', label: __('Source CRM Lead'),
          default: source || '', reqd: !canEnter(policy),
          description: __('Use a lead you can access, or leave blank to enter a newly supplied number if permitted.')},
        {fieldname: 'mask_mobile', fieldtype: 'Data', label: __('Masked Mobile'), read_only: 1,
          default: policy.mask_mobile || '', description: __('The original number will be copied from the source lead when you save.')},
        {fieldname: 'mask_phone', fieldtype: 'Data', label: __('Masked Phone'), read_only: 1,
          default: policy.mask_phone || ''});
      return fields;
    };
    const render = QE.prototype.render_dialog;
    QE.prototype.render_dialog = function () {
      const policy = this.intakePolicy;
      if (policy?.enabled) {
        this.doc[sourceKey] = policy.source || '';
        for (const [key, value] of Object.entries(policy.defaults || {})) {
          if (!this.doc[key] && value) this.doc[key] = value;
        }
        this.doc.mask_mobile = policy.mask_mobile || '';
        this.doc.mask_phone = policy.mask_phone || '';
      }
      render.call(this);
      if (!policy?.enabled) return;
      const dialog = this.dialog;
      // Frappe overlays Patient metadata while constructing controls. Apply
      // intake visibility to the finished dialog, not shared DocField metadata.
      for (const field of ['mobile', 'phone']) {
        if (dialog.fields_dict[field]) {
          dialog.set_df_property(field, 'hidden', !!policy.source || !canEnter(policy));
          dialog.set_df_property(field, 'reqd', field === 'mobile' && !policy.source && canEnter(policy) ? 1 : 0);
        }
      }
      for (const field of ['mask_mobile', 'mask_phone']) {
        dialog.set_df_property(field, 'hidden', 0);
        dialog.set_df_property(field, 'read_only', 1);
      }
      dialog.fields_dict[sourceKey].df.onchange = async () => {
        const source = dialog.doc[sourceKey];
        this.intakeLoading = true;
        dialog.get_primary_btn().prop('disabled', true);
        try {
          const next = await fetchContext(source);
          if (dialog.doc[sourceKey] !== source) return;
          if (next.existing_patient) {
            frappe.msgprint(__('This lead already has a Patient. Select the existing Patient: {0}', [next.existing_patient]));
            return;
          }
          this.intakePolicy = next;
          dialog.doc[sourceKey] = source || '';
          for (const field of ['mobile', 'phone']) {
            if (dialog.fields_dict[field]) {
              dialog.set_df_property(field, 'hidden', !!source || !canEnter(next));
              dialog.set_df_property(field, 'reqd', field === 'mobile' && !source && canEnter(next) ? 1 : 0);
              if (source) { dialog.set_value(field, ''); delete dialog.doc[field]; }
            }
          }
          dialog.set_value('mask_mobile', next.mask_mobile || '');
          dialog.set_value('mask_phone', next.mask_phone || '');
          for (const [key, value] of Object.entries(next.defaults || {})) {
            if (dialog.fields_dict[key] && !dialog.get_value(key) && value) dialog.set_value(key, value);
          }
          this.intakeLoading = false;
          dialog.get_primary_btn().prop('disabled', false);
        } catch (error) {
          // Leave Save disabled until a valid source/context has been selected.
          this.intakeLoading = true;
        }
      };
    };
    const insert = QE.prototype.insert;
    QE.prototype.insert = function () {
      if (this.intakeLoading) { this.dialog.working = false; return Promise.resolve(); }
      return insert.call(this);
    };
  };
  tryPatch();

  frappe.ui.form.on('Patient', {
    async refresh(frm) {
      if (!frm.is_new()) return;
      const source = frm.doc[sourceKey];
      const policy = await fetchContext(source);
      if (!frm.is_new() || frm.doc[sourceKey] !== source || !policy.enabled) return;
      for (const field of ['mobile', 'phone']) {
        const show = !source && canEnter(policy);
        frm.toggle_display(field, show);
        frm.set_df_property(field, 'read_only', show ? 0 : 1);
        frm.set_df_property(field, 'reqd', field === 'mobile' && show ? 1 : 0);
      }
      for (const [field, value] of Object.entries({mask_mobile: policy.mask_mobile, mask_phone: policy.mask_phone})) {
        frm.toggle_display(field, !!source);
        frm.doc[field] = value || '';
        frm.refresh_field(field);
      }
      frm.set_intro(source ? __('Numbers will be copied from the source CRM Lead when saved.') :
        (!canEnter(policy) ? __('Select a source CRM Lead to create this Patient without entering its hidden number.') : ''));
      frm.add_custom_button(__('Use CRM Lead'), () => frappe.prompt(
        [{fieldname: 'source', fieldtype: 'Link', options: 'CRM Lead', label: __('Source CRM Lead'), reqd: 1}],
        async values => {
          const next = await fetchContext(values.source);
          if (next.existing_patient) return frappe.set_route('Form', 'Patient', next.existing_patient);
          frm.doc[sourceKey] = values.source;
          delete frm.doc.mobile; delete frm.doc.phone;
          for (const [key, value] of Object.entries(next.defaults || {})) {
            if (!frm.doc[key] && value) frm.doc[key] = value;
          }
          frm.refresh();
        }, __('Patient Number Source')));
    }
  });
})();
