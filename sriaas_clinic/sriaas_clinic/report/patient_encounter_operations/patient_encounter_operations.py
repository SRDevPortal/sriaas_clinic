from __future__ import annotations

from frappe import _

from sriaas_clinic.api.patient_encounter_listing import get_optimized_encounters


def execute(filters=None):
    filters = dict(filters or {})
    page_length = filters.pop("page_length", 50)
    start = filters.pop("start", 0)
    result = get_optimized_encounters(filters=filters, start=start, page_length=page_length)
    message = None
    if result["has_more"]:
        message = _("More rows are available. Set Start Row to {0} for the next page.").format(
            result["next_start"]
        )
    return _columns(), result["rows"], message


def _columns():
    return [
        {
            "fieldname": "name",
            "label": _("Patient Encounter"),
            "fieldtype": "Link",
            "options": "Patient Encounter",
            "width": 170,
        },
        {"fieldname": "patient", "label": _("Patient"), "fieldtype": "Link", "options": "Patient", "width": 150},
        {"fieldname": "patient_name", "label": _("Patient Name"), "fieldtype": "Data", "width": 180},
        {"fieldname": "sr_pe_id", "label": _("Encounter ID"), "fieldtype": "Data", "width": 130},
        {"fieldname": "sr_pe_mobile", "label": _("Mobile"), "fieldtype": "Data", "width": 125},
        {
            "fieldname": "sr_pe_deptt",
            "label": _("Department"),
            "fieldtype": "Link",
            "options": "Medical Department",
            "width": 140,
        },
        {"fieldname": "sr_encounter_status", "label": _("Status"), "fieldtype": "Data", "width": 140},
        {"fieldname": "sr_encounter_type", "label": _("Type"), "fieldtype": "Data", "width": 100},
        {"fieldname": "sr_encounter_place", "label": _("Place"), "fieldtype": "Data", "width": 100},
        {"fieldname": "order_total", "label": _("Order Total"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "paid_total", "label": _("Paid Total"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "owner", "label": _("Owner"), "fieldtype": "Link", "options": "User", "width": 160},
        {"fieldname": "modified", "label": _("Modified"), "fieldtype": "Datetime", "width": 160},
    ]
