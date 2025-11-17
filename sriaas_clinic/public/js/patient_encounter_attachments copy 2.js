// patient_encounter_attachments.js
// Option A — safe multi-file upload: upload via upload_file, DO NOT add child rows.
// Renders gallery from File doctype. Blocks autosave while upload is happening.

(function () {
  const PAYMENT_PROOF_FIELD = 'sr_pe_payment_proof'; // preserve behavior for this field
  const PREVIEW_FIELD = 'sr_medical_reports_preview'; // HTML field where gallery and upload UI live
  const CLEAR_AFTER_MS = 4000; // ms to keep autosave blocked during uploads
  const RENDER_DEBOUNCE_MS = 300;

  // debounce helper
  function debounce(fn, wait) {
    let t;
    return function () {
      const args = arguments;
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  // -------------------------
  // Render gallery (reads File doctype attached to Patient Encounter)
  // -------------------------
  const render_medical_reports_preview = debounce(function (frm) {
    const wrapper = frm.get_field(PREVIEW_FIELD);
    if (!wrapper) return;
    wrapper.$wrapper.empty();

    if (!frm.doc.name) {
      wrapper.$wrapper.html('<div class="small text-muted">Save the encounter to upload and view reports.</div>');
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
            wrapper.$wrapper.html('<div class="small text-muted">No reports uploaded yet. Use "Upload reports" to add files.</div>');
            return;
          }

          const gallery = $('<div style="display:flex;flex-wrap:wrap;gap:8px"></div>');
          files.forEach(function (f) {
            let url = f.file_url || '';
            // If path looks like /private/files/... or /files/... OR file is private,
            // use the download_file wrapper to ensure permission & correct serving.
            if (f.is_private || url.startsWith('/private') || url.startsWith('private') || url.startsWith('/files') || url.startsWith('files')) {
              url = '/api/method/frappe.utils.file_manager.download_file?file_url=' + encodeURIComponent(url);
            } else {
              // make sure relative urls start with slash
              if (url && url.charAt(0) !== '/') url = '/' + url;
            }

            const filename = f.file_name || (url.split('/').pop() || 'report');
            const ext = (filename || '').split('.').pop().toLowerCase();
            let thumb;

            if (['png','jpg','jpeg','gif','webp','bmp'].indexOf(ext) !== -1) {
              thumb = $(`<a href="${url}" target="_blank" title="${frappe.utils.escape_html(filename)}"><img src="${url}" style="height:96px;max-width:120px;border:1px solid #e7e7e7;padding:4px;border-radius:4px;object-fit:cover"></a>`);
            } else if (ext === 'pdf') {
              thumb = $(`<a href="${url}" target="_blank" title="${frappe.utils.escape_html(filename)}" style="display:inline-block;text-align:center;width:120px"><div style="height:80px;display:flex;align-items:center;justify-content:center;border:1px solid #e7e7e7;border-radius:4px;padding:8px"><span style="font-size:28px">📕</span></div><div style="font-size:12px;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${frappe.utils.escape_html(filename)}</div></a>`);
            } else {
              thumb = $(`<a href="${url}" target="_blank" title="${frappe.utils.escape_html(filename)}" style="display:inline-block;text-align:center;width:120px"><div style="height:80px;display:flex;align-items:center;justify-content:center;border:1px solid #e7e7e7;border-radius:4px;padding:8px"><span style="font-size:28px">📄</span></div><div style="font-size:12px;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${frappe.utils.escape_html(filename)}</div></a>`);
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
        const wrapper2 = frm.get_field(PREVIEW_FIELD);
        if (wrapper2) wrapper2.$wrapper.html('<div class="small text-muted">Unable to load reports (server error).</div>');
      }
    });
  }, RENDER_DEBOUNCE_MS);

  // -------------------------
  // Create upload UI inside the preview wrapper and perform uploads
  // (IMPORTANT: we do NOT create child rows on the parent; upload_file attaches File to the Encounter)
  // -------------------------
  function create_reports_upload_ui(frm) {
    const wrapper = frm.get_field(PREVIEW_FIELD);
    if (!wrapper) return;

    // avoid double-binding UI
    if (wrapper.$wrapper.data('sr-upload-ui')) return;
    wrapper.$wrapper.data('sr-upload-ui', true);

    const uploadArea = $(`
      <div class="sr-upload-area" style="margin-bottom:8px;display:flex;gap:8px;align-items:center">
        <label class="btn btn-default btn-sm" style="margin:0;padding:6px 10px;cursor:pointer;">
          Upload reports
          <input type="file" multiple style="display:none" />
        </label>
        <div class="sr-upload-status small text-muted">Select files to upload (multiple allowed)</div>
      </div>
    `);

    // prepend so preview thumbnails show after this
    wrapper.$wrapper.prepend(uploadArea);

    const fileInput = uploadArea.find('input[type=file]')[0];
    const statusEl = uploadArea.find('.sr-upload-status');

    // helper: upload single file via upload_file endpoint
    async function uploadFile(file, frm) {
      const fd = new FormData();
      fd.append('file', file, file.name);
      fd.append('doctype', 'Patient Encounter');
      fd.append('docname', frm.doc.name);
      fd.append('is_private', 1);
      const res = await fetch('/api/method/upload_file', {
        method: 'POST',
        body: fd,
        credentials: 'same-origin'
      });
      const json = await res.json();
      if (!res.ok || json.exc) {
        throw new Error(JSON.stringify(json));
      }
      return json.message; // message contains file_url, file_name, name (File docname)
    }

    fileInput.addEventListener('change', async function (ev) {
      const files = Array.from(ev.target.files || []);
      if (!files.length) return;

      if (!frm.doc.name) {
        frappe.msgprint(__('Please save the Encounter before uploading reports.'));
        fileInput.value = '';
        return;
      }

      // block autosave while upload in progress
      frm._skipNextSaveDueToAttachment = true;
      frm._sr_upload_in_progress = true;

      statusEl.text(`Uploading ${files.length} file(s)...`);
      uploadArea.find('label').addClass('disabled');

      const uploaded = [];
      const errors = [];

      // sequential upload (safer)
      for (let i = 0; i < files.length; i++) {
        const f = files[i];
        try {
          statusEl.text(`Uploading ${i+1}/${files.length}: ${f.name}`);
          const file_doc = await uploadFile(f, frm);
          uploaded.push(file_doc);

          // IMPORTANT: DO NOT create child rows in the parent form here.
          // upload_file already attached the File to the Patient Encounter (attached_to_doctype/attached_to_name).
          // We'll refresh gallery (which reads File doctype) after uploads complete.
        } catch (err) {
          console.error('upload error', err);
          errors.push({ file: f.name, error: err });
        }
      }

      frm._sr_upload_in_progress = false;

      // short grace and then allow autosave again
      if (frm._skipTimer) clearTimeout(frm._skipTimer);
      frm._skipTimer = setTimeout(function () {
        frm._skipNextSaveDueToAttachment = false;
        frm._skipTimer = null;
      }, 500);

      uploadArea.find('label').removeClass('disabled');
      fileInput.value = '';

      if (errors.length) {
        statusEl.html(`<span style="color:#b94a48">Uploaded ${uploaded.length} files; ${errors.length} failed.</span>`);
        let msg = `<div>Uploaded ${uploaded.length} files. ${errors.length} failed:</div><ul>`;
        errors.forEach(e => { msg += `<li>${frappe.utils.escape_html(e.file)} — ${frappe.utils.escape_html(String(e.error).slice(0,200))}</li>`; });
        msg += '</ul>';
        frappe.msgprint({ title: __('Upload result'), message: msg, indicator: 'red' });
      } else {
        statusEl.text(`Uploaded ${uploaded.length} files.`);
        frappe.show_alert({ message: __('Reports uploaded'), indicator: 'green' });
      }

      // Do not auto-save the parent form. Mark it dirty so Save button is enabled if user changed other fields.
      try {
        frm.doc.__unsaved = true;
        frm.dirty();
      } catch (e) {
        console.warn('Could not mark form dirty', e);
      }

      // re-render gallery (reads File doctype)
      setTimeout(function () { render_medical_reports_preview(frm); }, 300);
    });
  }

  // -------------------------
  // Block autosave when user interacts with attach inputs (payment proof or any file input)
  // -------------------------
  function bind_attach_autosave_block(frm) {
    // patch save once
    if (!frm._attachmentsPatched) {
      const originalSave = frm.save.bind(frm);
      frm.save = function (action) {
        if (frm._skipNextSaveDueToAttachment && (!action || action === 'Save')) {
          frm._skipNextSaveDueToAttachment = false;
          return Promise.resolve(frm);
        }
        return originalSave(action);
      };
      frm._attachmentsPatched = true;
    }

    // specific handler for payment proof (keeps your previous short window behaviour)
    const pf = frm.get_field(PAYMENT_PROOF_FIELD);
    if (pf && pf.$wrapper) {
      // namespace the event to avoid duplicates
      pf.$wrapper.off('change.sr_payment_proof').on('change.sr_payment_proof', 'input[type=file]', function () {
        frm._skipNextSaveDueToAttachment = true;
        if (frm._skipTimer) clearTimeout(frm._skipTimer);
        frm._skipTimer = setTimeout(function () {
          frm._skipNextSaveDueToAttachment = false;
          frm._skipTimer = null;
        }, 1500);
        frappe.show_alert({ message: __('Changes not saved yet'), indicator: 'blue' });
      });
    }

    // global catch-all for native file inputs (also catches inputs rendered inside table rows/widgets)
    // Namespaced once on document
    if (!document._sr_global_file_listener) {
      document.addEventListener('change', function (e) {
        try {
          const el = e.target;
          if (el && el.tagName === 'INPUT' && el.type === 'file') {
            const frm = window.cur_frm;
            if (frm) {
              frm._skipNextSaveDueToAttachment = true;
              if (frm._skipTimer) clearTimeout(frm._skipTimer);
              frm._skipTimer = setTimeout(function () {
                frm._skipNextSaveDueToAttachment = false;
                frm._skipTimer = null;
              }, CLEAR_AFTER_MS);
              frappe.show_alert({ message: __('Changes not saved yet'), indicator: 'blue' });
            }
          }
        } catch (err) {
          // swallow
        }
      }, true);
      document._sr_global_file_listener = true;
    }
  }

  // -------------------------
  // Wire into form events
  // -------------------------
  frappe.ui.form.on('Patient Encounter', {
    onload(frm) {
      bind_attach_autosave_block(frm);
      create_reports_upload_ui(frm);
      render_medical_reports_preview(frm);
    },
    refresh(frm) {
      create_reports_upload_ui(frm);
      render_medical_reports_preview(frm);
    },
    after_save(frm) {
      // if user saved, refresh gallery to reflect newly persisted files (if any)
      render_medical_reports_preview(frm);
    }
  });

})();
