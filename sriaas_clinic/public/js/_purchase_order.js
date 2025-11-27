// apps/sriaas_clinic/sriaas_clinic/public/js/purchase_order.js
frappe.ready(function() {
    if (!cur_frm) return;

    // When a child row is added or when item_code changes, create a batch and set it on the row.
    function maybe_create_batch_for_row(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row) return;

        // Only create batch for non-empty item_code and only for new rows (unsaved parent)
        if (!row.item_code) return;

        // Avoid creating multiple batches if batch_no already filled
        if (row.batch_no) return;

        // Optionally skip for service items (uncomment if you maintain item type)
        // if (row.item_name && (row.item_name.toLowerCase().indexOf("service") !== -1)) return;

        // Call server to create batch
        frappe.call({
            method: "sriaas_clinic.api.purchase_order.create_batch_for_item",
            args: {
                item_code: row.item_code,
                warehouse: row.warehouse || null,
                // You can pass expiry_date or batch_name from UI if desired
            },
            freeze: true,
            freeze_message: "Creating batch...",
            callback: function(r) {
                if (!r || !r.message) return;
                const resp = r.message;
                if (resp.success) {
                    // set batch_no to returned batch identifier
                    frappe.model.set_value(cdt, cdn, "batch_no", resp.batch);
                    // refresh the child table so the new value appears
                    frm.refresh_field("items");
                } else {
                    frappe.msgprint({
                        title: __("Batch creation failed"),
                        message: resp.message || __("Unknown error creating batch"),
                        indicator: "orange"
                    });
                }
            }
        });
    }

    // Bind to child table events:
    // When a new row is added
    cur_frm.cscript['items_add'] = function(doc, cdt, cdn) {
        // small defer so fields are present
        setTimeout(function() {
            maybe_create_batch_for_row(cur_frm, cdt, cdn);
        }, 250);
    };

    // When item_code changes in a row
    frappe.ui.form.on('Purchase Order Item', {
        item_code: function(frm, cdt, cdn) {
            maybe_create_batch_for_row(frm, cdt, cdn);
        }
    });

});
