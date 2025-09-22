// Recalculate on field changes (visual aid only; server recomputes on save)
frappe.ui.form.on("Item", {
  sr_pkg_length: recalc,
  sr_pkg_width: recalc,
  sr_pkg_height: recalc,
  sr_pkg_dead_weight: recalc,
});

function toNum(v) {
  if (!v) return 0;
  if (typeof v === "string") v = v.replace(/,/g, "").trim();
  const n = parseFloat(v);
  return isNaN(n) ? 0 : n;
}

function recalc(frm) {
  const L = toNum(frm.doc.sr_pkg_length);
  const W = toNum(frm.doc.sr_pkg_width);
  const H = toNum(frm.doc.sr_pkg_height);
  const dead = toNum(frm.doc.sr_pkg_dead_weight);

  let vol = 0;
  if (L && W && H) vol = (L * W * H) / 5000.0;

  const applied = Math.max(dead, vol);

  frm.set_value("sr_pkg_vol_weight", Math.round(vol * 1000) / 1000);
  frm.set_value("sr_pkg_applied_weight", Math.round(applied * 1000) / 1000);
}
