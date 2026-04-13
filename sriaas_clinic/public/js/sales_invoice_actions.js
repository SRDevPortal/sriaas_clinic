// sriaas_clinic/public/js/sales_invoice_actions.js

frappe.ui.form.on('Sales Invoice', {
  setup(frm) {
    configure_item_grid(frm);
  },

  refresh(frm) {
    configure_item_grid(frm);

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

    if (frm.doc.patient) {
      frm.add_custom_button(__('Patient Dashboard'), () => {
        if (frm.doc.patient) {
          frappe.set_route('Form', 'Patient', frm.doc.patient);
        } else {
          frappe.msgprint(__('No Patient linked on this Sales Invoice.'));
        }
      });
    }
  },
});

frappe.ui.form.on('Sales Invoice Item', {
  item_tax_template(frm) {
    recalculate_invoice(frm);
  },

  discount_percentage(frm) {
    recalculate_invoice(frm);
  },

  qty(frm) {
    recalculate_invoice(frm);
  },

  price_list_rate(frm) {
    recalculate_invoice(frm);
  },
});

function configure_item_grid(frm) {
  const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
  if (!grid) return;

  ['amount'].forEach((fieldname) => {
    grid.toggle_display(fieldname, false);
    grid.update_docfield_property(fieldname, 'hidden', 1);
  });

  [
    'batch_no',
    'price_list_rate',
    'rate',
    'discount_percentage',
    'discount_amount',
    'item_tax_template',
    'item_tax_rate',
    'net_rate',
    'sr_row_tax_amount',
    'net_amount'
  ].forEach((fieldname) => {
    grid.toggle_display(fieldname, true);
    grid.update_docfield_property(fieldname, 'hidden', 0);
  });
}

function recalculate_invoice(frm) {
  if (frm.cscript && typeof frm.cscript.calculate_taxes_and_totals === 'function') {
    frm.cscript.calculate_taxes_and_totals();
  }
  frm.refresh_field('items');
}

function open_print(pe_name) {
  const doctype = 'Payment Entry';
  const format = 'Standard';
  const no_letterhead = 0;
  const url = `/printview?doctype=${encodeURIComponent(doctype)}&name=${encodeURIComponent(pe_name)}&format=${encodeURIComponent(format)}&no_letterhead=${no_letterhead}`;
  window.open(frappe.urllib.get_full_url(url), '_blank');
}
