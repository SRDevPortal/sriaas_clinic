// app/sriaas_clinic/public/js/batch.js
frappe.ui.form.on('Batch', {
    refresh: function(frm) {
        // When the form is refreshed, you can call the API to generate the sequential ID
        frm.add_custom_button(__('Generate Sequential ID'), function() {
            // Get the batch_id and item_name from the form
            var batch_id = frm.doc.batch_id;
            var item_name = frm.doc.item;

            if(batch_id && item_name) {
                // Call the API to generate the sequential batch ID
                frappe.call({
                    method: 'sriaas_clinic.api.batch.generate_sequential_batch_id',
                    args: {
                        batch_id: batch_id,
                        item_name: item_name
                    },
                    callback: function(r) {
                        if(r.message) {
                            // Set the generated ID to the form field
                            frm.set_value('name', r.message);
                        }
                    }
                });
            } else {
                frappe.msgprint(__('Please fill in both Batch ID and Item.'));
            }
        });
    }
});
