// sriaas_clinic/public/js/sales_invoice_actions.js

frappe.ui.form.on('Sales Invoice', {
  refresh(frm) {
    // Button: Print Payment Entry
    frm.add_custom_button('Print Payment Entry', async () => {
      try {
        const r = await frappe.call({
          method: 'sriaas_clinic.api.si_payment_flow.pe_lookup.get_payment_entries_for_invoice',
          args: { si_name: frm.doc.name },
        });
        const rows = r.message || [];

        if (!rows.length) {
          frappe.msgprint(__('No Payment Entry found for this Sales Invoice.'));
          return;
        }

        // If multiple PEs, ask which one to print
        let pe_name = rows[0].name;
        if (rows.length > 1) {
          const options = rows.map(d => ({
            label: `${d.name} (${d.status || (d.docstatus ? 'Submitted' : 'Draft')})`,
            value: d.name,
          }));

          const dlg = new frappe.ui.Dialog({
            title: __('Select Payment Entry to print'),
            fields: [{ fieldname: 'pe', label: 'Payment Entry', fieldtype: 'Select', options }],
            primary_action_label: __('Print'),
            primary_action: (values) => {
              pe_name = values.pe;
              dlg.hide();
              open_print(pe_name);
            }
          });
          dlg.set_value('pe', pe_name);
          dlg.show();
        } else {
          open_print(pe_name);
        }
      } catch (e) {
        console.error(e);
        frappe.msgprint(__('Could not fetch Payment Entries.'));
      }
    }, __('Actions'));

    // Button: Patient Dashboard
    if (frm.doc.patient) {
      frm.add_custom_button('Patient Dashboard', () => {
        // Works on v13+:
        frappe.set_route('dashboard-view', { doctype: 'Patient', name: frm.doc.patient });
        // Fallback (opens the Patient form if dashboard-view is unavailable):
        // frappe.set_route('Form', 'Patient', frm.doc.patient);
      }, __('Actions'));
    }
  },
});

function open_print(pe_name) {
  // Use standard print route; change 'Standard' to your PE Print Format if needed
  const doctype = 'Payment Entry';
  const format = 'Standard';
  const no_letterhead = 0;
  const url = `/printview?doctype=${encodeURIComponent(doctype)}&name=${encodeURIComponent(pe_name)}&format=${encodeURIComponent(format)}&no_letterhead=${no_letterhead}`;
  window.open(frappe.urllib.get_full_url(url), '_blank');
}
