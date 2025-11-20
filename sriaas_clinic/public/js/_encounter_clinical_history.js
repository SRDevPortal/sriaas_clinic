frappe.ui.form.on("Patient Encounter", {
  refresh(frm) {
    if (frm.is_new()) return;

    frm.add_custom_button("Print History", async () => {
      try {
        const esc = (t) => frappe.utils.escape_html(t || "-").replace(/\n/g, "<br>");
        const clean = (t) => (t || "").replace(/<[^>]*>/g, "").replace(/&nbsp;/g, " ").trim();

        // 1) Get current encounter details
        const encounter = frm.doc;

        // 2) Fetch patient details from Patient doctype
        const { message: patient = {} } = await frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Patient",
                name: encounter.patient,   // link field
            },
        });

        // 3) Fetch ALL encounters for the same patient
        const { message: allRows = [] } = await frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Patient Encounter",
                filters: { patient: encounter.patient },
                fields: [
                "name", "encounter_date", "practitioner", "practitioner_name",
                "sr_complaints", "sr_observations", "sr_investigations", "sr_notes"
                ],
                order_by: "encounter_date asc, creation asc",
                limit_page_length: 1000
            }
        });

        // 4) Filter to only rows with at least one clinical note
        const rows = allRows.filter(
            (e) =>
                clean(e.sr_complaints).length ||
                clean(e.sr_observations).length ||
                clean(e.sr_investigations).length ||
                clean(e.sr_notes).length
        );

        const css = `
          <style>
            body { font-family: Arial, sans-serif; padding: 16px; }
            .header { border-bottom: 1px solid #ddd; margin-bottom: 12px; }
            .meta { margin: 6px 0; font-size: 14px; color: #333; }
            .section-title { font-size: 16px; margin: 14px 0 6px; font-weight: bold; }
            .encounter { padding: 12px 0; }
            .encounter + .encounter { border-top: 1px dashed #ccc; margin-top: 12px; }
            .row-line { margin: 2px 0; }
            .muted { color: #666; }
            .print-actions { margin: 16px 0 8px; }
            @media print { .print-actions { display: none !important; } .encounter { page-break-inside: avoid; } }
          </style>
        `;

        const header = `
            <div class="header">
                <h2>Patient Clinical History</h2>
                <div class="meta"><b>Patient Name:</b> ${esc(patient.patient_name || patient.first_name || patient.name)}</div>
                <div class="meta"><b>Gender:</b> ${esc(patient.sex || patient.gender || "-")}
                &nbsp;&nbsp; <b>Mobile:</b> ${esc(patient.mobile || patient.mobile_no || patient.sr_mobile_no || "-")}</div>
                <div class="meta"><b>Patient ID:</b> ${esc(patient.sr_patient_id || patient.patient_id || patient.name)}</div>
                <div class="meta muted">Generated on ${esc(frappe.datetime.str_to_user(frappe.datetime.nowdate()))}</div>
            </div>
            <div class="print-actions"><button onclick="window.print()">🖨️ Print</button></div>
        `;

        if (!rows.length) {
          const html = `${css}${header}<p class='muted'>No encounters with Clinical Notes found.</p>`;
          const w = window.open("", "_blank");
          w.document.write(
            `<html><head><title>Patient Clinical History</title></head><body>${html}</body></html>`
          );
          w.document.close();
          return;
        }

        const blocks = rows
          .map((e) => {
            const date_txt = e.encounter_date
              ? frappe.datetime.str_to_user(e.encounter_date)
              : "-";
            const practitioner = e.practitioner_name || e.practitioner || "-";
            return `
              <div class="encounter">
                <div class="row-line">
                  <b>Encounter:</b> ${esc(e.name)}
                  &nbsp;&nbsp; <b>Date:</b> ${esc(date_txt)}
                  &nbsp;&nbsp; <b>Practitioner:</b> ${esc(practitioner)}
                </div>
                <div class="section-title">Complaints</div>
                <div class="row-line">${esc(clean(e.sr_complaints))}</div>
                <div class="section-title">Observations</div>
                <div class="row-line">${esc(clean(e.sr_observations))}</div>
                <div class="section-title">Investigations</div>
                <div class="row-line">${esc(clean(e.sr_investigations))}</div>
                <div class="section-title">Notes</div>
                <div class="row-line">${esc(clean(e.sr_notes))}</div>
              </div>
            `;
          })
          .join("");

        const html = `${css}${header}${blocks}`;
        const w = window.open("", "_blank");
        w.document.write(
          `<html><head><title>Patient Clinical History</title></head><body>${html}</body></html>`
        );
        w.document.close();
        setTimeout(() => {
          try {
            w.focus();
          } catch (e) {}
        }, 300);
      } catch (err) {
        console.error("Print Clinical History error:", err);
        frappe.msgprint("Could not generate history (see console).");
      }
    });
  },
});
