/**
 * SR Order Item – inline helpers (sriaas_clinic)
 * - On sr_item_code: fetch stock_uom, item_name, description
 * - On sr_item_qty / sr_item_rate: amount = qty * rate
 */

frappe.ui.form.on('SR Order Item', {
  sr_item_qty(frm, cdt, cdn)  { sr_set_amount(cdt, cdn); },
  sr_item_rate(frm, cdt, cdn) { sr_set_amount(cdt, cdn); },

  sr_item_code(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const item_code = row.sr_item_code;
    if (!item_code) return;

    frappe.db.get_value('Item', item_code, ['stock_uom','item_name','description']).then(r => {
      const m = (r && r.message) || {};
      sr_set_if_exists(cdt, cdn, 'sr_item_uom',  m.stock_uom);
      sr_set_if_exists(cdt, cdn, 'sr_item_name', m.item_name);
      // prefer custom description; fall back to standard
      if (!sr_set_if_exists(cdt, cdn, 'sr_item_description', m.description)) {
        sr_set_if_exists(cdt, cdn, 'description', m.description);
      }
      sr_set_amount(cdt, cdn);
    });
  },
});

function sr_set_amount(cdt, cdn) {
  const d    = locals[cdt][cdn] || {};
  const qty  = Number(d.sr_item_qty ?? d.qty)   || 0;
  const rate = Number(d.sr_item_rate ?? d.rate) || 0;
  const amt  = qty * rate;

  // write to custom amount if present, else standard
  if (!sr_set_if_exists(cdt, cdn, 'sr_item_amount', amt)) {
    sr_set_if_exists(cdt, cdn, 'amount', amt);
  }
}

// set only if field exists on the child doctype
function sr_set_if_exists(cdt, cdn, fieldname, value) {
  const exists = Boolean(frappe.meta.get_docfield('SR Order Item', fieldname, (locals[cdt][cdn] || {}).parent));
  if (!exists) return false;
  frappe.model.set_value(cdt, cdn, fieldname, value);
  return true;
}
