const SR_COMPLIANCE_FIELDS = {
  sr_compliance_batch: "compliance_batch",
  sr_compliance_batch_no: "compliance_batch_no",
  sr_compliance_mfg_date: "manufacturing_date",
  sr_compliance_expiry_date: "expiry_date",
  sr_scanned_barcode: "scanned_barcode",
};

frappe.ui.form.on("Sales Invoice", {
  onload(frm) {
    apply_role_based_warehouse_rules(frm);
    configure_barcode_columns(frm);
  },

  refresh(frm) {
    apply_role_based_warehouse_rules(frm);
    configure_barcode_columns(frm);
    focus_barcode_field(frm);
  },

  set_warehouse(frm) {
    apply_role_based_warehouse_rules(frm);
  },

  async scan_barcode(frm) {
    if (!frm.doc.scan_barcode || frm.doc.docstatus !== 0) {
      return;
    }

    const barcode = String(frm.doc.scan_barcode || "").trim();
    if (frm.__sr_barcode_scan_in_progress) {
      frm.__sr_pending_barcode_scans = frm.__sr_pending_barcode_scans || [];
      frm.__sr_pending_barcode_scans.push(barcode);
      await frm.set_value("scan_barcode", "");
      return;
    }

    if (!frm.doc.set_warehouse) {
      frappe.msgprint(__("Please select a Warehouse before scanning a barcode."));
      await clear_and_focus_barcode(frm);
      return;
    }

    frm.__sr_barcode_scan_in_progress = true;

    try {
      const response = await frappe.call({
        method: "sriaas_clinic.api.compliance_barcode.resolve_barcode",
        args: {
          barcode,
          warehouse: frm.doc.set_warehouse,
          company: frm.doc.company,
          context_doctype: "Sales Invoice",
          qty: 1,
          doc: frm.doc,
        },
        freeze: false,
      });

      const result = response.message || {};
      await apply_barcode_result(frm, result);
      show_barcode_warnings(result.warnings || []);
    } finally {
      frm.__sr_barcode_scan_in_progress = false;
      await clear_and_focus_barcode(frm);
      const nextBarcode = (frm.__sr_pending_barcode_scans || []).shift();
      if (nextBarcode && frm.doc.docstatus === 0) {
        await frm.set_value("scan_barcode", nextBarcode);
      }
    }
  },
});

async function apply_barcode_result(frm, result) {
  if (!result.item_code || !["compliance", "erpnext_batch"].includes(result.tracking_mode)) {
    frappe.throw(__("The barcode resolver returned an invalid result."));
  }

  let row = find_matching_row(frm, result);
  const targetQty = flt((row && row.qty) || 0) + 1;
  const totalRequestedQty =
    (frm.doc.items || [])
      .filter((itemRow) => itemRow.item_code === result.item_code)
      .reduce((total, itemRow) => total + flt(itemRow.qty), 0) + 1;

  if (
    result.stock_policy === "Block" &&
    result.tracking_mode === "compliance" &&
    flt(result.available_qty) < totalRequestedQty
  ) {
    frappe.throw(
      __("Only {0} of Item {1} is available in Warehouse {2}.", [
        result.available_qty,
        result.item_code,
        frm.doc.set_warehouse,
      ])
    );
  }

  if (!row) {
    row = frm.add_child("items");
    await frappe.model.set_value(row.doctype, row.name, "item_code", result.item_code);
    await frappe.model.set_value(row.doctype, row.name, "warehouse", frm.doc.set_warehouse);
  }

  if (result.tracking_mode === "compliance") {
    await apply_compliance_snapshot(row, result);
    await clear_erpnext_batch_fields(row);
  } else {
    await clear_compliance_snapshot(row);
    await frappe.model.set_value(row.doctype, row.name, "batch_no", result.batch_no);
  }

  await frappe.model.set_value(row.doctype, row.name, "qty", targetQty);
  if (result.price_list_rate !== null && result.price_list_rate !== undefined) {
    await frappe.model.set_value(row.doctype, row.name, "price_list_rate", result.price_list_rate);
  }
  if (result.rate !== null && result.rate !== undefined) {
    await frappe.model.set_value(row.doctype, row.name, "rate", result.rate);
  }

  configure_barcode_columns(frm);
  frm.refresh_field("items");
}

