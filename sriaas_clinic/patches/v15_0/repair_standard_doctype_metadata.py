import frappe


def execute():
    from sriaas_clinic.api.doctype_metadata_repair import repair_missing_standard_docfields

    result = repair_missing_standard_docfields(commit=False)
    frappe.log_error(
        title="Standard DocType metadata repair",
        message=frappe.as_json(result, indent=2),
    )
