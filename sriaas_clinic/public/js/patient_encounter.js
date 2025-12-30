// sriaas_clinic/public/js/patient_encounter.js

// --------------------------------------------------
// Patient Encounter
// --------------------------------------------------
frappe.ui.form.on('Patient Encounter', {
    onload(frm) {
        handle_encounter_place_access(frm);
    },
    refresh(frm) {
        handle_encounter_place_access(frm);

        if (frm.is_new()) return;

        // --------------------------------------
        // Intercept S3 attachment clicks
        // --------------------------------------
        setTimeout(() => {
            const $wrapper = $(frm.wrapper);

            // Prevent duplicate bindings
            $wrapper.off('click.presign').on(
                'click.presign',
                'a[href]',
                function (e) {
                    const href = $(this).attr('href');
                    if (!href) return;

                    // Only intercept S3 / AWS links
                    if (href.startsWith('s3://') || href.includes('amazonaws.com')) {
                        e.preventDefault();
                        e.stopPropagation();

                        frappe.call({
                            method: 'sriaas_clinic.api.s3.presign.get_presigned_url',
                            args: {
                                file_url: href
                            },
                            callback: function (r) {
                                if (r && typeof r.message === 'string') {
                                    window.open(r.message, '_blank');
                                } else {
                                    frappe.msgprint(
                                        __('Could not generate secure file link.')
                                    );
                                }
                            }
                        });

                        return false;
                    }
                }
            );
        }, 500); // wait for attachments DOM
    }
});


// --------------------------------------------------
// Encounter Place Access Control
// --------------------------------------------------
function handle_encounter_place_access(frm) {
    const roles = frappe.user_roles || [];

    const is_pure_agent =
        roles.includes('Agent') &&
        !roles.includes('System Manager') &&
        !roles.includes('Administrator') &&
        !roles.includes('Healthcare Practitioner');

    if (is_pure_agent) {
        // Agent-only users → Online only
        if (frm.doc.sr_encounter_place !== 'Online') {
            frm.set_value('sr_encounter_place', 'Online');
        }
        frm.set_df_property('sr_encounter_place', 'read_only', 1);
    } else {
        // Admin / Doctor / Others → full access
        frm.set_df_property('sr_encounter_place', 'read_only', 0);
    }
}

// --------------------------------------------------
// Child Table: SR Multi Mode Payment
// --------------------------------------------------

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
