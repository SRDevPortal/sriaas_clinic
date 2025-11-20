// Filter each practitioner Link by the practitioner's "Pathy"
const PATHY_FILTERS = {
  // use your Patient Encounter link fieldnames here
  sr_ayurvedic_practitioner:  ["Ayurveda"],
  sr_homeopathy_practitioner: ["Homeopathy"],
  sr_allopathy_practitioner:  ["Allopathy"],
};

frappe.ui.form.on("Patient Encounter", {
  setup(frm) {
    Object.entries(PATHY_FILTERS).forEach(([fieldname, allowed]) => {
      // skip if field doesn't exist on this site/customization
      if (!frm.fields_dict[fieldname]) return;

      frm.set_query(fieldname, () => ({
        // If your field on Healthcare Practitioner is "sr_pathy", use that key:
        filters: {
          sr_pathy: ["in", allowed],
          status: "Active",
        },
      }));
    });
  },
});
