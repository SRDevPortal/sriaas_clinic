frappe.ui.form.on('CRM Lead', {
    refresh(frm) {
        if (frm.is_new()) return;
        frm.add_custom_button(__('Number Details'), async () => {
            const name = frm.doc.name;
            const response = await frappe.call({
                method: 'sriaas_clinic.api.crm_lead.privacy.get_number_details',
                args: { name }
            });
            if (frm.doc.name !== name) return;
            const data = response.message || {};
            const dialog = new frappe.ui.Dialog({
                title: __('Number Details'),
                fields: (data.numbers || []).map(number => ({
                    fieldname: number.display_field,
                    fieldtype: 'Data',
                    label: number.display_field === 'mask_mobile' ? __('Mobile') : __('Phone'),
                    read_only: 1,
                    default: data.can_view_full ? number.value : number.masked
                }))
            });
            dialog.show();
        });
    }
});
