// sriaas_clinic/public/js/patient_encounter.js

frappe.ui.form.on('Patient Encounter', {
    onload(frm) {
        handle_encounter_place_access(frm);
    },
    refresh(frm) {
        handle_encounter_place_access(frm);
    }
});

function handle_encounter_place_access(frm) {
    const roles = frappe.user_roles || [];

    const is_pure_agent =
        roles.includes("Agent") &&
        !roles.includes("System Manager") &&
        !roles.includes("Administrator") &&
        !roles.includes("Healthcare Practitioner");

    if (is_pure_agent) {
        // Agent-only users → Online only
        if (frm.doc.sr_encounter_place !== "Online") {
            frm.set_value("sr_encounter_place", "Online");
        }
        frm.set_df_property("sr_encounter_place", "read_only", 1);
    } else {
        // Admin / Doctor / Others → full access
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
