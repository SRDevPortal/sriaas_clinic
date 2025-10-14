// sriaas_clinic/public/js/patient_encounter_block_autosave_for_proof.js
(function () {
  const FIELD = 'sr_pe_payment_proof';
  const CLEAR_AFTER_MS = 1500; // safety window to skip only the next autosave

  frappe.ui.form.on('Patient Encounter', {
    onload(frm) {
      if (frm._savePatchedForProof) return;

      const originalSave = frm.save.bind(frm);

      frm.save = function (action) {
        // Only swallow framework's autosave, never swallow user Submit
        if (frm._skipNextSaveDueToProof && (!action || action === 'Save')) {
          // clear the flag immediately so subsequent saves work
          frm._skipNextSaveDueToProof = false;
          // Return a resolved promise so any callers don't break
          return Promise.resolve(frm);
        }
        return originalSave(action);
      };

      frm._savePatchedForProof = true;
    },

    // Fires when the attach widget sets/changes the URL
    [FIELD](frm) {
      // Set a short-lived flag to skip the next autosave only
      frm._skipNextSaveDueToProof = true;

      // Safety: clear the flag automatically after a brief window
      if (frm._skipTimer) clearTimeout(frm._skipTimer);
      frm._skipTimer = setTimeout(() => {
        frm._skipNextSaveDueToProof = false;
        frm._skipTimer = null;
      }, CLEAR_AFTER_MS);

      // Optional feedback
      frappe.show_alert({
        message: __('Payment proof updated (changes not saved yet)'),
        indicator: 'blue'
      });
    }
  });
})();
