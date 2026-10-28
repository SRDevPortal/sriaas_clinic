// sriaas_clinic/public/js/patient_encounter.js

frappe.ui.form.on('Patient Encounter', {
    onload(frm) {
        apply_encounter_access_rules(frm);
        apply_active_master_filters(frm);
    },

    refresh(frm) {
        apply_encounter_access_rules(frm);
        apply_active_master_filters(frm);

        if (frm.is_new()) return;

        intercept_s3_attachments(frm);
    },

    sr_encounter_type(frm) {
        apply_encounter_submission_rule(frm);
        handle_encounter_place_access(frm);
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
    apply_encounter_submission_rule(frm);
    handle_encounter_place_access(frm);
    handle_encounter_source_requirement(frm);
    handle_encounter_status_access(frm);
}


function apply_encounter_submission_rule(frm) {
    // Keep the standard permission checks and evaluate the current document on
    // every toolbar refresh, including navigation between encounter records.
    if (!frm.toolbar._sr_appointment_submit_guard) {
        const can_submit = frm.toolbar.can_submit;
        frm.toolbar.can_submit = function () {
            const type = (frm.doc.sr_encounter_type || '').trim().toLowerCase();
            return type !== 'appointment' && can_submit.call(this);
        };
        frm.toolbar._sr_appointment_submit_guard = true;
    }
    frm.toolbar.set_primary_action();
}


// --------------------------------------------------
// Encounter Place Access Control
// --------------------------------------------------
function handle_encounter_place_access(frm) {
    const roles = frappe.user_roles || [];
    const encounter_type = frm.doc.sr_encounter_type;

    const is_pure_agent =
        roles.includes('Agent') &&
        !roles.includes('System Manager') &&
        !roles.includes('Administrator') &&
        !roles.includes('Healthcare Practitioner');

    if (is_pure_agent) {
        if (['Followup', 'Order'].includes(encounter_type)) {
            if (frm.doc.sr_encounter_place !== 'Online') {
                frm.set_value('sr_encounter_place', 'Online');
            }
            frm.set_df_property('sr_encounter_place', 'read_only', 1);
            return;
        }

        if (encounter_type === 'Appointment') {
            frm.set_df_property('sr_encounter_place', 'read_only', 0);
            return;
        }

        frm.set_df_property('sr_encounter_place', 'read_only', 1);
        return;
    }

    // Admin / Doctor / Others -> full access
    frm.set_df_property('sr_encounter_place', 'read_only', 0);
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
                        args: { file_url: href, doctype: frm.doctype, docname: frm.doc.name },
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


function apply_active_master_filters(frm) {

    // SR Delivery Type -> only active
    frm.set_query("sr_delivery_type", function() {
        return {
            filters: {
                is_active: 1
            }
        };
    });

    // SR Medication Template -> only active
    frm.set_query("sr_medication_template", function() {
        return {
            filters: {
                is_active: 1
            }
        };
    });

    // SR Encounter Status -> only active
    frm.set_query("sr_encounter_status", function() {
        return {
            filters: {
                is_active: 1
            }
        };
    });

    // SR Encounter Source -> only active
    frm.set_query("sr_encounter_source", function() {
        return {
            filters: {
                is_active: 1
            }
        };
    });

    // SR Sales Type -> only active
    frm.set_query("sr_sales_type", function() {
        return {
            filters: {
                is_active: 1
            }
        };
    });
}

function setup_appointment_autosave(frm) {
    if (frm._appointment_autosave) return;
    const state = frm._appointment_autosave = { timer: null, saving: false };
    const status = $('<span class="text-muted small" role="status" aria-live="polite"></span>')
        .appendTo(frm.page.page_actions);
    const eligible = () => window.cur_frm === frm &&
        frappe.get_route()[0] === 'Form' && frappe.get_route()[2] === frm.doc.name &&
        !frm.is_new() && frm.doc.docstatus === 0 && !frm.save_disabled &&
        (frm.doc.sr_encounter_type || '').trim().toLowerCase() === 'appointment';
    const schedule = () => {
        clearTimeout(state.timer);
        if (!eligible()) { status.text(''); return; }
        if (state.saving) return;
        status.text(__('Unsaved changes'));
        const name = frm.doc.name;
        state.timer = setTimeout(() => save(name), 2000);
    };
    const save = async (name) => {
        if (!eligible() || frm.doc.name !== name || !frm.is_dirty()) return;
        // Let link lookups, manual saves and attachment saves finish first.
        if (frappe.ui.form.is_saving || frappe.request.ajax_count || frm._skipNextSaveDueToProof) {
            schedule();
            return;
        }
        if (!appointment_autosave_complete(frm)) {
            status.text(__('Complete required fields to autosave'));
            return;
        }
        state.saving = true;
        status.text(__('Saving...'));
        try {
            // Normal AJAX draft save preserves all validation and permissions.
            // Frappe briefly freezes editing while the request is in flight.
            await frm.save('Save', null, null, () => {});
            if (frm.doc.name === name && eligible()) {
                if (frm.is_dirty()) {
                    status.text(__('Save failed - use Save to retry'));
                } else {
                    status.text('');
                    // The standard savedocs response already shows the Saved notification.
                }
            }
        } catch (error) {
            if (frm.doc.name === name) status.text(__('Save failed - use Save to retry'));
        } finally {
            state.saving = false;
        }
    };
    // Dirty includes parent fields, child edits, row additions and deletions.
    frm.$wrapper.on('dirty.appointment_autosave', schedule);
    // Reset the delay while typing before the control commits its value.
    frm.$wrapper.on('input.appointment_autosave change.appointment_autosave',
        'input, textarea, select, [contenteditable]', schedule);
    frappe.router.on('change', () => {
        clearTimeout(state.timer);
        status.text('');
    });
}

function appointment_autosave_complete(frm) {
    return frappe.model.get_all_docs(frm.doc).every(doc =>
        (frappe.meta.docfield_list[doc.doctype] || []).every(field => {
            const df = frappe.meta.get_docfield(doc.doctype, field.fieldname, doc.name);
            if (!df || !df.fieldname) return true;
            let required = df.reqd;
            const expression = df.mandatory_depends_on;
            if (expression) {
                try {
                    if (typeof expression === 'boolean') required = expression;
                    else if (typeof expression === 'function') required = expression(doc);
                    else if (expression.startsWith('eval:')) {
                        required = frappe.utils.eval(expression.slice(5), { doc, parent: frm.doc });
                    } else {
                        const value = doc[expression];
                        required = Array.isArray(value) ? value.length > 0 : !!value;
                    }
                } catch (error) {
                    return false;
                }
            }
            return !required || frappe.model.has_value(doc.doctype, doc.name, df.fieldname);
        })
    );
}

frappe.ui.form.on('Patient Encounter', {
    refresh(frm) {
        setup_appointment_autosave(frm);
    }
});
