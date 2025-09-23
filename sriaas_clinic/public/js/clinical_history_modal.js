// sriaas_clinic/public/js/clinical_history_modal.js

// ---------- helpers ----------
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
    _clean(e.sr_notes).length
  );
}

// Global + content CSS (cards, sticky footer, etc)
function _css_block() {
  return `
  <style>
    body { font-family: Arial, sans-serif; }
    .history-wrap { padding: 16px 16px 0; }
    .header { border-bottom: 1px solid #e7e7e7; margin-bottom: 12px; padding-bottom: 8px; }
    .meta { margin: 6px 0; font-size: 14px; color: #333; }
    .section-title { font-size: 15px; margin: 10px 0 6px; font-weight: 600; }
    .row-line { margin: 2px 0; }
    .muted { color: #666; }

    /* Card */
    .enc-card {
      border: 1px solid #eee;
      border-radius: 12px;
      box-shadow: 0 1px 6px rgba(0,0,0,0.06);
      padding: 12px 14px;
      margin: 12px 0;
      background: #fff;
    }
    .enc-head { margin-bottom: 6px; font-weight: 600; }

    /* Sticky action bar inside dialog body */
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

    /* Print tidy */
    @media print {
      .dialog-actions { display:none !important; }
      .enc-card { page-break-inside: avoid; }
    }
  </style>`;
}

function _build_header(patient, encounter) {
  return `
  <div class="header">
    <div class="meta"><b>Patient Name:</b> ${_esc(patient.patient_name || patient.first_name || patient.name)}</div>
    <div class="meta"><b>Gender:</b> ${_esc(patient.sex || patient.gender || "-")}
      &nbsp;&nbsp; <b>Mobile:</b> ${_esc(patient.mobile || patient.mobile_no || patient.sr_mobile_no || "-")}</div>
    <div class="meta"><b>Patient ID:</b> ${_esc(patient.sr_patient_id || patient.patient_id || patient.name)}</div>
    ${encounter ? `<div class="meta"><b>Encounter:</b> ${_esc(encounter.name)}</div>` : ""}
    <div class="meta muted">Generated on ${_esc(frappe.datetime.str_to_user(frappe.datetime.nowdate()))}</div>
  </div>`;
}

function _build_blocks(rows) {
  return rows.map((e) => {
    const date_txt = e.encounter_date ? frappe.datetime.str_to_user(e.encounter_date) : "-";
    const practitioner = e.practitioner_name || e.practitioner || "-";
    return `
      <div class="enc-card">
        <div class="enc-head">
          <b>Encounter:</b> ${_esc(e.name)}
          &nbsp;&nbsp; <b>Date:</b> ${_esc(date_txt)}
          &nbsp;&nbsp; <b>Practitioner:</b> ${_esc(practitioner)}
        </div>

        <div class="section-title">Complaints</div>
        <div class="row-line">${_esc(_clean(e.sr_complaints))}</div>

        <div class="section-title">Observations</div>
        <div class="row-line">${_esc(_clean(e.sr_observations))}</div>

        <div class="section-title">Investigations</div>
        <div class="row-line">${_esc(_clean(e.sr_investigations))}</div>

        <div class="section-title">Notes</div>
        <div class="row-line">${_esc(_clean(e.sr_notes))}</div>
      </div>`;
  }).join("");
}

async function _fetch_patient(patient_name) {
  const { message: patient = {} } = await frappe.call({
    method: "frappe.client.get",
    args: { doctype: "Patient", name: patient_name }
  });
  return patient;
}

async function _fetch_encounters(patient_name) {
  const { message: allRows = [] } = await frappe.call({
    method: "frappe.client.get_list",
    args: {
      doctype: "Patient Encounter",
      filters: { patient: patient_name },
      fields: [
        "name", "encounter_date", "practitioner", "practitioner_name",
        "sr_complaints", "sr_observations", "sr_investigations", "sr_notes"
      ],
      order_by: "encounter_date asc, creation asc",
      limit_page_length: 1000
    }
  });
  return allRows.filter(_has_notes);
}

// opens a modal with history; prints same content on click
async function openClinicalHistoryDialog({ patient_name, current_encounter = null }) {
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

    // Make dialog extra wide & tall; enable internal scrolling
    const $dlg = d.$wrapper.find(".modal-dialog");
    $dlg.addClass("modal-xl");                                // Bootstrap 5 wide
    d.$wrapper.find(".modal-body").css({
      maxHeight: "80vh",
      overflow: "auto",
      paddingBottom: 0
    });

    // loading
    d.$body.html("<div class='text-muted' style='padding:16px;'>Loading clinical history…</div>");
    d.show();

    const [patient, rows] = await Promise.all([
      _fetch_patient(patient_name),
      _fetch_encounters(patient_name)
    ]);

    const header = _build_header(patient, current_encounter);
    const blocks = rows.length
      ? _build_blocks(rows)
      : "<p class='muted' style='padding:0 16px;'>No encounters with Clinical Notes found.</p>";

    const inner = `
      ${_css_block()}
      <div class="history-wrap">
        ${header}
        ${blocks}
        <div class="dialog-actions">
          <button class="btn btn-primary" data-action="print-history">🖨️ Print</button>
          <button class="btn btn-default" data-action="close">Close</button>
        </div>
      </div>`;

    d.$body.html(inner);

    // Print the same content
    d.$body.find('[data-action="print-history"]').on("click", () => {
      const w = window.open("", "_blank");
      w.document.write(`<html><head><title>Patient Clinical History</title></head><body>${inner}</body></html>`);
      w.document.close();
      setTimeout(() => { try { w.focus(); w.print(); } catch(e) {} }, 150);
    });
    d.$body.find('[data-action="close"]').on("click", () => d.hide());

  } catch (err) {
    console.error("openClinicalHistoryDialog error:", err);
    frappe.msgprint("Could not load Clinical History (see console).");
  }
}

// ---------- buttons on both doctypes ----------
frappe.ui.form.on("Patient", {
  refresh(frm) {
    if (!frm.doc || frm.is_new()) return;
    frm.add_custom_button("🖨️ Clinical History", () =>
      openClinicalHistoryDialog({ patient_name: frm.doc.name })
    );
  },
});

frappe.ui.form.on("Patient Encounter", {
  refresh(frm) {
    if (!frm.doc || !frm.doc.patient) return;
    frm.add_custom_button("🖨️ Clinical History", () =>
      openClinicalHistoryDialog({ patient_name: frm.doc.patient, current_encounter: frm.doc })
    );
  },
});
