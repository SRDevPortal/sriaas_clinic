"""Clinic-owned entry point for the Patient intake UI."""
import frappe


@frappe.whitelist()
def get_context(source=None):
    from privacy_shield.patient_intake import context
    return context(source)


@frappe.whitelist()
def get_encounter_context(patient=None):
    from privacy_shield.link_fetch import encounter_context
    return encounter_context(patient)
