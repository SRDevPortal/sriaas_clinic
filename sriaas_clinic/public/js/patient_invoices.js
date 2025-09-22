frappe.ui.form.on("Patient", {
	refresh(frm) {
		if (frm.is_new()) return;

		// clear table before reloading
		frm.clear_table("sr_sales_invoice_list");

		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Sales Invoice",
				filters: {
					patient: frm.doc.name,
					docstatus: 1, // Submitted only; remove if you want drafts too
				},
				fields: ["name", "posting_date", "grand_total", "outstanding_amount"],
				order_by: "posting_date desc",
				limit_page_length: 100,
			},
			callback(r) {
				(r.message || []).forEach((inv) => {
					const row = frm.add_child("sr_sales_invoice_list");
					row.sr_invoice_no = inv.name;
					row.sr_posting_date = inv.posting_date;
					row.sr_grand_total = inv.grand_total;
					row.sr_outstanding = inv.outstanding_amount;
				});
				frm.refresh_field("sr_sales_invoice_list");
			},
		});
	},
});
