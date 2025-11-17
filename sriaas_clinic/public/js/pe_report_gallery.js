// sriaas_clinic/public/js/pe_report_gallery.js
frappe.ui.form.on('Patient Encounter', {
    refresh: function(frm) {
        render_medical_reports_preview(frm);
    },
    after_save: function(frm) {
        // update gallery after save (so attachments uploaded using paperclip are picked)
        render_medical_reports_preview(frm);
    }
});

function render_medical_reports_preview(frm) {
    const wrapper = frm.get_field('sr_medical_reports_preview');
    if (!wrapper) return;

    // clear first
    wrapper.$wrapper.empty();

    if (!frm.doc.name) {
        wrapper.$wrapper.html('<div class="small">Save the encounter to see uploaded reports.</div>');
        return;
    }

    // show loader
    wrapper.$wrapper.html('<div class="text-muted small">Loading reports…</div>');

    // call server to get File records attached to this doc
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "File",
            filters: [
                ["File", "attached_to_doctype", "=", "Patient Encounter"],
                ["File", "attached_to_name", "=", frm.doc.name]
            ],
            fields: ["file_url", "file_name", "is_private", "file_size"],
            order_by: "creation desc",
            limit_page_length: 200
        },
        callback: function(r) {
            const files = r.message || [];
            wrapper.$wrapper.empty();

            if (!files.length) {
                wrapper.$wrapper.html('<div class="small text-muted">No reports uploaded yet. Use the paperclip or the "Medical Reports" attach field to upload.</div>');
                return;
            }

            const gallery = $('<div style="display:flex;flex-wrap:wrap;gap:8px"></div>');
            files.forEach(function(f) {
                // Construct the public link. If private, use the download endpoint.
                let url = f.file_url;
                if (f.is_private) {
                    url = '/api/method/frappe.utils.file_manager.download_file?file_url=' + encodeURIComponent(f.file_url);
                }
                // small thumbnail / icon — for images show the image, for PDFs show an icon
                const ext = (f.file_name || '').split('.').pop().toLowerCase();
                let thumb;
                if (['png','jpg','jpeg','gif','webp','bmp'].indexOf(ext) !== -1) {
                    thumb = $(`<a href="${url}" target="_blank" title="${f.file_name}"><img src="${url}" style="height:96px;max-width:120px;border:1px solid #e7e7e7;padding:4px;border-radius:4px;object-fit:cover"></a>`);
                } else {
                    // generic icon for non-images (PDF, docx etc.)
                    thumb = $(`<a href="${url}" target="_blank" title="${f.file_name}" style="display:inline-block;text-align:center;width:120px"><div style="height:80px;display:flex;align-items:center;justify-content:center;border:1px solid #e7e7e7;border-radius:4px;padding:8px"><span style="font-size:28px;line-height:1.0">📄</span></div><div style="font-size:12px;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${f.file_name}</div></a>`);
                }

                gallery.append($('<div>').append(thumb));
            });

            wrapper.$wrapper.append(gallery);
        }
    });
}
