// sriaas_clinic/public/js/clinical_history_modal.js

// =====================================================
// 1️⃣ Helper Utilities
// =====================================================
function _esc(t) {
  return frappe.utils.escape_html(t || "-").replace(/\n/g, "<br>");
}

function _clean(t) {
  return (t || "").replace(/<[^>]*>/g, "").replace(/&nbsp;/g, " ").trim();
}

function _has_notes(e) {
  return (
    _clean(e.sr_complaints).length ||
    _clean(e.sr_observations).length ||
    _clean(e.sr_investigations).length ||
    _clean(e.sr_diagnosis).length ||
    _clean(e.sr_notes).length
  );
}

// =====================================================
// 2️⃣ Global + Content CSS
// =====================================================
function _css_block() {
  return `
  <style>
    body { font-family: Arial, sans-serif; }
    .header { border-bottom: 1px solid #e7e7e7; margin-bottom: 12px; padding-bottom: 8px; }
    .meta { margin: 6px 0; font-size: 14px; color: #333; }
    .section-title { font-size: 15px; margin: 10px 0 6px; font-weight: 600; }
    .row-line { margin: 2px 0; }
    .muted { color: #666; }

    .enc-card {
      border: 1px solid #8b8a8a;
      border-radius: 12px;
      box-shadow: 0 1px 6px rgba(0,0,0,0.06);
      padding: 12px 14px;
      margin: 12px 0;
      background: #fff;
    }
    .enc-head { margin-bottom: 6px; font-weight: 600; }
    .enc-card .table { margin: 10px 0px; }

    .med-table {
      width: 100%;
      table-layout: fixed;
    }

    .med-table th,
    .med-table td {
      font-size: 13px;
      padding: 6px 8px;
      vertical-align: top;
      word-wrap: break-word;
    }

    .med-col-no { width: 6%; text-align: center; }
    .med-col-name { width: 34%; }
    .med-col-dosage { width: 15%; text-align: center; }
    .med-col-period { width: 15%; text-align: center; }
    .med-col-form { width: 15%; text-align: center; }

    .dialog-actions {
      position: sticky;
      bottom: 0;
      z-index: 1;
      background: #fff;
      padding: 10px 16px;
      border-top: 1px solid #eee;
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 12px;
    }

    .dialog-actions [data-action="print-history"] {
      display: none !important;
    }

    @media print {
      .dialog-actions { display:none !important; }
      .enc-card { page-break-inside: avoid; }
    }
  </style>`;
}

// =====================================================
// 3️⃣ UI Builders
// =====================================================

// Header block
function _build_header(patient) {
  return `
  <div class="header">
    <div class="meta"><b>Patient Name:</b> ${_esc(patient.patient_name || patient.first_name || patient.name)}</div>
    <div class="meta"><b>Patient ID:</b> ${_esc(patient.sr_patient_id || patient.patient_id || patient.name)}</div>
    <div class="meta"><b>Gender:</b> ${_esc(patient.sex || patient.gender || "-")}</div>
    <div class="meta">
      <b>Mobile:</b> ${_esc(patient.mobile || patient.mobile_no || patient.sr_mobile_no || "-")}
      &nbsp;&nbsp;
      <b>Phone:</b> ${_esc(patient.phone || patient.phone_no || patient.sr_phone_no || "-")}
    </div>
  </div>`;
}

// Medication table
function _render_med_table(title, rows) {
  if (!rows || !rows.length) return "";

  const trs = rows.map((r, i) => `
    <tr>
      <td class="med-col-no">${i + 1}</td>
      <td class="med-col-name">${_esc(r.medication || r.drug || "-")}</td>
      <td class="med-col-dosage">${_esc(r.dosage || "-")}</td>
      <td class="med-col-period">${_esc(r.period || "-")}</td>
      <td class="med-col-form">${_esc(r.dosage_form || "-")}</td>
      <td class="med-col-form">${_esc(r.sr_drug_instruction || "-")}</td>
    </tr>
  `).join("");

  return `
    <div class="section-title">${title}</div>
    <table class="table table-bordered table-sm med-table">
      <thead>
        <tr>
          <th class="med-col-no">No</th>
          <th class="med-col-name">Medication</th>
          <th class="med-col-dosage">Dosage</th>
          <th class="med-col-period">Period</th>
          <th class="med-col-form">Form</th>
          <th class="med-col-form">Instruction</th>
        </tr>
      </thead>
      <tbody>${trs}</tbody>
    </table>`;
}

