frappe.ui.form.on("Patient", {
    setup(frm) {
        frm.set_query("sr_followup_status", () => ({
            filters: {
                is_active: 1,
            },
            order_by: "sort_order asc, name asc",
        }));
    },
});
