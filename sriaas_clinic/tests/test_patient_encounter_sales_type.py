from unittest import TestCase
from unittest.mock import patch

import frappe

from sriaas_clinic.api.encounter_flow.handlers import validate_sales_type_required


class TestPatientEncounterSalesType(TestCase):
    @patch(
        "sriaas_clinic.api.encounter_flow.handlers.frappe.throw",
        side_effect=ValueError,
    )
    def test_sales_type_is_required_for_order_and_appointment(self, throw):
        for encounter_type in ("Order", "Appointment"):
            with self.subTest(encounter_type=encounter_type):
                with self.assertRaises(ValueError):
                    validate_sales_type_required(
                        frappe._dict(
                            sr_encounter_type=encounter_type,
                            sr_sales_type=None,
                        )
                    )

        self.assertEqual(throw.call_count, 2)

    def test_sales_type_is_not_required_for_followup(self):
        validate_sales_type_required(
            frappe._dict(
                sr_encounter_type="Followup",
                sr_sales_type=None,
            )
        )

    def test_sales_type_allows_order_and_appointment(self):
        for encounter_type in ("Order", "Appointment"):
            with self.subTest(encounter_type=encounter_type):
                validate_sales_type_required(
                    frappe._dict(
                        sr_encounter_type=encounter_type,
                        sr_sales_type="Direct Sale",
                    )
                )
