// sriaas_clinic/public/js/patient_encounter.js

frappe.ui.form.on('Patient Encounter', {
    onload(frm) {
        apply_encounter_access_rules(frm);
    },

    refresh(frm) {
        apply_encounter_access_rules(frm);

        if (frm.is_new()) return;

        intercept_s3_attachments(frm);
    },

    sr_encounter_type(frm) {
        handle_encounter_source_requirement(frm);
    },

    sr_encounter_place(frm) {
        handle_encounter_source_requirement(frm);
    }
});


// --------------------------------------------------
// Centralized Access Rules
// --------------------------------------------------
function apply_encounter_access_rules(frm) {
    handle_encounter_place_access(frm);
    handle_encounter_source_requirement(frm);
    handle_encounter_status_access(frm);
}


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
// Encounter Source Requirement (Agent Only)
// --------------------------------------------------
function handle_encounter_source_requirement(frm) {
    const roles = frappe.user_roles || [];
    const is_agent = roles.includes('Agent');

    const is_required =
        is_agent &&
        ['Followup', 'Order'].includes(frm.doc.sr_encounter_type) &&
        frm.doc.sr_encounter_place === 'Online';

    frm.toggle_reqd('sr_encounter_source', is_required);
}


// --------------------------------------------------
// Encounter Status Access Control (Agent Only)
// --------------------------------------------------
function handle_encounter_status_access(frm) {
    const roles = frappe.user_roles || [];

    const is_pure_agent =
        roles.includes('Agent') &&
        !roles.includes('System Manager') &&
        !roles.includes('Administrator') &&
        !roles.includes('Healthcare Practitioner');

    frm.set_df_property(
        'sr_encounter_status',
        'read_only',
        is_pure_agent && !frm.is_new()
    );
}


// --------------------------------------------------
// Intercept S3 Attachments
// --------------------------------------------------
function intercept_s3_attachments(frm) {
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
                        args: { file_url: href },
                        callback(r) {
                            if (typeof r.message === 'string') {
                                window.open(r.message, '_blank');
                            } else {
                                frappe.msgprint(__('Could not generate secure file link.'));
                            }
                        }
                    });
                }
            }
        );
    }, 500);
}


// --------------------------------------------------
// Child Table: SR Multi Mode Payment
// --------------------------------------------------
frappe.ui.form.on('SR Multi Mode Payment', {
    mmp_payment_proof(frm, cdt, cdn) {
        const row = frappe.get_doc(cdt, cdn);

        if (!row.mmp_payment_proof && row.__last_proof) {
            frappe.call({
                method: 'sriaas_clinic.api.s3.delete.delete_s3_by_url',
                args: { file_url: row.__last_proof },
                silent: true
            });
        }

        row.__last_proof = row.mmp_payment_proof;
    }
});
