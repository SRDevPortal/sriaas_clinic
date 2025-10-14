// sriaas_clinic/public/js/patient_encounter_upload_proof.js
frappe.ui.form.on('Patient Encounter', {
  refresh(frm) {
    if (frm.is_new()) return;

    const BTN = __('Payment Receipt');
    if (frm.custom_buttons && frm.custom_buttons[BTN]) return;

    frm.add_custom_button(BTN, () => {
      new frappe.ui.FileUploader({
        doctype: frm.doctype,
        docname: frm.docname,
        // no fieldname -> attaches in sidebar only; does NOT save the doc
        restrictions: { allowed_file_types: ['image/*', 'application/pdf'] },
        on_success(file_doc) {
          const url = file_doc && file_doc.file_url;
          if (!url) {
            frappe.msgprint(__('Upload succeeded but file URL was not returned.'));
            return;
          }

          // fill the field, but DON'T save (keeps the Encounter as-is)
          frm.set_value('sr_pe_payment_proof', url);

          // refresh attachments sidebar UI
          frm.sidebar?.attachments?.refresh();

          // optional toast (no save)
          frappe.show_alert({ message: __('Payment proof attached (not saved yet)'), indicator: 'green' });
        },
        on_error(err) {
          console.error(err);
          frappe.msgprint(__('Upload failed'));
        }
      });
    }).addClass('btn-primary');
  }
});
