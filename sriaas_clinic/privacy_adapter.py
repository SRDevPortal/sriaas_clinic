"""Clinic-owned endpoints consumed by the shared Privacy Shield engine."""
ENDPOINTS = {
    "crm_get_data": "sriaas_clinic.api.crm_lead.privacy_views.get_data",
    "crm_get_notifications": "sriaas_clinic.api.crm_lead.privacy_notifications.get_notifications",
    "crm_mark_as_read": "sriaas_clinic.api.crm_lead.privacy_notifications.mark_as_read",
    "get_encounter_context": "sriaas_clinic.api.patient_intake.get_encounter_context",
}
TEMPLATES = {"kit_invoice_preview": "print_formats/privacy_kit_invoice_preview.html"}
