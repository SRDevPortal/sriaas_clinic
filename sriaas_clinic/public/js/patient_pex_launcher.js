// Patient: Add PEX launcher
frappe.ui.form.on('Patient', {
    refresh(frm) {
        // Mount only if the HTML field exists
        const html_field = frm.get_field('sr_pex_launcher_html');
        if (!html_field) return;

        const $wrapper = html_field.$wrapper;
        if ($wrapper.hasClass('pex-mounted')) return;
        $wrapper.addClass('pex-mounted');

        // Render launcher UI
        $wrapper.html(`
            <div class="flex" style="align-items:center; justify-content:space-between; margin:12px 0;">
                <div>
                    <h4 style="margin:0 0 4px;">Create Patient Encounter (PEX)</h4>
                    <div class="text-muted">Open full PE with all fields, pre-filled.</div>
                </div>
                <button class="btn btn-primary" id="sr_open_full_pe">Open Full PE</button>
            </div>
        `);

        // Button handler
        $wrapper.find('#sr_open_full_pe').on('click', () => {
            frappe.route_options = {
                from_pex: 1,
                patient: frm.doc.name,
                company: frm.doc.company || frappe.defaults.get_default('company'),
                practitioner: frm.doc.primary_healthcare_practitioner || '',
                pex_copy_forward: $wrapper.find('#pex_copy_forward').is(':checked') ? 1 : 0,
                pex_fill_draft: $wrapper.find('#pex_fill_draft').is(':checked') ? 1 : 0,
            };
            frappe.new_doc('Patient Encounter');
        });
    }
});
