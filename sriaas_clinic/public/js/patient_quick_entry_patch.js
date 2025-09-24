/* Patch Healthcare's Patient Quick Entry to use SR State link
   and keep legacy `state` text in sync.
*/

(function patchPatientQE() {
  // wait until Healthcare's class is defined
  const tryPatch = () => {
    const QE = frappe.ui.form && frappe.ui.form.PatientQuickEntryForm;
    if (!QE || !QE.prototype || QE.__sr_state_patched__) {
      // try again shortly if class not loaded yet
      return setTimeout(tryPatch, 60);
    }
    QE.__sr_state_patched__ = true;

    // ---- 1) replace "state" (Data) with "sr_state_link" (Link → SR State)
    const orig_get = QE.prototype.get_standard_fields;
    QE.prototype.get_standard_fields = function () {
      const fields = orig_get.call(this);

      // find "State" (Data) in the right-hand Address column
      const idx = fields.findIndex((f) => f.fieldname === "state");
      if (idx > -1) {
        // replace with our link field (shown to the user)
        fields.splice(idx, 1, {
          label: __("State/Province"),
          fieldname: "sr_state_link",
          fieldtype: "Link",
          options: "SR State",          // your custom doctype
        });

        // keep a hidden "state" (Data) so payload still has the legacy field
        fields.splice(idx + 1, 0, {
          fieldname: "state",
          fieldtype: "Data",
          hidden: 0
        });
      }
      return fields;
    };

    // ---- 2) after dialog renders, wire behaviors: filter, require, and mirror
    const orig_render = QE.prototype.render_dialog;
    QE.prototype.render_dialog = function () {
      orig_render.call(this);

      const d = this.dialog;
      const f = d.fields_dict;

      // filter SR State by selected Country (your SR State has field `sr_country`)
      if (f.sr_state_link) {
        f.sr_state_link.get_query = () => {
          const filters = {};
          const country = d.get_value("country");
          if (country) filters.sr_country = country;
          return { filters };
        };

        // make link required only when country = India (to match your server rule)
        const refresh_reqd = () => {
          const is_india = String(d.get_value("country") || "").toLowerCase() === "india";
          f.sr_state_link.df.reqd = is_india;
          f.sr_state_link.refresh();
        };
        refresh_reqd();

        // when country changes, refresh required flag + query
        if (f.country) {
          const orig_onchange = f.country.df.onchange;
          f.country.df.onchange = () => {
            orig_onchange && orig_onchange();
            refresh_reqd();
            // force query refresh next time the field opens
            f.sr_state_link._filters = null;
          };
        }

        // mirror to legacy text so downstream logic keeps working
        const set_legacy = () => d.set_value("state", d.get_value("sr_state_link") || "");
        // initial sync (useful if country defaulted to India)
        set_legacy();

        // mirror on change
        const orig_change = f.sr_state_link.df.change;
        f.sr_state_link.df.change = () => {
          orig_change && orig_change();
          set_legacy();
        };
      }
    };
  };

  tryPatch();
})();
