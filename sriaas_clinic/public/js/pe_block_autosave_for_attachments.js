(function () {
  // Fields to protect from accidental autosave when attachments are changed/uploaded.
  const ATTACH_FIELDS = [
    'sr_pe_payment_proof',   // existing payment proof field
    'sr_medical_reports'     // new medical reports attach (multi)
  ];

  // How long to keep the "skip next save" flag (ms).
  const CLEAR_AFTER_MS = 1500;

  frappe.ui.form.on('Patient Encounter', {
    onload(frm) {
      // don't patch twice
      if (frm._savePatchedForAttachments) return;

      // keep original save
      const originalSave = frm.save.bind(frm);

      // override save to swallow only the framework autosave once when flagged.
      frm.save = function (action) {
        // Only swallow framework autosave (no action or 'Save'), never swallow explicit Submit
        if (frm._skipNextSaveDueToAttachment && (!action || action === 'Save')) {
          // clear the flag immediately so subsequent saves work normally
          frm._skipNextSaveDueToAttachment = false;
          return Promise.resolve(frm);
        }
        return originalSave(action);
      };

      frm._savePatchedForAttachments = true;

      // Attach DOM-level listeners to file inputs inside the attachment widget(s).
      // This catches multi-file selection/uploads triggered by the widget's file input.
      // We attach these listeners on refresh too (so we rebind if widget re-renders).
      const bindFileInputChange = () => {
        try {
          ATTACH_FIELDS.forEach(fieldname => {
            const f = frm.get_field(fieldname);
            if (!f || !f.$wrapper) return;

            // Avoid double-binding: set a flag on field wrapper
            if (f.$wrapper.data('skip-listener-bound')) return;
            f.$wrapper.data('skip-listener-bound', true);

            // Delegate listener: when user chooses file(s) via input[type=file]
            f.$wrapper.on('change', 'input[type=file]', function () {
              // mark to skip next autosave
              frm._skipNextSaveDueToAttachment = true;

              // timer safety
              if (frm._skipTimer) clearTimeout(frm._skipTimer);
              frm._skipTimer = setTimeout(() => {
                frm._skipNextSaveDueToAttachment = false;
                frm._skipTimer = null;
              }, CLEAR_AFTER_MS);

              // user feedback
              frappe.show_alert({ message: __('Changes not saved yet'), indicator: 'blue' });
            });
          });
        } catch (e) {
          // safe fail — do nothing but avoid breaking form
          console.error('bindFileInputChange error', e);
        }
      };

      // call once onload
      bindFileInputChange();

      // Also rebind after refresh in case widget re-renders
      frm.page.wrapper.on('refresh', bindFileInputChange);
    },

    // Also listen for Frappe field-change events (fallback).
    // This covers cases where the framework triggers the field event (Attach widget sets URL).
    refresh(frm) {
      // no-op; but ensures listeners attached on refresh (DOM handler above rebinds)
    }
  });

  // Register per-field handlers using frappe.ui.form.on for extra safety:
  ATTACH_FIELDS.forEach(function (FIELD) {
    frappe.ui.form.on('Patient Encounter', {
      // dynamic key: when the field value is changed by the widget, fire
      [FIELD]: function (frm) {
        // set skip-next-save flag and timer
        frm._skipNextSaveDueToAttachment = true;

        if (frm._skipTimer) clearTimeout(frm._skipTimer);
        frm._skipTimer = setTimeout(() => {
          frm._skipNextSaveDueToAttachment = false;
          frm._skipTimer = null;
        }, CLEAR_AFTER_MS);

        frappe.show_alert({ message: __('Changes not saved yet'), indicator: 'blue' });
      }
    });
  });

})();
