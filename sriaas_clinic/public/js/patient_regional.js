// sriaas_clinic/public/js/patient_regional.js
frappe.ui.form.on("Patient", {
    sr_medical_department(frm) {

        // If department is NOT regional, reset both fields
        if (frm.doc.sr_medical_department !== "Regional") {
            frm.set_value("sr_dpt_disease", null);
            frm.set_value("sr_dpt_language", null);
        }

        // Optional: If you want to refresh UI visibility immediately
        frm.refresh_field("sr_dpt_disease");
        frm.refresh_field("sr_dpt_language");
    }
});
