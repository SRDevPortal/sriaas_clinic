app_name = "sriaas_clinic"
app_title = "Sriaas Clinic"
app_publisher = "SRIAAS"
app_description = "Clinic customizations packaged as clean installable/uninstallable app."
app_email = "webdevelopersriaas@gmail.com"
app_license = "mit"

# Installation
# before_install = "sriaas_clinic.install.before_install"
after_install = "sriaas_clinic.install.after_install"
after_migrate = "sriaas_clinic.install.after_migrate"

# Uninstallation
# before_uninstall = "sriaas_clinic.uninstall.before_uninstall"
# after_uninstall = "sriaas_clinic.uninstall.after_uninstall"

app_include_css = [
    "/assets/sriaas_clinic/css/theme_overrides.css",
]

app_include_js = [
    "/assets/sriaas_clinic/js/patient_quick_entry_patch.js",
]

web_include_css = "/assets/sriaas_clinic/css/theme_overrides.css"

doctype_js = {
    "Patient": [
        "public/js/patient_invoices.js",
        "public/js/patient_payments.js",
        "public/js/patient_pex_launcher.js",
        "public/js/patient_regional.js",
        "public/js/clinical_history_modal.js",
    ],
    "Patient Encounter": [
        "public/js/patient_encounter.js",
        "public/js/encounter_draft_invoice.js",
        "public/js/encounter_order_item.js",
        "public/js/encounter_practitioner_filters.js",
        "public/js/encounter_medication_template.js",
        "public/js/encounter_medication_manual.js",
        "public/js/encounter_medication_filters.js",
        "public/js/encounter_block_autosave_for_proof.js",
        "public/js/encounter_attachments.js",
        "public/js/clinical_history_modal.js",
    ],
    "Healthcare Practitioner": [
        "public/js/healthcare_practitioner.js",
    ],
    "CRM Lead": [
        "public/js/crm_lead_disposition_filter.js",
        "public/js/crm_lead_lock_fields.js",
        "public/js/crm_lead_pex_launcher.js",
    ],
    "Item": [
        "public/js/item_package_weight.js",
    ],
    "Sales Invoice": [
        "public/js/sales_invoice_actions.js",
        "public/js/sales_invoice_barcode.js",
        # "public/js/shipkia_sales_invoice.js",
    ],
    "Payment Entry": [
        "public/js/payment_entry_outstanding_dialog.js",
        "public/js/payment_entry_actions.js",
        # "public/js/_payment_entry_extend.js",
    ],
    "Stock Entry": [
        "public/js/stock_entry_barcode.js",
    ],
}

list_js = {
    "Sales Invoice": "public/js/sales_invoice_list.js",
}

doctype_list_js = {
    "CRM Lead": "public/js/crm_lead_list.js",
}

# Permissions
# -----------
permission_query_conditions = {
    "CRM Lead": "sriaas_clinic.api.crm_lead.access.crm_lead_pqc",
}
has_permission = {
    "CRM Lead": "sriaas_clinic.api.crm_lead.access.crm_lead_has_permission",
}

