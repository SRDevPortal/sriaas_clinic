from __future__ import annotations

import frappe

from sriaas_clinic.phone_utils import normalize_phone_last10


def sync_normalized_mobile(doc, method=None) -> None:
    """Keep the Patient Encounter phone key synchronized without extra writes."""
    source_mobile = doc.get("sr_pe_mobile")
    if not source_mobile and doc.get("patient"):
        source_mobile = _patient_mobile(doc.patient)
        if source_mobile:
            doc.sr_pe_mobile = source_mobile

    normalized = normalize_phone_last10(source_mobile)
    if doc.get("sr_pe_mobile_norm") != normalized:
        doc.sr_pe_mobile_norm = normalized


def _patient_mobile(patient: str) -> str:
    return frappe.db.get_value("Patient", patient, "mobile") or ""
