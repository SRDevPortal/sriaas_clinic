/** Filter Medication by Medication Class per child table in Patient Encounter. */

// Map your PE child-table fieldnames -> allowed medication_class values
const CLASS_FILTERS = {
  // Patient Encounter child table fieldname : allowed classes (strings in Medication.medication_class)
  drug_prescription:               ["Ayurvedic Medicine", "Ayurvedic"],       // allow both labels if you use variants
  sr_homeopathy_drug_prescription: ["Homeopathic Medicine", "Homeopathic"],
  sr_allopathy_drug_prescription:  ["Allopathic Medicine", "Allopathic"],
};

frappe.ui.form.on("Patient Encounter", {
  refresh(frm) {
    // For each child table, set a query on its `medication` link
    Object.entries(CLASS_FILTERS).forEach(([parentfield, allowedClasses]) => {
      frm.set_query("medication", parentfield, function () {
        return {
          // Use array-of-tuples; 'in' works reliably here
          filters: [
            ["Medication", "medication_class", "in", allowedClasses],
            ["Medication", "disabled", "=", 0],
          ],
        };
      });
    });
  },
});

/**
 * Hard-guard: if someone picks a Medication whose class doesn't belong to
 * the current table, show a message and clear it.
 * (Assumes the child row doctype is the standard "Drug Prescription".
 * If your child doctypes are different, duplicate this block for each doctype.)
 */
frappe.ui.form.on("Drug Prescription", {
  medication(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const allowed = CLASS_FILTERS[row.parentfield] || null;
    if (!allowed || !row.medication) return;

    frappe.db.get_value("Medication", row.medication, "medication_class").then((r) => {
      const cls = r?.message?.medication_class;
      if (cls && !allowed.includes(cls)) {
        frappe.msgprint({
          message: `Selected Medication is <b>${frappe.utils.escape_html(cls)}</b> which is not allowed in this section.`,
          title: "Wrong Medication Class",
          indicator: "red",
        });
        row.medication = null;
        frm.refresh_field(row.parentfield);
      }
    });
  },
});
