# sriaas_clinic/setup/runner.py
from .utils import ensure_module_def, reload_local_json_doctypes
from . import (
    masters,
    patient, customer, address,
    encounter, practitioner, drug_prescription,
    sales_invoice, item_package, payment_entry,
    crm_lead,
    print_formats, ui
)

def setup_all():
    # Make sure Module Def exists
    ensure_module_def()
    
    # If you want to specify module/app name manually, use this instead:
    # ensure_module_def("SRIAAS Clinic", "sriaas_clinic")

    # Reload any JSON Doctypes you ship with the app (if changed)
    reload_local_json_doctypes([
        # (keep empty unless you ship JSON Doctype)
        # "sr_patient_disable_reason","sr_patient_invoice_view",
        # "sr_patient_payment_view","sr_sales_type",
        # "sr_encounter_status","sr_instructions",
        # "sr_medication_template_item","sr_medication_template",
        # "sr_delivery_type","sr_order_item","sr_lead_source"
    ])

    # Masters (Create DocTypes if missing)
    masters.apply()

    # Patient fields/customizations
    patient.apply()

    # Customer fields/customizations
    customer.apply()

    # Address customizations (State dropdown)
    address.apply()

    # Patient Encounter customizations
    encounter.apply()

    # Healthcare Practitioner customizations
    practitioner.apply()

    # Drug Prescription customizations
    drug_prescription.apply()

    # Sales Invoice customizations
    sales_invoice.apply()

    # Item Package customizations
    item_package.apply()

    # Payment Entry customizations
    payment_entry.apply()

    # CRM Lead custom fields
    crm_lead.apply()

    # Print Formats (Patient Encounter New etc.)
    print_formats.apply()

    # UI customizations (desk, workspace, tweaks, hide flags, status etc)
    ui.apply()
