# sriaas_clinic/patches/migrate_populate_created_by_agent.py
import frappe

def migrate_patient_created_by_agent():
    """
    Populate created_by_agent on existing Patient records.

    Strategy (per-patient):
      1. Use latest Patient Encounter.created_by_agent (if present)
      2. Else use Patient.owner
      3. Else skip
    """
    frappe.reload_doc("sriaas_clinic", "doctype", "patient", force=True)  # safe no-op if already loaded

    patients = frappe.get_all("Patient", fields=["name", "owner"], limit=None)
    updated = 0
    skipped = 0
    errors = 0

    for p in patients:
        patient_name = p.get("name")
        try:
            # 1) try latest encounter created_by_agent (most-recent modified)
            enc = frappe.get_all(
                "Patient Encounter",
                filters={"patient": patient_name},
                fields=["created_by_agent"],
                order_by="modified desc",
                limit=1,
            )
            val = None
            if enc and enc[0].get("created_by_agent"):
                val = enc[0]["created_by_agent"]
            elif p.get("owner"):
                # 2) fallback to owner
                val = p.get("owner")

            if val:
                cur = frappe.db.get_value("Patient", patient_name, "created_by_agent")
                if not cur or str(cur) != str(val):
                    # Avoid touching modified/modified_by timestamps
                    frappe.db.set_value("Patient", patient_name, "created_by_agent", val, update_modified=False)
                    updated += 1
                else:
                    skipped += 1
            else:
                skipped += 1
        except Exception:
            errors += 1
            frappe.log_error(frappe.get_traceback(), f"migrate_populate_created_by_agent: {patient_name}")

    frappe.msgprint(f"populate_created_by_agent: Updated={updated}, Skipped={skipped}, Errors={errors}")
    return {"updated": updated, "skipped": skipped, "errors": errors}
