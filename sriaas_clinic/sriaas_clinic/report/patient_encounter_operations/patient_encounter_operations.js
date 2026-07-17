frappe.query_reports["Patient Encounter Operations"] = {
    filters: [
        {
            fieldname: "sr_pe_id",
            label: __("Encounter ID"),
            fieldtype: "Data",
        },
        {
            fieldname: "mobile",
            label: __("Patient Mobile"),
            fieldtype: "Data",
        },
        {
            fieldname: "sr_pe_deptt",
            label: __("Medical Department"),
            fieldtype: "Link",
            options: "Medical Department",
        },
        {
            fieldname: "sr_encounter_status",
            label: __("Encounter Status"),
            fieldtype: "Link",
            options: "SR Encounter Status",
        },
        {
            fieldname: "sr_encounter_type",
            label: __("Encounter Type"),
            fieldtype: "Data",
        },
        {
            fieldname: "sr_encounter_place",
            label: __("Encounter Place"),
            fieldtype: "Data",
        },
        {
            fieldname: "owner",
            label: __("Owner"),
            fieldtype: "Link",
            options: "User",
        },
        {
            fieldname: "creation_from",
            label: __("Created From"),
            fieldtype: "Date",
        },
        {
            fieldname: "creation_to",
            label: __("Created To"),
            fieldtype: "Date",
        },
        {
            fieldname: "page_length",
            label: __("Rows"),
            fieldtype: "Int",
            default: 50,
        },
        {
            fieldname: "start",
            label: __("Start Row"),
            fieldtype: "Int",
            default: 0,
        },
    ],
};
