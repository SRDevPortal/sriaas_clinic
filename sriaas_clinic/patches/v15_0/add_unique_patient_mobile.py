import frappe

def execute():
    if frappe.db.db_type != "mariadb":
        return

    indexes = frappe.db.sql("""
        SHOW INDEX FROM `tabPatient`
        WHERE Key_name = 'uniq_patient_mobile'
    """)

    if not indexes:
        frappe.db.sql("""
            ALTER TABLE `tabPatient`
            ADD UNIQUE INDEX `uniq_patient_mobile` (`mobile`)
        """)