// Encounter cards
function _build_blocks(rows) {
  return rows.map((e) => {
    const date_txt = e.encounter_date
      ? frappe.datetime.str_to_user(e.encounter_date)
      : "-";

    const section = (title, val) => {
      const cleaned = _clean(val);
      if (!cleaned) return "";
      return `
        <div class="section-title">${title}</div>
        <div class="row-line">${_esc(cleaned)}</div>`;
    };

    return `
      <div class="enc-card">
        <div class="enc-head">
          <b>Encounter:</b> ${_esc(e.name)} &nbsp;&nbsp;
          <b>Date:</b> ${_esc(date_txt)}
        </div>

        ${section("Complaints", e.sr_complaints)}
        ${section("Observations", e.sr_observations)}
        ${section("Investigations", e.sr_investigations)}
        ${section("Diagnosis", e.sr_diagnosis)}
        ${section("Notes", e.sr_notes)}

        ${_render_med_table("Ayurvedic Medications", e.drug_prescription)}
        ${_render_med_table("Homeopathy Medications", e.sr_homeopathy_drug_prescription)}
        ${_render_med_table("Allopathy Medications Considered", e.sr_allopathy_drug_prescription)}
      </div>`;
  }).join("");
}

// =====================================================
// 4️⃣ Data Fetchers
// =====================================================
async function _fetch_patient(patient_name) {
  const { message: patient = {} } = await frappe.call({
    method: "frappe.client.get",
    args: { doctype: "Patient", name: patient_name }
  });
  return patient;
}

async function _fetch_encounters(patient_name) {
  const { message: rows = [] } = await frappe.call({
    method: "frappe.client.get_list",
    args: {
      doctype: "Patient Encounter",
      filters: { patient: patient_name },
      fields: ["name", "encounter_date"],
      order_by: "encounter_date desc, creation desc",
      limit_page_length: 100
    }
  });

  const full = await Promise.all(
    rows.map(r =>
      frappe.call({
        method: "frappe.client.get",
        args: { doctype: "Patient Encounter", name: r.name }
      }).then(res => res.message)
    )
  );

  return full.filter(_has_notes);
}

// =====================================================
// 5️⃣ Main Controller
// =====================================================
async function openClinicalHistoryDialog({ patient_name }) {
  try {
    if (!patient_name) {
      frappe.msgprint("No Patient set.");
      return;
    }

    const d = new frappe.ui.Dialog({
      title: "Patient Clinical History",
      size: "large",
      static: true
    });

    const $dlg = d.$wrapper.find(".modal-dialog");
    $dlg.addClass("modal-xl");
    d.$wrapper.find(".modal-body").css({
      maxHeight: "80vh",
      overflow: "auto",
      paddingBottom: 0
    });

    d.$body.html("<div class='text-muted' style='padding:16px;'>Loading clinical history...</div>");
    d.show();

    const [patient, rows] = await Promise.all([
      _fetch_patient(patient_name),
      _fetch_encounters(patient_name)
    ]);

    const header = _build_header(patient);
    const blocks = rows.length
      ? _build_blocks(rows)
      : "<p class='muted' style='padding:0 16px;'>No encounters with Clinical Notes found.</p>";

    const inner = `
      ${_css_block()}
      <div class="history-wrap">
        ${header}
        ${blocks}
        <div class="dialog-actions">
          <button class="btn btn-primary" data-action="print-history">Print</button>
          <button class="btn btn-default" data-action="close">Close</button>
        </div>
      </div>`;

    d.$body.html(inner);

    d.$body.find('[data-action="print-history"]').on("click", () => {
      const w = window.open("", "_blank");
      w.document.write(`<html><body>${inner}</body></html>`);
      w.document.close();
      setTimeout(() => { w.focus(); w.print(); }, 150);
    });

    d.$body.find('[data-action="close"]').on("click", () => d.hide());

  } catch (err) {
    console.error("Clinical History Error:", err);
    frappe.msgprint("Could not load Clinical History.");
  }
}

// =====================================================
// 6️⃣ Event Bindings
// =====================================================
frappe.ui.form.on("Patient", {
  refresh(frm) {
    if (!frm.doc || frm.is_new()) return;
    frm.add_custom_button("Clinical History", () =>
      openClinicalHistoryDialog({ patient_name: frm.doc.name })
    );
  },
});

frappe.ui.form.on("Patient Encounter", {
  refresh(frm) {
    if (!frm.doc || !frm.doc.patient) return;
    frm.add_custom_button("Clinical History", () =>
      openClinicalHistoryDialog({ patient_name: frm.doc.patient })
    );
  },
});
