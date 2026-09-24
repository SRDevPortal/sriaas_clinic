app_name = "sriaas_clinic"
app_title = "Sriaas Clinic"
app_publisher = "SRIAAS"
app_description = "Clinic customizations packaged as clean installable/uninstallable app."
app_email = "webdevelopersriaas@gmail.com"
app_license = "mit"
required_apps = ["sriaas_role_permissions"]

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
    "/assets/privacy_shield/js/desk_privacy.js",
]

web_include_css = "/assets/sriaas_clinic/css/theme_overrides.css"

list_js = {
    "Sales Invoice": "public/js/sales_invoice_list.js",
}

doctype_list_js = {
    "Patient Encounter": "public/js/patient_encounter_list.js",
}

permission_query_conditions = {
    "CRM Lead": "sriaas_clinic.api.crm_lead.access.crm_lead_pqc",
}

has_permission = {
    "CRM Lead": "sriaas_clinic.api.crm_lead.access.crm_lead_has_permission",
}

doc_events = {
    "Patient": {
        "autoname": [
            "sriaas_clinic.api.patient.set_patient_series",
        ],
        "before_insert": [
            "sriaas_clinic.api.patient.set_patient_creator",
            # Normalize early
            "sriaas_clinic.api.patient.normalize_patient_contact_numbers",
            "sriaas_clinic.api.patient.validate_unique_contact_mobile",
            "sriaas_clinic.api.patient.set_patient_id",            
            "sriaas_clinic.api.patient.set_followup_id",
            "sriaas_clinic.api.patient.set_followup_day",
        ],
        "validate": [
            "sriaas_clinic.api.patient.validate_followup_status",
        ],
        "after_save": [
            "sriaas_clinic.api.address.mirror_links_to_customer",
        ],
    },
    "Customer": {
        "autoname": [
            "sriaas_clinic.api.customer.set_customer_series",
        ],
        "before_insert": [
            "sriaas_clinic.api.customer.set_customer_id",
            "sriaas_clinic.api.customer.set_customer_creator",
        ],        
        "before_save": [
            "sriaas_clinic.api.customer.sanitize_customer_contact_numbers",
        ],
    },
    "Contact": {
        "before_save": [
            "sriaas_clinic.api.contact.normalize_phoneish_fields",
        ],
    },
    "Address": {
        "before_validate": [
            "sriaas_clinic.api.address.validate_state",
        ],
        "before_save": [
            "sriaas_clinic.api.address.ensure_address_has_customer_link",
        ],
    },
    "CRM Lead": {
        "validate": [
            "sriaas_clinic.api.crm_lead.guards.guard_restricted_fields",
        ],
        "before_save": [
            "sriaas_clinic.api.crm_lead.controller.normalize_phoneish_fields",
        ],
    },
    "Healthcare Practitioner": {
        "before_validate": [
            "sriaas_clinic.api.practitioner.compose_full_name",
        ],
    },
    "Patient Appointment": {
        "before_insert": [
            "sriaas_clinic.api.patient_appointment.set_created_by_agent",
        ],
        # "on_update": [
        #     "sriaas_clinic.api.patient_appointment.create_payment_entries_from_child_table",
        #     "sriaas_clinic.api.patient_appointment.on_update_create_payments",
        # ],
    },
    "Patient Encounter": {
        "before_validate": [
            "sriaas_clinic.api.patient_encounter_phone.sync_normalized_mobile",
        ],
        "validate": [
            "sriaas_clinic.api.encounter_flow.handlers.validate_agent_status_change",
            "sriaas_clinic.api.encounter_flow.handlers.validate_agent_followup_online_source",
            "sriaas_clinic.api.encounter_flow.handlers.validate_sales_type_required",
            "sriaas_clinic.api.encounter_flow.handlers.validate_order_items_required",
            # "sriaas_clinic.api.encounter_flow.handlers.validate_encounter_workflow",
        ],
        "before_insert": [
            "sriaas_clinic.api.encounter_flow.handlers.set_created_by_agent",
            "sriaas_clinic.api.encounter_flow.handlers.set_default_encounter_status",
        ],
        "after_insert": [
            "sriaas_clinic.api.crm_lead.attachments.copy_crm_lead_attachments_to_encounter",
        ],
        "before_save": [
            "sriaas_clinic.api.encounter_flow.handlers.enforce_agent_encounter_place",
            "sriaas_clinic.api.encounter_flow.handlers.link_crm_lead_source_patient_from_encounter",
            "sriaas_clinic.api.encounter_flow.handlers.before_save_patient_encounter",
            "sriaas_clinic.api.encounter_flow.handlers.clear_advance_dependent_fields",
            "sriaas_clinic.api.s3.file_hooks.cleanup_payment_proof_removals",
        ],
        "before_submit": [
            "sriaas_clinic.api.encounter_flow.handlers.validate_required_before_submit",
        ],
        "on_submit": [
            "sriaas_clinic.api.encounter_flow.handlers.create_billing_on_submit",
        ],
    },
    "Item": {
        "validate": "sriaas_clinic.api.item_package_weight.calculate_pkg_weights",
    },
    "Sales Invoice": {
        "onload": [
            "sriaas_clinic.api.gst_breakup.update_gst_breakup_table",
        ],
        "before_print": [
            "sriaas_clinic.api.gst_breakup.update_gst_breakup_table",
        ],
        "before_insert": [
            "sriaas_clinic.api.si_payment_flow.handlers.set_created_by_agent",
        ],
        "before_validate": [
            "sriaas_clinic.api.sales_invoice.set_sales_invoice_series",
            "sriaas_clinic.api.si_payment_flow.handlers.apply_kit_discount_from_grand_total",
            "sriaas_clinic.api.gst_breakup.prepare_gst_validation_fields",
            "sriaas_clinic.api.compliance_barcode.prepare_sales_invoice_compliance",
        ],
        "validate": [
            "sriaas_clinic.api.sales_invoice.validate_sales_invoice_series",
            "sriaas_clinic.api.sales_invoice_guard.validate_sales_invoice_warehouse",
        ],
        "before_save": [
            "sriaas_clinic.api.sales_invoice_cost.before_save",
            "sriaas_clinic.api.gst_breakup.refresh_gst_breakup_on_save",
        ],
        "before_submit": [
            "sriaas_clinic.api.sales_invoice_guard.validate_sales_invoice_warehouse",
            "sriaas_clinic.api.sales_invoice_guard.validate_kit_total_vs_grand_total",
            "sriaas_clinic.api.compliance_barcode.validate_sales_invoice_compliance",
            # "sriaas_clinic.api.si_payment_flow.handlers.validate_dp_before_submit",
        ],        
        "on_submit": [
            "sriaas_clinic.api.sales_invoice_ledger.repair_sales_invoice_ledger_links",
            "sriaas_clinic.api.encounter_flow.handlers.link_pending_payment_entries",
            # "sriaas_clinic.api.si_payment_flow.handlers.create_pe_from_si_dp",
            # "sriaas_clinic.api.integrations.n8n_shiprocket.send_to_n8n_on_submit",
        ],
        "before_cancel": [
            "sriaas_clinic.api.sales_invoice_guard.validate_sales_invoice_warehouse",
        ],
        "before_amend": [
            "sriaas_clinic.api.sales_invoice_guard.validate_sales_invoice_warehouse",
        ],
    },
    "Payment Entry": {
        "before_validate": [
            "sriaas_clinic.api.payment_entry.hydrate_missing_party_and_reference_fields",
        ],
        "before_insert": [
            "sriaas_clinic.api.payment_entry.set_created_by_agent",
        ],        
        "on_submit": [
            "sriaas_clinic.api.payment_entry.repair_payment_entry_ledger_links",
        ],
        # "before_save": [
        #     "sriaas_clinic.api.payment_entry.sync_parent_mode_from_children_server",
        # ],
        # "validate": [
        #     "sriaas_clinic.api.payment_entry.validate_payment_modes_total",
        # ],
        # "on_submit": [
        #     "sriaas_clinic.api.payment_entry.create_journal_for_payment_modes",
        # ],
        # "on_cancel": [
        #     "sriaas_clinic.api.payment_entry.cancel_linked_journal_entries",
        # ],
    },
    # "Medical Department": {
    #     "after_insert": [
    #         "sriaas_clinic.api.medical_department.after_insert",
    #     ],
    #     "on_rename": [
    #         "sriaas_clinic.api.medical_department.on_rename",
    #     ],
    # },
    "Team": {
        "on_update": [
            "sriaas_clinic.api.team_sync.sync_user_team_leaders",
        ],
        "on_trash": [
            "sriaas_clinic.api.team_sync.sync_user_team_leaders",
        ],
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
    "File": {
        "after_insert": [
            "sriaas_clinic.api.s3.file_hooks.handle_file_after_insert",
        ],
        "on_trash": [
            "sriaas_clinic.api.s3.file_hooks.handle_file_on_trash",
        ],
    }
}

doctype_js = {
    "Patient": [
        "public/js/patient_followup_marker.js",
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
        "public/js/s3_attachment_links.js",
        "public/js/crm_lead_disposition_filter.js",
        "public/js/crm_lead_lock_fields.js",
        "public/js/crm_lead_number_privacy.js",
        "public/js/crm_lead_pex_launcher.js",
    ],
    "Item": [
        "public/js/item_package_weight.js",
    ],
    "Sales Invoice": [
        "public/js/sales_invoice_series.js",
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

fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "Sriaas Clinic"]]},
    {"dt": "Property Setter", "filters": [["module", "=", "Sriaas Clinic"]]},
    {"dt": "Client Script", "filters": [["module", "=", "Sriaas Clinic"]]},
    {"dt": "Server Script", "filters": [["module", "=", "Sriaas Clinic"]]},
    {"dt": "Workspace", "filters": [["module", "=", "Sriaas Clinic"]]},
    {"dt": "Print Format", "filters": [["module", "=", "Sriaas Clinic"]]},
    {"dt": "Report", "filters": [["module", "=", "Sriaas Clinic"]]},
    {"dt": "Dashboard Chart", "filters": [["module", "=", "Sriaas Clinic"]]},
    {"dt": "Notification", "filters": [["module", "=", "Sriaas Clinic"]]},
    {"dt": "Web Template", "filters": [["module", "=", "Sriaas Clinic"]]},
    {"dt": "Form Tour", "filters": [["module", "=", "Sriaas Clinic"]]},
    {"dt": "Form Tour Step", "filters": [["module", "=", "Sriaas Clinic"]]},
    {"dt": "Custom DocPerm", "filters": [["module", "=", "Sriaas Clinic"]]},
]

