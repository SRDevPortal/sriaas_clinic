// Patient Encounter — auto-fill drug_code & sr_medication_name_print on manual row edits
// Child grid: Drug Prescription (works for Ayurvedic/Homeopathy/Allopathy if they share this child)

// ---------- helpers ----------
const MED_DIRECT_ITEM_FIELDS = ["linked_item", "default_item"]; // add any direct Item link fields here

function parse_days(s = "") {
  const p = (s || "").toLowerCase().trim();
  const n = parseInt(p) || 0;
  if (p.includes("month")) return n * 30;
  if (p.includes("week"))  return n * 7;
  if (p.includes("day"))   return n;
  return n;
}

// "1-0-1" -> 2; OD/BD/TDS/QID; HS/bed time -> 1; "alternate day" -> 0.5
function parse_per_day(s = "") {
  const d = (s || "").toLowerCase().trim();
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
}

function short_form(f = "") {
  const x = (f || "").toLowerCase();
  if (x.includes("tablet"))  return "Tab";
  if (x.includes("capsule")) return "Cap";
  return "";
}

async function get_medication_doc(name) {
  try {
    const r = await frappe.call({
      method: "frappe.client.get",
      args: { doctype: "Medication", name },
    });
    return r && r.message ? r.message : null;
  } catch (e) {
    console.warn("Medication load failed", name, e);
    return null;
  }
}

// Pull an Item link from the Medication doc (direct field or child with item/item_code)
function find_item_from_med_doc(med_doc) {
  if (!med_doc) return "";
  for (const f of MED_DIRECT_ITEM_FIELDS) {
    if (med_doc[f]) return med_doc[f];
  }
  for (const v of Object.values(med_doc)) {
    if (Array.isArray(v)) {
      for (const r of v) {
        if (r && (r.item || r.item_code)) return r.item || r.item_code;
      }
    }
  }
  return "";
}

// Resolve which print field exists on this site (we use sr_medication_name_print)
function resolve_print_field(cdt) {
  if (frappe.meta.has_field(cdt, "sr_medication_name_print")) return "sr_medication_name_print";
  return "";
}

async function set_drug_code_from_medication(cdt, cdn) {
  const row = locals[cdt][cdn];
  if (!row?.medication) return;

  const med_doc  = await get_medication_doc(row.medication);
  const itemname = find_item_from_med_doc(med_doc);

  if (itemname && frappe.meta.has_field(cdt, "drug_code")) {
    await frappe.model.set_value(cdt, cdn, "drug_code", itemname); // Link → Item
  }
}

async function update_print_name(cdt, cdn) {
  const row = locals[cdt][cdn];
  if (!row) return;

  const pf = resolve_print_field(cdt);
  if (!pf) return;

  const name      = row.medication || row.item_name || row.drug || "";
  const per       = parse_per_day(row.dosage || "");
  const days      = parse_days(row.period || "");
  const qty       = Math.ceil(per * days);
  const sf        = short_form(row.dosage_form || "");
  const countable = ["tablet", "capsule"].includes((row.dosage_form || "").toLowerCase());

  const pretty = (name && countable && sf && per > 0 && days > 0)
    ? `${name} (${qty} ${sf})`
    : name;

  await frappe.model.set_value(cdt, cdn, pf, pretty);
}

async function sync_row(cdt, cdn) {
  const row = locals[cdt][cdn];
  if (!row) return;

  // Fill drug_code from Medication (once)
  if (row.medication && !row.drug_code) {
    await set_drug_code_from_medication(cdt, cdn);
  }

  // numeric helpers
  const per = parse_per_day(row.dosage || "");
  if (frappe.meta.has_field(cdt, "no_of_tablets_per_day_for_calculation")) {
    await frappe.model.set_value(cdt, cdn, "no_of_tablets_per_day_for_calculation", per);
  }

  const days      = parse_days(row.period || "");
  const countable = ["tablet", "capsule"].includes((row.dosage_form || "").toLowerCase());
  if (frappe.meta.has_field(cdt, "quantity") && per > 0 && days > 0 && countable) {
    await frappe.model.set_value(cdt, cdn, "quantity", Math.ceil(per * days));
  }

  // Always refresh pretty name
  await update_print_name(cdt, cdn);
}

// Bind child (works for Ayurvedic/Homeopathy/Allopathy if they share “Drug Prescription”)
bind_child("Drug Prescription");
// If you truly have distinct child doctypes, uncomment and set exact names:
// bind_child("Homeopathy Drug Prescription");
// bind_child("Allopathy Drug Prescription");

function bind_child(child_doctype) {
  frappe.ui.form.on(child_doctype, {
    async medication(frm, cdt, cdn)   { await sync_row(cdt, cdn); },
    async dosage(frm, cdt, cdn)       { await sync_row(cdt, cdn); },
    async period(frm, cdt, cdn)       { await sync_row(cdt, cdn); },
    async dosage_form(frm, cdt, cdn)  { await sync_row(cdt, cdn); },
    // When a new row editor opens
    async form_render(frm, cdt, cdn)  { await sync_row(cdt, cdn); },
  });
}

// Safety net on PE save (covers alt grids if present)
frappe.ui.form.on("Patient Encounter", {
  async before_save(frm) {
    const tables = [
      "drug_prescription",
      "sr_homeopathy_drug_prescription",
      "sr_allopathy_drug_prescription",
    ];
    for (const t of tables) {
      for (const r of (frm.doc[t] || [])) {
        await sync_row(r.doctype, r.name);
      }
    }
  },
});
