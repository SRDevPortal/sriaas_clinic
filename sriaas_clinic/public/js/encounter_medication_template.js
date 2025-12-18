// Patient Encounter — Load meds from SR Medication Template
// Routing based on Medication Class
// Ayurvedic   → drug_prescription
// Homeopathic → sr_homeopathy_drug_prescription
// Allopathic  → sr_allopathy_drug_prescription

frappe.ui.form.on('Patient Encounter', {

  /* ---------------- TRIGGERS ---------------- */
  sr_medication_template(frm) {
    frm.trigger('load_template_medication');
  },

  /* ---------------- MAIN LOADER ---------------- */
  load_template_medication(frm) {
    if (!frm.doc.sr_medication_template) return;

    /* ---------------- HELPERS ---------------- */

    const resolve_child_table = (medication_class = "") => {
      switch ((medication_class || "").trim()) {
        case "Ayurvedic Medicine":
          return "drug_prescription";
        case "Homeopathic Medicine":
          return "sr_homeopathy_drug_prescription";
        case "Allopathic Medicine":
          return "sr_allopathy_drug_prescription";
        default:
          return null;
      }
    };

    const parse_days = (period_str = "") => {
      const p = (period_str || "").toLowerCase().trim();
      const n = parseInt(p) || 1;
      if (p.includes("month")) return n * 30;
      if (p.includes("week")) return n * 7;
      if (p.includes("day")) return n;
      return n;
    };

    const parse_per_day = (dosage_str = "") => {
      const d = (dosage_str || "").toLowerCase().trim();
      const nums = d.match(/\d+/g);

      if (nums && (/[-\s/]/.test(d) || nums.length > 1)) {
        return nums.map(n => parseInt(n) || 0).reduce((a, b) => a + b, 0);
      }
      if (/\b(qid|4\s*times|four\s*times|4x)\b/.test(d)) return 4;
      if (/\b(tds|thrice|three\s*times|3\s*times|3x)\b/.test(d)) return 3;
      if (/\b(bd|twice|two\s*times|2\s*times|2x)\b/.test(d)) return 2;
      if (/\b(od|once|1\s*time|1x|hs|bed\s*time|at\s*bedtime)\b/.test(d)) return 1;
      if (/\balternate\s*day\b/.test(d)) return 0.5;
      return 0;
    };

    const short_form = (dosage_form = "") => {
      const f = (dosage_form || "").toLowerCase();
      if (f.includes("tablet")) return "Tab";
      if (f.includes("capsule")) return "Cap";
      return "";
    };

    /* ---------------- CLEAR EXISTING ---------------- */

    [
      "drug_prescription",
      "sr_homeopathy_drug_prescription",
      "sr_allopathy_drug_prescription"
    ].forEach(table => {
      if (frm.fields_dict[table]) {
        frm.clear_table(table);
      }
    });

    /* ---------------- FETCH TEMPLATE ---------------- */

    frappe.call({
      method: "frappe.client.get",
      args: {
        doctype: "SR Medication Template",
        name: frm.doc.sr_medication_template
      },
      callback(r) {
        const tmpl = r.message;
        if (!tmpl) return;

        // Header instruction → Encounter instruction
        if (tmpl.sr_tmpl_instruction) {
          frm.set_value("sr_pe_instruction", tmpl.sr_tmpl_instruction);
        }

        /* ---------------- LOAD MEDICATIONS ---------------- */

        (tmpl.sr_medications || []).forEach(row => {

          const target_table = resolve_child_table(row.sr_medication_class);
          if (!target_table || !frm.fields_dict[target_table]) {
            console.warn(
              "Skipped medication due to invalid class:",
              row.sr_medication,
              row.sr_medication_class
            );
            return;
          }

          const grid = frm.fields_dict[target_table].grid;
          const childDoctype = grid.doctype;
          const hasField = (df) => frappe.meta.has_field(childDoctype, df);

          const med = frm.add_child(target_table);

          const medication_name = row.sr_medication || "";
          const dosage          = row.sr_dosage || "";
          const period_str      = row.sr_period || "";
          const dosage_form     = row.sr_dosage_form || "";
          const code            = row.sr_drug_code || "";
          const instr           = row.sr_instruction || "";

          const per_day   = parse_per_day(dosage);
          const days      = parse_days(period_str);
          const total_qty = Math.ceil(per_day * days);
          const short     = short_form(dosage_form);
          const is_countable = ["tablet","capsule"].includes(
            (dosage_form || "").toLowerCase()
          );

          med.medication = medication_name;

          if (hasField("drug_code"))   med.drug_code   = code;
          if (hasField("dosage"))      med.dosage      = dosage;
          if (hasField("period"))      med.period      = period_str;
          if (hasField("dosage_form")) med.dosage_form = dosage_form;

          if (hasField("sr_drug_instruction")) {
            med.sr_drug_instruction = instr;
          }

          if (hasField("no_of_tablets_per_day_for_calculation")) {
            med.no_of_tablets_per_day_for_calculation = per_day;
          }

          if (hasField("quantity") && is_countable) {
            med.quantity = total_qty;
          }

          const pretty = (is_countable && short && total_qty > 0)
            ? `${medication_name} (${total_qty} ${short})`
            : medication_name;

          if (hasField("sr_medication_name_print")) {
            med.sr_medication_name_print = pretty;
          } else if (hasField("custom_instruction")) {
            med.custom_instruction = instr
              ? `${pretty} — ${instr}`
              : pretty;
          }
        });

        /* ---------------- REFRESH ---------------- */

        frm.refresh_field("drug_prescription");
        frm.refresh_field("sr_homeopathy_drug_prescription");
        frm.refresh_field("sr_allopathy_drug_prescription");
      }
    });
  }
});