function find_matching_row(frm, result) {
  return (frm.doc.items || []).find((row) => {
    if (row.item_code !== result.item_code) return false;
    if (result.tracking_mode === "compliance") {
      return row.sr_compliance_batch === result.compliance_batch && !row.batch_no;
    }
    return row.batch_no === result.batch_no && !row.sr_compliance_batch;
  });
}

async function apply_compliance_snapshot(row, result) {
  for (const [fieldname, resultKey] of Object.entries(SR_COMPLIANCE_FIELDS)) {
    await frappe.model.set_value(row.doctype, row.name, fieldname, result[resultKey] || null);
  }
}

async function clear_compliance_snapshot(row) {
  for (const fieldname of Object.keys(SR_COMPLIANCE_FIELDS)) {
    if (row[fieldname]) {
      await frappe.model.set_value(row.doctype, row.name, fieldname, null);
    }
  }
}

async function clear_erpnext_batch_fields(row) {
  for (const fieldname of ["batch_no", "serial_no", "serial_and_batch_bundle"]) {
    if (row[fieldname]) {
      await frappe.model.set_value(row.doctype, row.name, fieldname, null);
    }
  }
  if (row.use_serial_batch_fields) {
    await frappe.model.set_value(row.doctype, row.name, "use_serial_batch_fields", 0);
  }
}

function configure_barcode_columns(frm) {
  const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
  if (!grid) return;

  const hasLegacyRows = (frm.doc.items || []).some(
    (row) => row.batch_no || row.serial_and_batch_bundle
  );
  const hasComplianceField = Boolean(
    frappe.meta.get_docfield("Sales Invoice Item", "sr_compliance_batch_no", frm.doc.name)
  );

  if (hasComplianceField) {
    grid.toggle_display("sr_compliance_batch_no", true);
    grid.update_docfield_property("sr_compliance_batch_no", "hidden", 0);
  }

  if (frappe.meta.get_docfield("Sales Invoice Item", "batch_no", frm.doc.name)) {
    grid.toggle_display("batch_no", hasLegacyRows);
    grid.update_docfield_property("batch_no", "hidden", hasLegacyRows ? 0 : 1);
  }
}

function show_barcode_warnings(warnings) {
  if (!warnings.length) return;
  frappe.msgprint({
    title: __("Barcode Warning"),
    indicator: "orange",
    message: warnings.map((warning) => frappe.utils.escape_html(warning)).join("<br>"),
  });
}

async function clear_and_focus_barcode(frm) {
  await frm.set_value("scan_barcode", "");
  focus_barcode_field(frm);
}

function focus_barcode_field(frm) {
  if (frm.fields_dict.scan_barcode) {
    frm.fields_dict.scan_barcode.$input?.focus();
  }
}

function apply_role_based_warehouse_rules(frm) {
  const roles = frappe.user_roles || [];

  if (frappe.session.user === "Administrator" || roles.includes("System Manager")) {
    frm.set_df_property("set_warehouse", "read_only", 0);
    return;
  }

  if (roles.includes("OPD Biller")) {
    lock_warehouse(frm, "OPD Warehouse - SR");
    return;
  }

  if (roles.includes("Packaging Biller")) {
    lock_warehouse(frm, "Packaging Warehouse - SR");
  }
}

function lock_warehouse(frm, warehouse) {
  if (frm.doc.set_warehouse !== warehouse) {
    frm.set_value("set_warehouse", warehouse);
  }
  frm.set_df_property("set_warehouse", "read_only", 1);
  (frm.doc.items || []).forEach((row) => {
    frappe.model.set_value(row.doctype, row.name, "warehouse", warehouse);
  });
}
