// sriaas_clinic/public/js/patient_encounter.js

// --------------------------------------
// Parent: Patient Encounter
// --------------------------------------
frappe.ui.form.on('Patient Encounter', {
    onload(frm) {
        toggle_encounter_place(frm);
    },

    refresh(frm) {
        toggle_encounter_place(frm);
    }
});

function toggle_encounter_place(frm) {
    const is_agent =
        frappe.user_roles.includes("Agent") &&
        !frappe.user_roles.includes("System Manager");

    if (is_agent) {
        frm.set_value("sr_encounter_place", "Online");
        frm.set_df_property("sr_encounter_place", "read_only", 1);
    } else {
        frm.set_df_property("sr_encounter_place", "read_only", 0);
    }
}

// --------------------------------------
// Child Table: SR Multi Mode Payment
// --------------------------------------
frappe.ui.form.on('SR Multi Mode Payment', {
    mmp_payment_proof(frm, cdt, cdn) {
        const row = frappe.get_doc(cdt, cdn);

        // If proof was cleared and there was a previous value → delete from S3
        if (!row.mmp_payment_proof && row.__last_proof) {
            frappe.call({
                method: 'sriaas_clinic.api.s3.delete.delete_s3_by_url',
                args: {
                    file_url: row.__last_proof
                }
            });
        }

        // Store current value for next change
        row.__last_proof = row.mmp_payment_proof;
    }
});
