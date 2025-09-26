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
