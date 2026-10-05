const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const bench = path.resolve(__dirname, "../../../..");
const upstream = fs.readFileSync(path.join(bench, "apps/healthcare/healthcare/public/js/healthcare_orders.html"), "utf8");
const context = vm.createContext({
    __: value => value,
    frappe: {
        templates: { healthcare_orders: upstream, other: "Unrelated" },
        avatar: () => "",
        datetime: { global_date_format: value => value },
        throw: message => { throw new Error(message); },
    },
});
vm.runInContext(fs.readFileSync(path.join(bench, "apps/frappe/frappe/public/js/frappe/microtemplate.js"), "utf8"), context);
const row = (name, status) => ({ name, status, docstatus: 1, billing_status: "Pending", order_group: "", practitioner_email: "", order_date: "2026-10-05", order_time: "", practitioner_name: "", template_dt: "", template_dn: "", medication: "", period: "", dosage_form: "", dosage: "", quantity: 0 });
const data = (medications, services) => ({ medication_requests: medications, service_requests: services, create_orders: true, status_code_map: { Active: "ACTIVE_LABEL", "On Hold": "HOLD_LABEL" } });
const render = value => context.frappe.render_template("healthcare_orders", value);
const meds = [row("MED-1", "On Hold"), row("MED-2", "Active")];
const services = [row("SR-1", "Active")];
assert.throws(() => render(data(meds, [])), /status/); // Reproduce the reported failure.
const patch = fs.readFileSync(path.join(__dirname, "../public/js/healthcare_orders_fix.js"), "utf8");
vm.runInContext(patch, context);
let output = render(data(meds, []));
assert.match(output, /MED-1/);
assert.match(output, /MED-2/);
assert.match(output, /HOLD_LABEL/);
output = render(data([], services));
assert.match(output, /ACTIVE_LABEL/);
assert.match(output, /No Medication Requests/);
output = render(data(meds, services));
assert.match(output, /HOLD_LABEL/); // Medication status must not borrow service status.
assert.match(output, /MED-2/); // Unequal list lengths must render.
assert.match(output, /SR-1/);
assert.match(output, /new-service-request-btn/);
assert.match(output, /new-medication-btn/);
assert.match(output, /order-cancel/);
assert.match(render(data([], [])), /No Medication Requests/);
assert.equal(context.frappe.render_template("other"), "Unrelated");
const installed = context.frappe.render_template;
vm.runInContext(patch, context);
assert.equal(context.frappe.render_template, installed);
const corrected = context.frappe.templates.healthcare_orders;
render(data(meds, services));
assert.equal(context.frappe.templates.healthcare_orders, corrected);
// Also correct an upstream template registered again after the asset loads.
context.frappe.templates.healthcare_orders = upstream;
assert.match(render(data(meds, [])), /HOLD_LABEL/);
console.log("PASS: medication-only, service-only, mixed/unequal, empty, actions, cache and unrelated templates");
