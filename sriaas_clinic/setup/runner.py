# apps/sriaas_clinic/sriaas_clinic/setup/runner.py
from . import (
    masters,
    patient, customer, encounter, practitioner,
    drug_prescription, item_price, item_package,
    sales_invoice, payment_entry,
    crm_lead, user,
    print_formats, ui,
)

def setup_all():
    # Apply masters (create/update seed records, workspaces, etc.) if missing
    masters.apply()

    # Patient fields/customizations
    patient.apply()

    # Customer fields/customizations
    customer.apply()

    # Patient Encounter customizations
    encounter.apply()

    # Healthcare Practitioner customizations
    practitioner.apply()

    # Drug Prescription customizations
    drug_prescription.apply()

    # Item Price customizations (Cost Price field)
    item_price.apply()

    # Item Package customizations
    item_package.apply()

    # Sales Invoice customizations
    sales_invoice.apply()

    # Payment Entry customizations
    payment_entry.apply()

    # CRM Lead custom fields
    crm_lead.apply()

    # User customizations
    user.apply()

    # Print Formats (Patient Encounter New etc.)
    print_formats.apply()

    # UI customizations (desk, workspace, tweaks, hide flags, status etc)
    ui.apply()
