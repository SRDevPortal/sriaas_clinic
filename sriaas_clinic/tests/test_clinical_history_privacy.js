const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../public/js/clinical_history_modal.js"),
  "utf8"
);
const legacySource = fs.readFileSync(
  path.join(__dirname, "../public/js/_encounter_clinical_history.js"),
  "utf8"
);
const handlers = {};
const sandbox = {
  frappe: {
    utils: {
      escape_html(value) {
        return String(value)
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;");
      },
    },
    ui: {
      form: {
        on(doctype, events) {
          handlers[doctype] = events;
        },
      },
    },
  },
  console,
};

vm.runInNewContext(source, sandbox);

assert.match(legacySource, /patient\.mobile \|\| patient\.mask_mobile/);
assert.doesNotMatch(legacySource, /patient\.(?:mobile_no|sr_mobile_no)/);

const restricted = sandbox._build_header({
  patient_name: "Synthetic",
  mobile_no: "2025550198",
  phone_no: "2025550199",
  mask_mobile: "******0101",
  mask_phone: "******0102",
});
assert.match(restricted, /\*\*\*\*\*\*0101/);
assert.match(restricted, /\*\*\*\*\*\*0102/);
assert.doesNotMatch(restricted, /2025550198|2025550199/);

const full = sandbox._build_header({
  patient_name: "Synthetic",
  mobile: "2025550101",
  phone: "2025550102",
  mask_mobile: "******0101",
  mask_phone: "******0102",
});
assert.match(full, /2025550101/);
assert.match(full, /2025550102/);

console.log("Clinical-history number privacy checks passed.");
