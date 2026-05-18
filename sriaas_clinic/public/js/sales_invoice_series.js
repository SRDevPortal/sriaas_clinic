frappe.ui.form.on("Sales Invoice", {
  setup(frm) {
    frm.__sriaas_original_naming_series_options =
      frm.fields_dict.naming_series && frm.fields_dict.naming_series.df.options;
  },

  refresh(frm) {
    apply_sales_invoice_series_options(frm);
  },

  is_return(frm) {
    apply_sales_invoice_series_options(frm);
  },

  return_against(frm) {
    apply_sales_invoice_series_options(frm);
  },
});

function apply_sales_invoice_series_options(frm) {
  if (!frm.fields_dict.naming_series || frm.doc.docstatus !== 0) {
    return;
  }

  frappe.call({
    method: "sriaas_clinic.api.sales_invoice.get_sales_invoice_series_config",
    callback(r) {
      const config = r.message || {};
      const series = frm.doc.is_return
        ? config.credit_note_series
        : config.sales_invoice_series;
      const config_key = frm.doc.is_return
        ? "credit_note_series"
        : "sales_invoice_series";

      if (!series) {
        frappe.msgprint(__(`Please set ${config_key} in site config.`));
        return;
      }

      frm.set_df_property("naming_series", "options", series);

      if (frm.doc.naming_series !== series) {
        frm.set_value("naming_series", series);
      }
    },
  });
}
