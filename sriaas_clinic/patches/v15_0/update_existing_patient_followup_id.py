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
        source = p.sr_practo_id or p.sr_patient_id
        last_digit = None

        if source:
            source = source.strip()
            for ch in source:
                if ch.isdigit():
                    last_digit = ch

        # Update ONLY sr_followup_id
        if p.sr_followup_id != last_digit:
            frappe.db.set_value(
                "Patient",
                p.name,
                "sr_followup_id",
                last_digit,
                update_modified=False
            )

    frappe.db.commit()
