frappe.ui.form.on("Stock Entry", {
  async scan_barcode(frm) {
    if (!frm.doc.scan_barcode || frm.doc.docstatus !== 0 || frm.__sr_barcode_scan_in_progress) {
      return;
    }

    const warehouse = get_scan_warehouse(frm);
    if (!warehouse) {
      frappe.msgprint(__("Select a source or target Warehouse before scanning a barcode."));
      await clear_stock_entry_barcode(frm);
      return;
    }

    frm.__sr_barcode_scan_in_progress = true;
    const barcode = String(frm.doc.scan_barcode || "").trim();
    try {
      const response = await frappe.call({
        method: "sriaas_clinic.api.compliance_barcode.resolve_barcode",
        args: {
          barcode,
          warehouse,
          company: frm.doc.company,
          context_doctype: "Stock Entry",
          qty: 1,
          doc: frm.doc,
        },
      });
      await apply_stock_entry_scan(frm, response.message || {});
    } finally {
      frm.__sr_barcode_scan_in_progress = false;
      await clear_stock_entry_barcode(frm);
    }
  },
});

async function apply_stock_entry_scan(frm, result) {
  if (!result.item_code) {
    frappe.throw(__("The barcode resolver returned an invalid Item."));
  }

  let row = (frm.doc.items || []).find((candidate) => {
    if (candidate.item_code !== result.item_code) return false;
    if (result.tracking_mode === "erpnext_batch") {
      return candidate.batch_no === result.batch_no;
    }
    return !candidate.batch_no && !candidate.serial_and_batch_bundle;
  });

  if (!row) {
    row = frm.add_child("items");
    await frappe.model.set_value(row.doctype, row.name, "item_code", result.item_code);
    if (frm.doc.from_warehouse) {
      await frappe.model.set_value(row.doctype, row.name, "s_warehouse", frm.doc.from_warehouse);
    }
    if (frm.doc.to_warehouse) {
      await frappe.model.set_value(row.doctype, row.name, "t_warehouse", frm.doc.to_warehouse);
    }
  }

  if (result.tracking_mode === "erpnext_batch") {
    await frappe.model.set_value(row.doctype, row.name, "batch_no", result.batch_no);
  } else {
    if (row.batch_no) await frappe.model.set_value(row.doctype, row.name, "batch_no", null);
    if (row.serial_and_batch_bundle) {
      await frappe.model.set_value(row.doctype, row.name, "serial_and_batch_bundle", null);
    }
  }

  await frappe.model.set_value(row.doctype, row.name, "qty", flt(row.qty) + 1);
  if (result.rate !== null && result.rate !== undefined) {
    await frappe.model.set_value(row.doctype, row.name, "basic_rate", result.rate);
  }
  frm.refresh_field("items");

  if ((result.warnings || []).length) {
    frappe.msgprint((result.warnings || []).map((warning) => frappe.utils.escape_html(warning)).join("<br>"));
  }
}

function get_scan_warehouse(frm) {
  if (["Material Issue", "Send to Subcontractor"].includes(frm.doc.stock_entry_type)) {
    return frm.doc.from_warehouse;
  }
  return frm.doc.to_warehouse || frm.doc.from_warehouse;
}

async function clear_stock_entry_barcode(frm) {
  await frm.set_value("scan_barcode", "");
  frm.fields_dict.scan_barcode?.$input?.focus();
}
