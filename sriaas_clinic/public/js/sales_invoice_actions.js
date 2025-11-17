// sriaas_clinic/public/js/sales_invoice_actions.js

frappe.ui.form.on('Sales Invoice', {
  refresh(frm) {
    // Print Payment Entry
    const printBtn = frm.add_custom_button(__('Print Payment'), async () => {
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
    });
    // decorate_button(printBtn, 'fa fa-money');

    // Patient Dashboard
    if (frm.doc.patient) {
      const dashBtn = frm.add_custom_button(__('Patient Dashboard'), () => {
        if (frm.doc.patient) {
          frappe.set_route('Form', 'Patient', frm.doc.patient);
        } else {
          frappe.msgprint(__('No Patient linked on this Sales Invoice.'));
        }
      });
      // decorate_button(dashBtn, 'fa fa-user');
    }
  },
});

function open_print(pe_name) {
  const doctype = 'Payment Entry';
  const format = 'Standard'; // change to your custom print format if needed
  const no_letterhead = 0;
  const url = `/printview?doctype=${encodeURIComponent(doctype)}&name=${encodeURIComponent(pe_name)}&format=${encodeURIComponent(format)}&no_letterhead=${no_letterhead}`;
  window.open(frappe.urllib.get_full_url(url), '_blank');
}

// Small helper to add an icon + keep consistent style
function decorate_button($btn, icon_class) {
  try {
    // $btn is a jQuery object in most builds
    $btn.removeClass('btn-default').addClass('btn-secondary');
    const el = $btn.get(0);
    if (el && icon_class) {
      // prepend icon
      el.innerHTML = `<i class="${icon_class}" style="margin-right:6px;"></i>` + el.innerHTML;
    }
  } catch (e) {
    // no-op if DOM shape changes
  }
}