# Document Events
# ---------------
# Hook on document methods and events
doc_events = {
    "Patient": {
        "before_insert": [
            "sriaas_clinic.api.patient.set_sr_patient_id",
            "sriaas_clinic.api.patient.set_created_by_agent",
            "sriaas_clinic.api.patient.validate_unique_contact_mobile",
        ],
        "autoname": "sriaas_clinic.api.patient.force_patient_series",
        "before_save": "sriaas_clinic.api.patient.normalize_phoneish_fields",
        "after_insert": [
            "sriaas_clinic.api.patient.assign_followup_day",
            "sriaas_clinic.api.patient.set_followup_last_digit",
        ],
        "after_save": "sriaas_clinic.api.address.mirror_links_to_customer",
    },
    "Customer": {
        "before_insert": "sriaas_clinic.api.customer.set_sr_customer_id",
        "autoname": "sriaas_clinic.api.customer.force_customer_series",
        "before_save":   "sriaas_clinic.api.customer.normalize_phoneish_fields",
    },
    "Address": {
        "before_validate": "sriaas_clinic.api.address.validate_state",
        "before_save": "sriaas_clinic.api.address.ensure_address_has_customer_link",
    },
    "Contact": {
        "before_save": "sriaas_clinic.api.contact.normalize_phoneish_fields",
    },
    "Patient Encounter": {
        "validate": [
            "sriaas_clinic.api.encounter_flow.handlers.validate_encounter_workflow",
        ],
        "before_insert": [
            "sriaas_clinic.api.encounter_flow.handlers.set_created_by_agent",
            "sriaas_clinic.api.encounter_flow.handlers.enforce_agent_encounter_place",
            "sriaas_clinic.api.encounter_flow.handlers.set_default_encounter_status",
        ],
        "before_save": [
            "sriaas_clinic.api.encounter_flow.handlers.enforce_agent_encounter_place",
            "sriaas_clinic.api.encounter_flow.handlers.before_save_patient_encounter",
            "sriaas_clinic.api.encounter_flow.handlers.clear_advance_dependent_fields",
        ],
        "before_submit": [
            "sriaas_clinic.api.encounter_flow.handlers.validate_required_before_submit",
        ],
        "on_submit": [
            "sriaas_clinic.api.encounter_flow.handlers.create_billing_on_submit",
        ],
    },
    "Patient Appointment": {
        "before_insert": "sriaas_clinic.api.patient_appointment.set_created_by_agent",
        # "on_update": "sriaas_clinic.api.patient_appointment.create_payment_entries_from_child_table",
        # "on_update": "sriaas_clinic.api.patient_appointment.on_update_create_payments",
    },
    "Healthcare Practitioner": {
        "before_validate": "sriaas_clinic.api.practitioner.compose_full_name",
    },
    "Sales Invoice": {
        "before_insert": "sriaas_clinic.api.si_payment_flow.handlers.set_created_by_agent", #done
        "validate": "sriaas_clinic.api.sales_invoice_guard.validate_sales_invoice_warehouse", #done
        "before_save": "sriaas_clinic.api.sales_invoice_cost.before_save",
        "before_submit": [
            "sriaas_clinic.api.sales_invoice_guard.validate_sales_invoice_warehouse", #done
            # "sriaas_clinic.api.si_payment_flow.handlers.validate_dp_before_submit",
        ],        
        "on_submit": [
            "sriaas_clinic.api.encounter_flow.handlers.link_pending_payment_entries",
            # "sriaas_clinic.api.si_payment_flow.handlers.create_pe_from_si_dp",
            # "sriaas_clinic.api.integrations.n8n_shiprocket.send_to_n8n_on_submit",
            # "sriaas_clinic.api.integrations.shipkia_sales_invoice.send_sales_invoice_to_shipkia",
        ],        
        "before_cancel": "sriaas_clinic.api.sales_invoice_guard.validate_sales_invoice_warehouse", #done
        "before_amend": "sriaas_clinic.api.sales_invoice_guard.validate_sales_invoice_warehouse", #done
    },
    "Item": {
        "validate": "sriaas_clinic.api.item_package_weight.calculate_pkg_weights",
    },
    "Payment Entry": {
        "before_insert": "sriaas_clinic.api.payment_entry.set_created_by_agent",
        # "before_save": "sriaas_clinic.api.payment_entry.sync_parent_mode_from_children_server",
        # "validate": "sriaas_clinic.api.payment_entry.validate_payment_modes_total",
        # "on_submit": "sriaas_clinic.api.payment_entry.create_journal_for_payment_modes",
        # "on_cancel": "sriaas_clinic.api.payment_entry.cancel_linked_journal_entries",
    },
    # "Medical Department": {
    #     "after_insert": "sriaas_clinic.api.medical_department.after_insert",
    #     # "on_rename": "sriaas_clinic.api.medical_department.on_rename",
    # },
    "CRM Lead": {
        "validate":     "sriaas_clinic.api.crm_lead.guards.guard_restricted_fields",
        "before_save":  "sriaas_clinic.api.crm_lead.controller.normalize_phoneish_fields",
        "after_save":   "sriaas_clinic.api.crm_lead.access.restore_lead_owner_after_unassign",
        "after_insert": "sriaas_clinic.api.crm_lead.lifecycle.after_insert",
        "on_update":    "sriaas_clinic.api.crm_lead.lifecycle.on_update",
    },
    "ToDo": {
        "on_trash": "sriaas_clinic.api.assign_guard.todo_on_trash",
    },
    # "User": {
    #     "after_insert": "sriaas_clinic.api.user_department_membership.after_insert",
    #     "on_update":    "sriaas_clinic.api.user_department_membership.on_update",
    #     "after_save":   "sriaas_clinic.api.user_department_membership.after_save",
    # },
    # "User Group": {
    #     "before_save": "sriaas_clinic.api.user_group_backlink.user_group_before_save",
    # },
    # "Purchase Order": {
    #     "before_submit": "sriaas_clinic.api.purchase_order.create_batches_before_submit"
    # },
    # "File": {
    #     "after_insert": "sriaas_clinic.api.s3.file_hooks.handle_file_after_insert",
    #     "on_trash": "sriaas_clinic.api.s3.file_hooks.handle_file_on_trash",
    # }
}

# Overriding Methods
# ------------------------------
# Keep your assignment authorization guards
override_whitelisted_methods = {
    "frappe.desk.form.assign_to.add": "sriaas_clinic.api.assign_guard.add",
    "frappe.desk.form.assign_to.remove": "sriaas_clinic.api.assign_guard.remove",
    "frappe.desk.form.assign_to.clear": "sriaas_clinic.api.assign_guard.clear",
}

# Export only items that belong to our module
fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "SRIAAS Clinic"]]},
    {"dt": "Property Setter", "filters": [["module", "=", "SRIAAS Clinic"]]},
    {"dt": "Client Script", "filters": [["module", "=", "SRIAAS Clinic"]]},
    {"dt": "Server Script", "filters": [["module", "=", "SRIAAS Clinic"]]},
    {"dt": "Workspace", "filters": [["module", "=", "SRIAAS Clinic"]]},
    {"dt": "Print Format", "filters": [["module", "=", "SRIAAS Clinic"]]},
    {"dt": "Report", "filters": [["module", "=", "SRIAAS Clinic"]]},
    {"dt": "Dashboard Chart", "filters": [["module", "=", "SRIAAS Clinic"]]},
    {"dt": "Notification", "filters": [["module", "=", "SRIAAS Clinic"]]},
    {"dt": "Web Template", "filters": [["module", "=", "SRIAAS Clinic"]]},
    {"dt": "Form Tour", "filters": [["module", "=", "SRIAAS Clinic"]]},
    {"dt": "Form Tour Step", "filters": [["module", "=", "SRIAAS Clinic"]]},
    {"dt": "Custom DocPerm", "filters": [["module", "=", "SRIAAS Clinic"]]},
]
