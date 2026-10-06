import frappe

def execute():
    patients = frappe.get_all(
        "Patient",
        fields=[
            "name",
            "sr_practo_id",
            "sr_patient_id",
            "sr_followup_id",
        ],
    )

    for p in patients:
        if p.sr_followup_id:
            continue

        source = p.sr_practo_id or p.sr_patient_id or p.name
        if source:
            source = str(source).strip()

        digits = [ch for ch in source if ch.isdigit()] if source else []
        if not digits:
            continue

        try:
            last_digit = int(digits[-1])
        except (TypeError, ValueError):
            continue

        record = frappe.get_cached_value(
            "SR Followup ID",
            {"digit": last_digit, "is_active": 1},
            "name",
        )

        if record:
            frappe.db.set_value(
                "Patient",
                p.name,
                "sr_followup_id",
                record,
                update_modified=False
            )

    frappe.db.commit()
