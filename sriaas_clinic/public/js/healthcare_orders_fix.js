// Correct the upstream medication status lookup without replacing the order template.
(() => {
    if (frappe.render_template.__clinic_orders_fix) return;
    const render_template = frappe.render_template;
    frappe.render_template = function (name, ...args) {
        if (name === "healthcare_orders") {
            const template = frappe.templates[name];
            const marker = '<div class="medication-requests pr-1">';
            const start = typeof template === "string" ? template.indexOf(marker) : -1;
            if (start !== -1) {
                const corrected = template.slice(0, start) + template.slice(start).replace(
                    /status_code_map\[service_requests\[i\]\.status\]/g,
                    "status_code_map[medication_requests[i].status]"
                );
                if (corrected !== template) {
                    frappe.templates[name] = corrected;
                    delete frappe.template.compiled[name];
                    delete frappe.template.debug[name];
                }
            }
        }
        return render_template.call(this, name, ...args);
    };
    frappe.render_template.__clinic_orders_fix = true;
})();
