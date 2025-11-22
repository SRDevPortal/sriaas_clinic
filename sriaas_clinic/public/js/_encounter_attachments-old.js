// encounter_attachments.js
// Option A — safe multi-file upload: upload via upload_file, DO NOT add child rows.
// Renders gallery from File doctype, supports private-file thumbnails by fetching blobs,
// and opens images in a modal gallery. Blocks autosave while upload is happening.

(function () {
  // const PAYMENT_PROOF_FIELD = 'sr_pe_payment_proof';
  // const PREVIEW_FIELD = 'sr_medical_reports_preview';
  // const CLEAR_AFTER_MS = 4000;
  // const RENDER_DEBOUNCE_MS = 250;

  const CHILD_TABLE_FIELD = 'enc_multi_payments'; // child table fieldname on Patient Encounter
  const CHILD_FILE_FIELD = 'mmp_payment_proof';   // file fieldname inside SR Multi Mode Payment child
  const PREVIEW_FIELD = 'sr_medical_reports_preview';
  const CLEAR_AFTER_MS = 4000;
  const RENDER_DEBOUNCE_MS = 250;

  function debounce(fn, wait) {
    let t;
    return function () {
      const args = arguments;
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  // -------------------------
  // Modal gallery helpers
  // -------------------------
  function create_modal_dom() {
    if (document.getElementById('sr-report-modal')) return;

    const modalHtml = `
      <div id="sr-report-modal" style="display:none;position:fixed;inset:0;z-index:2200;align-items:center;justify-content:center;background:rgba(0,0,0,0.75);">
        <div style="position:relative;max-width:90%;max-height:90%;display:flex;align-items:center;justify-content:center">
          <button id="sr-modal-prev" class="btn" style="position:absolute;left:8px;top:50%;transform:translateY(-50%);z-index:1;background:transparent;border:0;color:#fff;font-size:28px">◀</button>
          <div id="sr-modal-inner" style="max-width:100%;max-height:100%;display:flex;align-items:center;justify-content:center">
            <img id="sr-modal-img" src="" alt="" style="max-width:100%;max-height:100%;border-radius:6px;box-shadow:0 6px 18px rgba(0,0,0,0.5)">
          </div>
          <button id="sr-modal-next" class="btn" style="position:absolute;right:8px;top:50%;transform:translateY(-50%);z-index:1;background:transparent;border:0;color:#fff;font-size:28px">▶</button>
          <button id="sr-modal-close" class="btn" style="position:absolute;right:10px;top:10px;z-index:1;background:transparent;border:0;color:#fff;font-size:22px">✕</button>
        </div>
      </div>
    `;
    const div = document.createElement('div');
    div.innerHTML = modalHtml;
    document.body.appendChild(div.firstElementChild);

    const modal = document.getElementById('sr-report-modal');
    const img = document.getElementById('sr-modal-img');
    const prev = document.getElementById('sr-modal-prev');
    const next = document.getElementById('sr-modal-next');
    const close = document.getElementById('sr-modal-close');

    let currentIndex = -1;
    let items = [];

    function showIndex(i) {
      if (!items || !items.length) return;
      currentIndex = (i + items.length) % items.length;
      const it = items[currentIndex];
      img.src = it.src || it.url; // either blob objectURL or URL
      img.alt = it.name || '';
      modal.style.display = 'flex';
    }

    prev.addEventListener('click', function (e) {
      showIndex(currentIndex - 1);
    });
    next.addEventListener('click', function (e) {
      showIndex(currentIndex + 1);
    });
    close.addEventListener('click', function () { modal.style.display = 'none'; });

    modal.addEventListener('click', function (e) {
      if (e.target === modal) modal.style.display = 'none';
    });

    document.addEventListener('keydown', function (e) {
      if (!modal || modal.style.display !== 'flex') return;
      if (e.key === 'Escape') modal.style.display = 'none';
      if (e.key === 'ArrowLeft') showIndex(currentIndex - 1);
      if (e.key === 'ArrowRight') showIndex(currentIndex + 1);
    });

    // expose setters
    modal._set_items = function (list) { items = list || []; };
    modal._show = showIndex;
  }

  // -------------------------
  // Build a thumbnail element for file record `f`.
  // If private image: fetch blob and use object URL.
  // Returns a Promise resolving to {el, info} where el is jQuery element, info contains {isImage, url, name, blobUrl?}
  // -------------------------
  async function build_thumb_element(f) {
    // f contains: file_url, file_name, is_private
    let rawUrl = f.file_url || '';
    let useDownloadWrapper = false;

    // consider private OR private-like paths
    if (f.is_private || rawUrl.startsWith('/private') || rawUrl.startsWith('private') || rawUrl.startsWith('/files') || rawUrl.startsWith('files')) {
      useDownloadWrapper = true;
    }

    // compute endpoint to use for link (we will use download wrapper for clicking too)
    let linkUrl = rawUrl;
    if (useDownloadWrapper) {
      linkUrl = '/api/method/frappe.utils.file_manager.download_file?file_url=' + encodeURIComponent(rawUrl);
    } else {
      if (rawUrl && rawUrl.charAt(0) !== '/') rawUrl = '/' + rawUrl;
      linkUrl = rawUrl;
    }

    const filename = f.file_name || (rawUrl.split('/').pop() || 'report');
    const ext = (filename || '').split('.').pop().toLowerCase();
    const isImage = ['png','jpg','jpeg','gif','webp','bmp'].indexOf(ext) !== -1;
    const isPdf = ext === 'pdf';

    // create container and placeholder
    const $div = $('<div style="width:120px;text-align:center"></div>');

    // Create clickable anchor (opens in new tab for downloads) but for image clicking we will open modal
    const $a = $(`<a href="${linkUrl}" target="_blank" style="display:inline-block;text-align:center;width:120px"></a>`);

    if (isImage) {
      // Create placeholder img element
      const $img = $(`<img style="height:96px;max-width:120px;border:1px solid #e7e7e7;padding:4px;border-radius:4px;object-fit:cover">`);
      $a.append($img);
      $div.append($a);
      // Caption
      $div.append($(`<div style="font-size:12px;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${frappe.utils.escape_html(filename)}</div>`));

      // For private images, fetch blob and createObjectURL
      if (useDownloadWrapper) {
        try {
          const res = await fetch(linkUrl, { credentials: 'same-origin' });
          if (!res.ok) {
            // failed fetch — show generic icon
            $img.attr('src', '');
            $img.css('background', '#f5f5f5');
            return { el: $div, info: { isImage, url: linkUrl, name: filename, error: res.status } };
          }
          const blob = await res.blob();
          const objUrl = URL.createObjectURL(blob);
          $img.attr('src', objUrl);
          // attach data for modal
          $a.data('sr_blob_url', objUrl);
          return { el: $div, info: { isImage, url: linkUrl, name: filename, blobUrl: objUrl } };
        } catch (err) {
          console.error('fetch blob error', err);
          $img.attr('src', '');
          $img.css('background', '#f5f5f5');
          return { el: $div, info: { isImage, url: linkUrl, name: filename, error: err } };
        }
      } else {
        // non-private images: set src directly
        $img.attr('src', linkUrl);
        // attach url for modal
        $a.data('sr_blob_url', linkUrl);
        return { el: $div, info: { isImage, url: linkUrl, name: filename } };
      }
    } else if (isPdf) {
      const $box = $(`<div style="height:80px;display:flex;align-items:center;justify-content:center;border:1px solid #e7e7e7;border-radius:4px;padding:8px"><span style="font-size:28px">📕</span></div>`);
      $a.append($box);
      $div.append($a);
      $div.append($(`<div style="font-size:12px;margin-top:6px">${frappe.utils.escape_html(filename)}</div>`));
      return { el: $div, info: { isImage: false, url: linkUrl, name: filename } };
    } else {
      const $box = $(`<div style="height:80px;display:flex;align-items:center;justify-content:center;border:1px solid #e7e7e7;border-radius:4px;padding:8px"><span style="font-size:28px">📄</span></div>`);
      $a.append($box);
      $div.append($a);
      $div.append($(`<div style="font-size:12px;margin-top:6px">${frappe.utils.escape_html(filename)}</div>`));
      return { el: $div, info: { isImage: false, url: linkUrl, name: filename } };
    }
  }

  // -------------------------
  // Render gallery (reads File entries attached to encounter), now using build_thumb_element
  // -------------------------
  const render_medical_reports_preview = debounce(async function (frm) {
    const wrapper = frm.get_field(PREVIEW_FIELD);
    if (!wrapper) return;
    wrapper.$wrapper.empty();

    if (!frm.doc.name) {
      wrapper.$wrapper.html('<div class="small text-muted">Save the encounter to upload and view reports.</div>');
      return;
    }

    wrapper.$wrapper.html('<div class="small text-muted">Loading reports…</div>');

    try {
      const r = await frappe.xcall('frappe.client.get_list', {
        doctype: 'File',
        filters: [
          ['File', 'attached_to_doctype', '=', 'Patient Encounter'],
          ['File', 'attached_to_name', '=', frm.doc.name]
        ],
        fields: ['file_url', 'file_name', 'is_private', 'file_size', 'creation', 'name'],
        order_by: 'creation desc',
        limit_page_length: 200
      });

      const files = r || [];
      wrapper.$wrapper.empty();
      if (!files.length) {
        wrapper.$wrapper.html('<div class="small text-muted">No reports uploaded yet. Use "Upload reports" to add files.</div>');
        return;
      }

      // prepare modal DOM
      create_modal_dom();
      const modal = document.getElementById('sr-report-modal');

      const gallery = $('<div style="display:flex;flex-wrap:wrap;gap:8px"></div>');
      const imageItems = []; // for modal gallery

      // Build all thumbs (serially to avoid hammering server), but could be parallel
      for (const f of files) {
        try {
          const result = await build_thumb_element(f);
          gallery.append(result.el);

          // If it's an image, capture source for modal and bind click
          if (result.info && result.info.isImage) {
            // find anchor inside
            const $anchor = result.el.find('a').first();
            const item = { url: result.info.url, name: result.info.name, src: result.info.blobUrl || result.info.url };
            imageItems.push(item);

            // clicking the anchor should open modal instead of opening new tab
            $anchor.on('click', function (evt) {
              evt.preventDefault();
              // set items into modal and open index of this clicked item
              const idx = imageItems.findIndex(it => it.src === item.src && it.name === item.name);
              if (idx === -1) return;
              // ensure modal exists and has utility
              if (modal && modal._set_items) {
                modal._set_items(imageItems);
                modal._show(idx);
              }
            });
          }
        } catch (err) {
          console.error('thumb build failed', err);
        }
      }

      wrapper.$wrapper.append(gallery);
    } catch (err) {
      console.error('Error fetching files', err);
      wrapper.$wrapper.html('<div class="small text-muted">Unable to load reports (server error).</div>');
    }
  }, RENDER_DEBOUNCE_MS);

  // -------------------------
  // Upload UI (same as before) - DOES NOT add child rows
  // -------------------------
  function create_reports_upload_ui(frm) {
    const wrapper = frm.get_field(PREVIEW_FIELD);
    if (!wrapper) return;

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

    wrapper.$wrapper.prepend(uploadArea);

    const fileInput = uploadArea.find('input[type=file]')[0];
    const statusEl = uploadArea.find('.sr-upload-status');

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
      return json.message;
    }

    fileInput.addEventListener('change', async function (ev) {
      const files = Array.from(ev.target.files || []);
      if (!files.length) return;

      if (!frm.doc.name) {
        frappe.msgprint(__('Please save the Encounter before uploading reports.'));
        fileInput.value = '';
        return;
      }

      frm._skipNextSaveDueToAttachment = true;
      frm._sr_upload_in_progress = true;

      statusEl.text(`Uploading ${files.length} file(s)...`);
      uploadArea.find('label').addClass('disabled');

      const uploaded = [];
      const errors = [];

      for (let i = 0; i < files.length; i++) {
        const f = files[i];
        try {
          statusEl.text(`Uploading ${i+1}/${files.length}: ${f.name}`);
          const file_doc = await uploadFile(f, frm);
          uploaded.push(file_doc);
        } catch (err) {
          console.error('upload error', err);
          errors.push({ file: f.name, error: err });
        }
      }

      frm._sr_upload_in_progress = false;

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

      try {
        frm.doc.__unsaved = true;
        frm.dirty();
      } catch (e) {}

      setTimeout(function () { render_medical_reports_preview(frm); }, 300);
    });
  }

  // -------------------------
  // Autosave-blocking (updated to monitor child-table file inputs)
  // -------------------------
  function bind_attach_autosave_block(frm) {
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

    // const pf = frm.get_field(PAYMENT_PROOF_FIELD);
    // if (pf && pf.$wrapper) {
    //   pf.$wrapper.off('change.sr_payment_proof').on('change.sr_payment_proof', 'input[type=file]', function () {
    //     frm._skipNextSaveDueToAttachment = true;
    //     if (frm._skipTimer) clearTimeout(frm._skipTimer);
    //     frm._skipTimer = setTimeout(function () {
    //       frm._skipNextSaveDueToAttachment = false;
    //       frm._skipTimer = null;
    //     }, 1500);
    //     frappe.show_alert({ message: __('Changes not saved yet'), indicator: 'blue' });
    //   });
    // }

    // New: listen for file inputs inside the child table rows
    bind_child_table_file_listeners(frm);
    
    // Keep the global fallback listener for any other file inputs on the page
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
        } catch (err) {}
      }, true);
      document._sr_global_file_listener = true;
    }
  }

  // -------------------------
  // Listen for file inputs inside enc_multi_payments child table
  // -------------------------
  function bind_child_table_file_listeners(frm) {
    try {
      const wrapper = frm.wrapper; // main form wrapper
      if (!wrapper) return;

      // data-fieldname attr is present on the child table container
      const child_selector = `[data-fieldname="${CHILD_TABLE_FIELD}"]`;

      // Use delegated listener on the form wrapper to catch dynamically added inputs
      $(wrapper).off('change.sr_child_file').on('change.sr_child_file', child_selector + ' input[type="file"]', function (ev) {
        try {
          // A file input inside a child row changed — block autosave briefly
          frm._skipNextSaveDueToAttachment = true;
          if (frm._skipTimer) clearTimeout(frm._skipTimer);
          frm._skipTimer = setTimeout(function () {
            frm._skipNextSaveDueToAttachment = false;
            frm._skipTimer = null;
          }, CLEAR_AFTER_MS);

          // notify user (non-intrusive)
          frappe.show_alert({ message: __('Changes not saved yet (file attached in payments)'), indicator: 'blue' });
        } catch (err) {
          console.error('child file listener error', err);
        }
      });
    } catch (err) {
      console.error('bind_child_table_file_listeners error', err);
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
      bind_attach_autosave_block(frm); // rebind in case child table was dynamically changed
      create_reports_upload_ui(frm);
      render_medical_reports_preview(frm);
    },
    after_save(frm) {
      render_medical_reports_preview(frm);
    }
  });

})();
