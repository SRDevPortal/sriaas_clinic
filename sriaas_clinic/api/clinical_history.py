"""Read-only Patient history for the clinic dialog, using native record access."""
from copy import deepcopy

import frappe

def enabled(doctype):
    try:
        from privacy_shield.desk import enabled as privacy_enabled
    except ImportError:
        return False
    return privacy_enabled(doctype)


def current_capabilities():
    from privacy_shield.policy import current_capabilities as capabilities
    return capabilities()


CLINICAL_TEXT_FIELDS = ("sr_complaints", "sr_observations", "sr_investigations",
                        "sr_diagnosis", "sr_notes", "patient_name", "practitioner_name")
MEDICATION_TABLES = ("drug_prescription", "sr_homeopathy_drug_prescription",
                     "sr_allopathy_drug_prescription")


def project_history_document(data, capabilities):
    # Send only the fields displayed by this dialog, not hidden Encounter
    # comments, provider payloads or unrelated contact copies.
    fields = {"doctype", "name", "patient", "encounter_date", "sr_pe_mobile", *CLINICAL_TEXT_FIELDS, *MEDICATION_TABLES}
    data = {key: deepcopy(value) for key, value in data.items() if key in fields}
    for table in MEDICATION_TABLES:
        if table in data:
            data[table] = [{key: value for key, value in row.items()
                            if key in {"medication", "drug", "dosage", "period", "dosage_form", "sr_drug_instruction"}}
                           for row in data[table] or []]
    if not enabled("Patient Encounter"):
        return data
    from privacy_shield.desk import project_document
    result = project_document(data, capabilities)
    if capabilities.view_full:
        return result
    from privacy_shield.display_text import mask_display
    result = deepcopy(result)
    for field in CLINICAL_TEXT_FIELDS:
        if field in result:
            result[field] = mask_display(result[field])
    for table in MEDICATION_TABLES:
        for row in result.get(table) or []:
            for field in ("medication", "medication_name", "drug", "sr_drug_instruction", "instruction"):
                if field in row:
                    row[field] = mask_display(row[field])
    return result


@frappe.whitelist()
def get_encounters(patient):
    parent = frappe.get_doc("Patient", patient)
    parent.check_permission("read")
    # Native listing applies role/user permissions; the per-record check and
    # field-level projection are retained before returning any document data.
    rows = frappe.get_list("Patient Encounter", filters={"patient": patient},
                           fields=["name", "encounter_date"],
                           order_by="encounter_date desc, creation desc", limit_page_length=100)
    capabilities = current_capabilities() if enabled("Patient Encounter") else None
    result = []
    for row in rows:
        doc = frappe.get_doc("Patient Encounter", row.name)
        doc.check_permission("read")
        doc.apply_fieldlevel_read_permissions()
        result.append(project_history_document(doc.as_dict(), capabilities))
    return result
