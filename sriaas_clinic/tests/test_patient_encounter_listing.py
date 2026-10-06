from unittest import TestCase
from unittest.mock import patch

import frappe

from sriaas_clinic.api.patient_encounter_listing import (
    MAX_PAGE_LENGTH,
    _build_parent_filters,
    _normalize_phone_lookup,
    get_optimized_encounters as _whitelisted_get_optimized_encounters,
)
from sriaas_clinic.api.patient_encounter_phone import sync_normalized_mobile
from sriaas_clinic.phone_utils import normalize_phone_last10
from sriaas_clinic.maintenance.patient_encounter_phone_backfill import normalized_update
from sriaas_clinic.maintenance.patient_encounter_phone_backfill import _ensure_phone_index


get_optimized_encounters = _whitelisted_get_optimized_encounters.__wrapped__


class _Meta:
    def __init__(self, fields):
        self.fields = set(fields)

    def has_field(self, fieldname):
        return fieldname in self.fields


class TestPatientEncounterFilters(TestCase):
    @patch(
        "sriaas_clinic.api.patient_encounter_listing._indexed_phone_lookup_enabled",
        return_value=True,
    )
    def test_phone_filter_prefers_normalized_exact_field(self, _enabled):
        filters = _build_parent_filters(
            {"mobile": "+91 98765-43210"},
            _Meta({"sr_pe_mobile", "sr_pe_mobile_norm"}),
        )

        self.assertEqual(filters, [["sr_pe_mobile_norm", "=", "9876543210"]])
        self.assertNotIn("like", str(filters).lower())

    @patch(
        "sriaas_clinic.api.patient_encounter_listing._indexed_phone_lookup_enabled",
        return_value=False,
    )
    def test_phone_filter_uses_compatible_exact_field_while_feature_is_disabled(self, _enabled):
        filters = _build_parent_filters(
            {"mobile": "9876543210"},
            _Meta({"sr_pe_mobile", "sr_pe_mobile_norm"}),
        )

        self.assertEqual(filters, [["sr_pe_mobile", "=", "9876543210"]])
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

    def test_phone_normalization_variants_and_invalid_values(self):
        expected = "9876543210"
        self.assertEqual(normalize_phone_last10("9876543210"), expected)
        self.assertEqual(normalize_phone_last10("+91 98765-43210"), expected)
        self.assertEqual(normalize_phone_last10("0091 (98765) 43210"), expected)
        self.assertEqual(normalize_phone_last10("00"), "")
        self.assertEqual(normalize_phone_last10(","), "")
        self.assertEqual(normalize_phone_last10(None), "")

    @patch("sriaas_clinic.api.patient_encounter_listing.frappe.throw", side_effect=ValueError)
    def test_phone_filter_rejects_short_input(self, _throw):
        with self.assertRaises(ValueError):
            _build_parent_filters(
                {"mobile": "00"},
                _Meta({"sr_pe_mobile", "sr_pe_mobile_norm"}),
            )

    def test_save_hook_synchronizes_existing_mobile(self):
        doc = frappe._dict(
            patient="PAT-1",
            sr_pe_mobile="+91 98765-43210",
            sr_pe_mobile_norm="",
        )

        sync_normalized_mobile(doc)

        self.assertEqual(doc.sr_pe_mobile_norm, "9876543210")

    def test_backfill_skips_correct_key_and_repairs_mismatch(self):
        self.assertEqual(
            normalized_update(
                frappe._dict(sr_pe_mobile="+91 98765-43210", sr_pe_mobile_norm="9876543210")
            ),
            {},
        )
        self.assertEqual(
            normalized_update(
                frappe._dict(sr_pe_mobile="+91 98765-43210", sr_pe_mobile_norm="incorrect")
            ),
            {"sr_pe_mobile_norm": "9876543210"},
        )

    @patch("sriaas_clinic.api.patient_encounter_phone._patient_mobile", return_value="9876543210")
    def test_save_hook_fetches_patient_mobile_when_encounter_mobile_is_empty(self, patient_mobile):
        doc = frappe._dict(patient="PAT-1", sr_pe_mobile="", sr_pe_mobile_norm="")

        sync_normalized_mobile(doc)

        patient_mobile.assert_called_once_with("PAT-1")
        self.assertEqual(doc.sr_pe_mobile, "9876543210")
        self.assertEqual(doc.sr_pe_mobile_norm, "9876543210")


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
        self.assertEqual(get_list.call_args.kwargs["order_by"], "modified desc, name desc")
        self.assertEqual([row.name for row in result["rows"]], ["PE-1", "PE-2"])
        self.assertTrue(result["has_more"])
        self.assertEqual(result["next_start"], 2)
        self.assertEqual(result["rows"][0].order_total, 100)
        self.assertEqual(result["rows"][0].paid_total, 50)
        for call in child_totals.call_args_list:
            self.assertEqual(call.args[2], ["PE-1", "PE-2"])

    @patch(
        "sriaas_clinic.maintenance.patient_encounter_phone_backfill._index_exists",
        return_value=True,
    )
    @patch(
        "sriaas_clinic.maintenance.patient_encounter_phone_backfill._fields_ready",
        return_value=True,
    )
    def test_phone_index_creation_is_idempotent(self, _fields_ready, _index_exists):
        result = _ensure_phone_index()

        self.assertFalse(result["created"])
        self.assertTrue(result["exists"])

    @patch("sriaas_clinic.maintenance.patient_encounter_phone_backfill._add_phone_index")
    @patch(
        "sriaas_clinic.maintenance.patient_encounter_phone_backfill._phone_key_coverage",
        return_value={"ready": True, "missing": 0, "mismatch": 0},
    )
    @patch(
        "sriaas_clinic.maintenance.patient_encounter_phone_backfill._index_exists",
        return_value=False,
    )
    @patch(
        "sriaas_clinic.maintenance.patient_encounter_phone_backfill._fields_ready",
        return_value=True,
    )
    def test_phone_index_is_created_only_after_coverage(
        self,
        _fields_ready,
        _index_exists,
        _coverage,
        add_phone_index,
    ):
        result = _ensure_phone_index()

        add_phone_index.assert_called_once_with()
        self.assertTrue(result["created"])

    @patch("sriaas_clinic.api.patient_encounter_listing._child_totals", return_value={})
    @patch("sriaas_clinic.api.patient_encounter_listing.frappe.get_list", return_value=[])
    @patch("sriaas_clinic.api.patient_encounter_listing.frappe.get_meta")
    @patch("sriaas_clinic.api.patient_encounter_listing.frappe.has_permission")
    def test_page_length_is_bounded(self, _permission, get_meta, get_list, _totals):
        get_meta.return_value = _Meta({"modified"})

        get_optimized_encounters(page_length=1000)

        self.assertEqual(get_list.call_args.kwargs["page_length"], MAX_PAGE_LENGTH + 1)
