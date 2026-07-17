from unittest import TestCase
from unittest.mock import patch

import frappe

from sriaas_clinic.api.patient_encounter_listing import (
    MAX_PAGE_LENGTH,
    _build_parent_filters,
    _normalize_phone_lookup,
    get_optimized_encounters,
)


class _Meta:
    def __init__(self, fields):
        self.fields = set(fields)

    def has_field(self, fieldname):
        return fieldname in self.fields


class TestPatientEncounterFilters(TestCase):
    def test_phone_filter_prefers_normalized_exact_field(self):
        filters = _build_parent_filters(
            {"mobile": "+91 98765-43210"},
            _Meta({"sr_pe_mobile", "sr_pe_mobile_norm"}),
        )

        self.assertEqual(filters, [["sr_pe_mobile_norm", "=", "9876543210"]])
        self.assertNotIn("like", str(filters).lower())

    def test_exact_operational_filters_and_date_range(self):
        filters = _build_parent_filters(
            {
                "sr_pe_deptt": "Ayurveda",
                "sr_encounter_status": "Draft",
                "creation_from": "2026-07-01",
                "creation_to": "2026-07-31",
            },
            _Meta({"sr_pe_deptt", "sr_encounter_status"}),
        )

        self.assertIn(["sr_pe_deptt", "=", "Ayurveda"], filters)
        self.assertIn(["sr_encounter_status", "=", "Draft"], filters)
        self.assertIn(["creation", ">=", "2026-07-01"], filters)
        self.assertIn(["creation", "<=", "2026-07-31"], filters)

    def test_phone_normalization(self):
        self.assertEqual(_normalize_phone_lookup("+91 98765-43210"), "9876543210")


class TestOptimizedPatientEncounterListing(TestCase):
    @patch("sriaas_clinic.api.patient_encounter_listing._child_totals")
    @patch("sriaas_clinic.api.patient_encounter_listing.frappe.get_list")
    @patch("sriaas_clinic.api.patient_encounter_listing.frappe.get_meta")
    @patch("sriaas_clinic.api.patient_encounter_listing.frappe.has_permission")
    def test_parent_rows_are_paginated_before_child_aggregation(
        self,
        has_permission,
        get_meta,
        get_list,
        child_totals,
    ):
        get_meta.return_value = _Meta(
            {
                "patient",
                "patient_name",
                "sr_pe_id",
                "sr_pe_deptt",
                "sr_encounter_status",
                "modified",
            }
        )
        get_list.return_value = [
            frappe._dict(name="PE-1"),
            frappe._dict(name="PE-2"),
            frappe._dict(name="PE-3"),
        ]
        child_totals.side_effect = (
            {"PE-1": 100, "PE-2": 200},
            {"PE-1": 50, "PE-2": 80},
        )

        result = get_optimized_encounters(
            {"sr_pe_deptt": "Ayurveda"},
            page_length=2,
        )

        has_permission.assert_called_once_with("Patient Encounter", "read", throw=True)
        self.assertEqual(get_list.call_args.kwargs["page_length"], 3)
        self.assertEqual([row.name for row in result["rows"]], ["PE-1", "PE-2"])
        self.assertTrue(result["has_more"])
        self.assertEqual(result["next_start"], 2)
        self.assertEqual(result["rows"][0].order_total, 100)
        self.assertEqual(result["rows"][0].paid_total, 50)
        for call in child_totals.call_args_list:
            self.assertEqual(call.args[2], ["PE-1", "PE-2"])

    @patch("sriaas_clinic.api.patient_encounter_listing._child_totals", return_value={})
    @patch("sriaas_clinic.api.patient_encounter_listing.frappe.get_list", return_value=[])
    @patch("sriaas_clinic.api.patient_encounter_listing.frappe.get_meta")
    @patch("sriaas_clinic.api.patient_encounter_listing.frappe.has_permission")
    def test_page_length_is_bounded(self, _permission, get_meta, get_list, _totals):
        get_meta.return_value = _Meta({"modified"})

        get_optimized_encounters(page_length=1000)

        self.assertEqual(get_list.call_args.kwargs["page_length"], MAX_PAGE_LENGTH + 1)
