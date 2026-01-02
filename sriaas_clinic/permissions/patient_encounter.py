# sriaas_clinic/permissions/patient_encounter.py

import frappe

def get_conditions(user):
    # Admin should see everything
    if user == "Administrator":
        return ""

    # Only restrict Order Confirmation role
    if "Order Confirmation" not in frappe.get_roles(user):
        return ""

    return f"""
        -- Must be assigned (active assignment only)
        EXISTS (
            SELECT 1
            FROM `tabToDo`
            WHERE
                `tabToDo`.reference_type = 'Patient Encounter'
                AND `tabToDo`.reference_name = `tabPatient Encounter`.name
                AND `tabToDo`.allocated_to = '{user}'
                AND `tabToDo`.status = 'Open'
        )

        -- Department must match USER PERMISSION (Encounter-level)
        AND `tabPatient Encounter`.sr_pe_deptt IN (
            SELECT for_value
            FROM `tabUser Permission`
            WHERE
                user = '{user}'
                AND allow = 'Medical Department'
        )

        -- Safety net: Patient department must also match
        AND EXISTS (
            SELECT 1
            FROM `tabPatient`
            WHERE
                `tabPatient`.name = `tabPatient Encounter`.patient
                AND `tabPatient`.sr_medical_department IN (
                    SELECT for_value
                    FROM `tabUser Permission`
                    WHERE
                        user = '{user}'
                        AND allow = 'Medical Department'
                )
        )
    """
