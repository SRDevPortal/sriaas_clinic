# apps/sriaas_clinic/sriaas_clinic/setup/runner.py
from . import (
    masters,
    patient, customer, practitioner, contact,
    encounter, crm_lead, patient_appointment,
    drug_prescription, item_price, item_package,
    sales_invoice, payment_entry, purchase_order, user,
    print_formats,
)

def setup_all():
    # Master Data fields/customizations
    masters.apply()
    # Patient fields/customizations
    patient.apply()
    # Customer fields/customizations
    customer.apply()
    # Practitioner fields/customizations
    practitioner.apply()
    # Contact/Address fields/customizations
    contact.apply()
    # Patient Encounter fields/customizations
    encounter.apply()
    # CRM Lead fields/customizations
    crm_lead.apply()
    # Patient Appointment fields/customizations
    patient_appointment.apply()
    # Drug Prescription fields/customizations
    drug_prescription.apply()    
    # Item Price fields/customizations
    item_price.apply()
    # Item Package fields/customizations
    item_package.apply()
    # Sales Invoice fields/customizations
    sales_invoice.apply()
    # Payment Entry fields/customizations
    payment_entry.apply()    
    # Purchase Order fields/customizations
    purchase_order.apply()
    # User fields/customizations
    user.apply()
    # Print Format fields/customizations
    print_formats.apply()
