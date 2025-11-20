// patient_encounter_attachments.js (improved)
// Combines autosave-blocking and gallery rendering for attachments.
// Fields covered: sr_pe_payment_proof, sr_medical_reports
(function () {
  const ATTACH_FIELDS = ['sr_pe_payment_proof', 'sr_medical_reports'];
  const CLEAR_AFTER_MS = 4000; // safety window (ms) - bump for large files
  const RENDER_DEBOUNCE_MS = 400; // debounce gallery render

  // small debounce helper
  function debounce(fn, wait) {
    let t;
    return function () {
      const args = arguments;
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  // --------- Gallery rendering ----------
  const render_medical_reports_preview = debounce(function (frm) {
    const wrapper_field = 'sr_medical_reports_preview';
    const wrapper = frm.get_field(wrapper_field);
    if (!wrapper) return;

    wrapper.$wrapper.empty();

    if (!frm.doc.name) {
      wrapper.$wrapper.html('<div class="small text-muted">Save the encounter to see uploaded reports.</div>');
      return;
    }

    wrapper.$wrapper.html('<div class="small text-muted">Loading reports…</div>');

    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "File",
        filters: [
          ["File", "attached_to_doctype", "=", "Patient Encounter"],
          ["File", "attached_to_name", "=", frm.doc.name]
        ],
        fields: ["file_url", "file_name", "is_private", "file_size", "creation"],
        order_by: "creation desc",
        limit_page_length: 200
      },
      callback: function (r) {
        try {
          const files = r.message || [];
          wrapper.$wrapper.empty();

          if (!files.length) {
            wrapper.$wrapper.html('<div class="small text-muted">No reports uploaded yet. Use the paperclip or the "Medical Reports" attach field to upload multiple files.</div>');
            return;
          }

          const gallery = $('<div style="display:flex;flex-wrap:wrap;gap:8px"></div>');
          files.forEach(function (f) {
            let url = f.file_url;
            if (f.is_private) {
              url = '/api/method/frappe.utils.file_manager.download_file?file_url=' + encodeURIComponent(f.file_url);
            }

            const ext = (f.file_name || '').split('.').pop().toLowerCase();
            let thumb;
            if (['png','jpg','jpeg','gif','webp','bmp'].indexOf(ext) !== -1) {
              thumb = $(`<a href="${url}" target="_blank" title="${f.file_name}"><img src="${url}" style="height:96px;max-width:120px;border:1px solid #e7e7e7;padding:4px;border-radius:4px;object-fit:cover"></a>`);
            } else if (ext === 'pdf') {
              thumb = $(`<a href="${url}" target="_blank" title="${f.file_name}" style="display:inline-block;text-align:center;width:120px"><div style="height:80px;display:flex;align-items:center;justify-content:center;border:1px solid #e7e7e7;border-radius:4px;padding:8px"><span style="font-size:28px;line-height:1.0">📕</span></div><div style="font-size:12px;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${f.file_name}</div></a>`);
            } else {
              thumb = $(`<a href="${url}" target="_blank" title="${f.file_name}" style="display:inline-block;text-align:center;width:120px"><div style="height:80px;display:flex;align-items:center;justify-content:center;border:1px solid #e7e7e7;border-radius:4px;padding:8px"><span style="font-size:28px;line-height:1.0">📄</span></div><div style="font-size:12px;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${f.file_name}</div></a>`);
            }

            gallery.append($('<div>').append(thumb));
          });

          wrapper.$wrapper.append(gallery);
        } catch (err) {
          console.error('Error rendering files', err);
          wrapper.$wrapper.html('<div class="small text-muted">Unable to load reports.</div>');
        }
      },
      error: function (err) {
        console.error('frappe.call error', err);
        const wrapper = frm.get_field('sr_medical_reports_preview');
        if (wrapper) wrapper.$wrapper.html('<div class="small text-muted">Unable to load reports (server error).</div>');
      }
    });
  }, RENDER_DEBOUNCE_MS);

  // --------- Autosave blocking + DOM binding ----------
  frappe.ui.form.on('Patient Encounter', {
    onload(frm) {
      if (frm._attachmentsPatched) return;

      // Keep original save
      const originalSave = frm.save.bind(frm);

      frm.save = function (action) {
        // Only swallow framework autosave (no action or 'Save'), never swallow explicit Submit
        if (frm._skipNextSaveDueToAttachment && (!action || action === 'Save')) {
          frm._skipNextSaveDueToAttachment = false;
          return Promise.resolve(frm);
        }
        return originalSave(action);
      };

      frm._attachmentsPatched = true;

      // Bind DOM listener to each attach field wrapper to catch input[file] changes (multi-file)
      const bindFileInputChange = function () {
        try {
          ATTACH_FIELDS.forEach(function (fieldname) {
            const f = frm.get_field(fieldname);
            if (!f || !f.$wrapper) return;

            // Remove previous handler if any, then bind
            f.$wrapper.off('change.sr_attach').on('change.sr_attach', 'input[type=file]', function () {
              frm._skipNextSaveDueToAttachment = true;

              if (frm._skipTimer) clearTimeout(frm._skipTimer);
              frm._skipTimer = setTimeout(function () {
                frm._skipNextSaveDueToAttachment = false;
                frm._skipTimer = null;
              }, CLEAR_AFTER_MS);

              frappe.show_alert({ message: __('Changes not saved yet'), indicator: 'blue' });
            });
          });
        } catch (e) {
          console.error('bindFileInputChange error', e);
        }
      };

      // initial bind
      bindFileInputChange();

      // Rebind on refresh (use off/on to avoid duplicates)
      frm.page.wrapper.off('refresh.sr_attach').on('refresh.sr_attach', bindFileInputChange);

      // initial gallery render
      render_medical_reports_preview(frm);
    },

    refresh(frm) {
      // refresh gallery preview (on every refresh to reflect new uploads)
      render_medical_reports_preview(frm);
    },

    after_save(frm) {
      // ensure gallery updates right after save (attachments via paperclip typically save to File on save)
      render_medical_reports_preview(frm);
    }
  });

  // Consolidated per-field handlers fallback
  const perFieldHandler = function (frm) {
    frm._skipNextSaveDueToAttachment = true;

    if (frm._skipTimer) clearTimeout(frm._skipTimer);
    frm._skipTimer = setTimeout(function () {
      frm._skipNextSaveDueToAttachment = false;
      frm._skipTimer = null;
    }, CLEAR_AFTER_MS);

    frappe.show_alert({ message: __('Changes not saved yet'), indicator: 'blue' });

    // update gallery
    render_medical_reports_preview(frm);
  };

  const handlers = {};
  ATTACH_FIELDS.forEach(function (f) { handlers[f] = perFieldHandler; });
  frappe.ui.form.on('Patient Encounter', handlers);

})();
