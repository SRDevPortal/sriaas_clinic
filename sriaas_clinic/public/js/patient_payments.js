frappe.ui.form.on("Patient", {
	refresh(frm) {
		// only when saved and when Patient is linked to a Customer
		if (frm.is_new() || !frm.doc.customer) return;

		// clear table before reloading
		frm.clear_table("sr_payment_entry_list");

		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Payment Entry",
				filters: {
					party_type: "Customer",
					party: frm.doc.customer,
					docstatus: 1, // Submitted; remove if you want drafts too
				},
				fields: ["name", "posting_date", "paid_amount", "mode_of_payment"],
				order_by: "posting_date desc",
				limit_page_length: 100,
			},
			callback(r) {
				(r.message || []).forEach((entry) => {
					const row = frm.add_child("sr_payment_entry_list");
					row.sr_payment_entry = entry.name;
					row.sr_posting_date = entry.posting_date;
					row.sr_paid_amount = entry.paid_amount;
					row.sr_mode_of_payment = entry.mode_of_payment;
				});
				frm.refresh_field("sr_payment_entry_list");
			},
		});
	},
});
