(function patchPatientEncounterList() {
    const copiedFilterFieldBlacklist = new Set([
        "sr_pe_id",
        "sr_pe_mobile",
        "sr_pe_deptt",
        "sr_pe_disease",
        "sr_pe_language",
        "sr_pe_age",
    ]);

    const existingSettings = frappe.listview_settings["Patient Encounter"] || {};
    const existingOnload = existingSettings.onload;

    frappe.listview_settings["Patient Encounter"] = {
        ...existingSettings,
        onload(listview) {
            if (typeof existingOnload === "function") {
                existingOnload(listview);
            }

            if (listview.__sr_new_doc_patch_installed) {
                return;
            }

            listview.__sr_new_doc_patch_installed = true;

            listview.page.add_inner_button(
                __("Optimized Operations"),
                () => frappe.set_route("query-report", "Patient Encounter Operations"),
                __("View")
            );

            listview.page.add_inner_button(
                __("Search by Mobile"),
                () => {
                    frappe.prompt(
                        {
                            fieldname: "mobile",
                            fieldtype: "Data",
                            label: __("Patient Mobile"),
                            reqd: 1,
                        },
                        ({ mobile }) => {
                            const digits = String(mobile || "").replace(/\D/g, "");
                            if (digits.length < 10) {
                                frappe.msgprint(__("Enter a phone number containing at least 10 digits."));
                                return;
                            }
                            frappe.route_options = { mobile: digits.slice(-10) };
                            frappe.set_route("query-report", "Patient Encounter Operations");
                        },
                        __("Search Patient Encounters"),
                        __("Search")
                    );
                },
                __("View")
            );

            listview.make_new_doc = function () {
                const options = {};
                const allowedFilterTypes = [
                    "=",
                    "descendants of (inclusive)",
                    "descendants of",
                    "ancestors of",
                ];

                this.filter_area.get().forEach((filter) => {
                    const fieldname = filter[1];
                    const operator = filter[2];

                    if (
                        allowedFilterTypes.includes(operator) &&
                        frappe.model.is_non_std_field(fieldname) &&
                        !copiedFilterFieldBlacklist.has(fieldname)
                    ) {
                        options[fieldname] = filter[3];
                    }
                });

                frappe.new_doc(this.doctype, options);
            };
        },
    };
})();
