// sriaas_clinic/public/js/patient_encounter_clear_advance.js
frappe.ui.form.on('Patient Encounter', {
  sr_pe_paid_amount(frm) {
    const _flt = (v) => (typeof flt === "function" ? flt(v) : (parseFloat(v) || 0));
    const amt = _flt(frm.doc.sr_pe_paid_amount || 0);
    
    if (amt <= 0) {
      frm.set_value({
        sr_pe_mode_of_payment: null,
        sr_pe_payment_proof: null,
        sr_pe_payment_reference_no: null,
        sr_pe_payment_reference_date: null,
      });

      frm.sidebar?.attachments?.refresh();
    }
  }
});
