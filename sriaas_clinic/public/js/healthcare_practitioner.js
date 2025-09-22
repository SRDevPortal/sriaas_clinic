function compose_full_name(frm) {
  const parts = [frm.doc.first_name, frm.doc.middle_name, frm.doc.last_name]
    .filter(Boolean);
  const full = parts.join(" ").trim();
  if (full && frm.doc.practitioner_name !== full) {
    frm.set_value("practitioner_name", full);
  }
}

frappe.ui.form.on("Healthcare Practitioner", {
  // keep the field synced while user types
  first_name(frm)  { compose_full_name(frm); },
  middle_name(frm) { compose_full_name(frm); },
  last_name(frm)   { compose_full_name(frm); },

  // most important: run right before client-side validation
  validate(frm)    { compose_full_name(frm); },

  // also handle brand-new form load where values may be prefilled
  refresh(frm)     { compose_full_name(frm); },
});