# CRM and Desk privacy integration is owned by Sriaas Clinic.
# The adapters delegate unchanged until the development pilot gate is enabled.
override_whitelisted_methods = {
    "frappe.core.doctype.data_export.exporter.export_data": "sriaas_clinic.api.crm_lead.privacy_outputs.export_data",
    "frappe.desk.reportview.export_query": "sriaas_clinic.api.crm_lead.privacy_outputs.export_query",
    "frappe.utils.print_format.download_pdf": "sriaas_clinic.api.crm_lead.privacy_outputs.download_pdf",
    "frappe.www.printview.get_html_and_style": "sriaas_clinic.api.crm_lead.privacy_outputs.get_html_and_style",
    "frappe.client.insert": "sriaas_clinic.api.crm_lead.privacy.lifecycle_insert",
    "frappe.client.insert_many": "sriaas_clinic.api.crm_lead.privacy.lifecycle_insert_many",
    "frappe.client.submit": "sriaas_clinic.api.crm_lead.privacy.lifecycle_submit",
    "frappe.client.cancel": "sriaas_clinic.api.crm_lead.privacy.lifecycle_cancel",
    "frappe.client.bulk_update": "sriaas_clinic.api.crm_lead.privacy.lifecycle_bulk_update",
    "frappe.desk.form.save.cancel": "sriaas_clinic.api.crm_lead.privacy.lifecycle_desk_cancel",

    "crm.api.doc.get_data": "sriaas_clinic.api.crm_lead.privacy_views.get_data",
    "frappe.desk.reportview.get": "sriaas_clinic.api.crm_lead.privacy.reportview_get",
    "frappe.desk.reportview.get_list": "sriaas_clinic.api.crm_lead.privacy.reportview_get_list",
    "frappe.desk.search.search_link": "sriaas_clinic.api.crm_lead.privacy.search_link",
    "frappe.desk.search.search_widget": "sriaas_clinic.api.crm_lead.privacy.search_widget",
    "frappe.client.get_list": "sriaas_clinic.api.crm_lead.privacy.client_get_list",
    "frappe.client.get_value": "sriaas_clinic.api.crm_lead.privacy.client_get_value",
    "frappe.desk.form.load.getdoc": "sriaas_clinic.api.crm_lead.privacy.desk_getdoc",
    "frappe.desk.form.save.savedocs": "sriaas_clinic.api.crm_lead.privacy.desk_savedocs",
    "frappe.client.get": "sriaas_clinic.api.crm_lead.privacy.client_get",
    "frappe.client.save": "sriaas_clinic.api.crm_lead.privacy.client_save",
    "frappe.client.set_value": "sriaas_clinic.api.crm_lead.privacy.client_set_value",
}


# Project Lead detail metadata to the same masked keys as its document response.
override_whitelisted_methods.update({
    "crm.fcrm.doctype.crm_fields_layout.crm_fields_layout.get_sidepanel_sections":
        "sriaas_clinic.api.crm_lead.privacy_views.get_sidepanel_sections",
})

# CRM remains upstream-owned; privacy integration lives in the clinic app.
override_doctype_class = {
    "CRM Notification": "sriaas_clinic.api.crm_lead.privacy_notifications.PrivacyCRMNotification",
}

# Duplicate popup protection stays clinic-owned; dedupe matching is unchanged.
override_whitelisted_methods.update({
    "crm_lead_dedupe.api.crm_lead_duplicates.get_duplicates_for_crm_lead":
        "sriaas_clinic.api.crm_lead.privacy_duplicates.get_duplicates_for_crm_lead",
})

# Explicit generator selection plus pilot-only configuration; defaults are unchanged.
pdf_generator = ["sriaas_clinic.pilot_pdf.generate"]
