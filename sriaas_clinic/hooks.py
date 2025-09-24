app_name = "sriaas_clinic"
app_title = "Sriaas Clinic"
app_publisher = "SRIAAS"
app_description = "Clinic customizations packaged as clean installable/uninstallable app."
app_email = "webdevelopersriaas@gmail.com"
app_license = "mit"

# Life-cycle hooks
after_install = "sriaas_clinic.install.after_install"
after_migrate = "sriaas_clinic.install.after_migrate"

# If you add an uninstall cleaner later:
# before_uninstall = "sriaas_clinic.uninstall.before_uninstall"
# after_uninstall = "sriaas_clinic.uninstall.after_uninstall"

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

doc_events = {
    "Customer": {
        "before_insert": "sriaas_clinic.api.customer.set_sr_customer_id",
        "before_save":   "sriaas_clinic.api.customer.normalize_phoneish_fields",
    },
    "Patient": {
        "before_insert": "sriaas_clinic.api.patient.set_sr_patient_id",
        "before_save":   "sriaas_clinic.api.patient.normalize_phoneish_fields",
        "after_insert": [
            "sriaas_clinic.api.patient.assign_followup_day",
            "sriaas_clinic.api.patient.set_followup_last_digit",
        ],
        "after_save": "sriaas_clinic.api.address.mirror_links_to_customer",
    },
    "Address": {
        "before_save": "sriaas_clinic.api.address.ensure_address_has_customer_link",
        "before_validate": "sriaas_clinic.api.address.validate_state",
    },
    "Contact": {
        "before_save": "sriaas_clinic.api.contact.normalize_phoneish_fields",
    },
    "Healthcare Practitioner": {
        "before_validate": "sriaas_clinic.api.practitioner.compose_full_name",
    },
    "Item": {
        "validate": "sriaas_clinic.api.item_package_weight.calculate_pkg_weights",
    },
    "Patient Encounter": {
        "before_save": "sriaas_clinic.api.encounter_flow.handlers.before_save_patient_encounter",
        "on_update":   "sriaas_clinic.api.encounter_flow.handlers.create_billing_on_save",
    },
    "Sales Invoice": {
        "on_submit": "sriaas_clinic.api.encounter_flow.handlers.link_pending_payment_entries",
    },
    "CRM Lead": {
        "before_save": "sriaas_clinic.api.crm_lead.normalize_phoneish_fields",
    },
}

doctype_js = {
    "Patient": [
        "public/js/patient_invoices.js",
        "public/js/patient_payments.js",
        "public/js/patient_pex_launcher.js",
        # "public/js/patient_clinical_history.js",
        "public/js/clinical_history_modal.js",
    ],
    "Address": [
        "public/js/address_state_link.js",
    ],
    "Healthcare Practitioner": [
        "public/js/healthcare_practitioner.js",
    ],
    "Patient Encounter": [
        "public/js/pe_draft_invoice.js",
        "public/js/pe_order_item.js",
        "public/js/pe_practitioner_filters.js",
        "public/js/pe_medication_filters.js",
        "public/js/pe_template_medication.js",
        "public/js/pe_manual_medication.js",
        # "public/js/pe_clinical_history.js",
        "public/js/clinical_history_modal.js",
    ],
    "Item": "public/js/item_package_weight.js",
    "Payment Entry": "public/js/payment_entry_outstanding_dialog.js",
    "CRM Lead": [
        "public/js/crm_lead_pex_launcher.js",
        "public/js/crm_lead_disposition_filter.js",
    ],
}

app_include_css = "/assets/sriaas_clinic/css/theme_overrides.css"
web_include_css = "/assets/sriaas_clinic/css/theme_overrides.css"

app_include_js = [
    "/assets/sriaas_clinic/js/patient_quick_entry_patch.js",
]

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "sriaas_clinic",
# 		"logo": "/assets/sriaas_clinic/logo.png",
# 		"title": "Sriaas Clinic",
# 		"route": "/sriaas_clinic",
# 		"has_permission": "sriaas_clinic.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/sriaas_clinic/css/sriaas_clinic.css"
# app_include_js = "/assets/sriaas_clinic/js/sriaas_clinic.js"

# include js, css files in header of web template
# web_include_css = "/assets/sriaas_clinic/css/sriaas_clinic.css"
# web_include_js = "/assets/sriaas_clinic/js/sriaas_clinic.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "sriaas_clinic/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "sriaas_clinic/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "sriaas_clinic.utils.jinja_methods",
# 	"filters": "sriaas_clinic.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "sriaas_clinic.install.before_install"
# after_install = "sriaas_clinic.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "sriaas_clinic.uninstall.before_uninstall"
# after_uninstall = "sriaas_clinic.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "sriaas_clinic.utils.before_app_install"
# after_app_install = "sriaas_clinic.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "sriaas_clinic.utils.before_app_uninstall"
# after_app_uninstall = "sriaas_clinic.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "sriaas_clinic.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"sriaas_clinic.tasks.all"
# 	],
# 	"daily": [
# 		"sriaas_clinic.tasks.daily"
# 	],
# 	"hourly": [
# 		"sriaas_clinic.tasks.hourly"
# 	],
# 	"weekly": [
# 		"sriaas_clinic.tasks.weekly"
# 	],
# 	"monthly": [
# 		"sriaas_clinic.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "sriaas_clinic.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "sriaas_clinic.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "sriaas_clinic.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["sriaas_clinic.utils.before_request"]
# after_request = ["sriaas_clinic.utils.after_request"]

# Job Events
# ----------
# before_job = ["sriaas_clinic.utils.before_job"]
# after_job = ["sriaas_clinic.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"sriaas_clinic.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

