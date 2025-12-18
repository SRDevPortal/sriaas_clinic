frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {

        if (frm.doc.docstatus === 1) {

            // Show only if not sent OR allow resend
            if (!frm.doc.sent_to_shipkia) {

                frm.add_custom_button(
                    __("Send to Shipkia"),
                    () => {
                        frappe.confirm(
                            "Send this Sales Invoice to Shipkia?",
                            () => {
                                frappe.call({
                                    method: "sriaas_clinic.api.integrations.shipkia_sales_invoice.send_sales_invoice_to_shipkia",
                                    args: {
                                        invoice_name: frm.doc.name
                                    },
                                    freeze: true,
                                    freeze_message: __("Sending to Shipkia..."),
                                    callback(r) {
                                        if (!r.exc) {
                                            frappe.msgprint(r.message);
                                            frm.reload_doc();
                                        }
                                    }
                                });
                            }
                        );
                    },
                    __("Actions")
                );

            } else {

                // Optional RESEND
                frm.add_custom_button(
                    __("Resend to Shipkia"),
                    () => {
                        frappe.confirm(
                            "This invoice was already sent. Resend?",
                            () => {
                                frappe.call({
                                    method: "sriaas_clinic.api.integrations.shipkia_sales_invoice.send_sales_invoice_to_shipkia",
                                    args: {
                                        invoice_name: frm.doc.name
                                    },
                                    freeze: true,
                                    callback(r) {
                                        if (!r.exc) {
                                            frappe.msgprint("Resent successfully");
                                        }
                                    }
                                });
                            }
                        );
                    },
                    __("Actions")
                );

            }
        }
    }
});
