import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch
import frappe
from privacy_shield.policy import Capabilities
from sriaas_clinic.api import clinical_history as history


class ClinicalHistoryPrivacyTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(history, "enabled", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.raw = {"doctype": "Patient Encounter", "name": "ENC-1", "patient": "PAT-1",
                    "sr_notes": "Phone: 2025550101. Age: 27. Blood urea: 124 mg/dL.",
                    "sr_complaints": "Call +91 2025550199", "sr_pe_mobile": "2025550101",
                    "drug_prescription": [{"dosage": "1-0-1", "sr_drug_instruction": "Call 2025550199"}]}

    def test_masked_role_notes_are_response_only(self):
        original = deepcopy(self.raw)
        result = history.project_history_document(self.raw, Capabilities())
        self.assertNotIn("2025550101", str(result))
        self.assertNotIn("2025550199", str(result))
        self.assertIn("Age: 27. Blood urea: 124 mg/dL.", result["sr_notes"])
        self.assertEqual(result["name"], "ENC-1")
        self.assertEqual(self.raw, original)

    def test_full_access_and_disabled_privacy_preserve_notes(self):
        self.assertEqual(history.project_history_document(self.raw, Capabilities(True))["sr_notes"], self.raw["sr_notes"])
        with patch.object(history, "enabled", return_value=False):
            self.assertEqual(history.project_history_document(self.raw, Capabilities()), self.raw)

    def test_read_authorization_and_field_permissions_precede_projection(self):
        parent, encounter = MagicMock(), MagicMock()
        encounter.as_dict.return_value = deepcopy(self.raw)
        with patch.object(frappe, "get_doc", side_effect=[parent, encounter]), \
             patch.object(frappe, "get_list", return_value=[frappe._dict(name="ENC-1")]), \
             patch.object(history, "current_capabilities", return_value=Capabilities()):
            result = history.get_encounters.__wrapped__("PAT-1")
        parent.check_permission.assert_called_once_with("read")
        encounter.check_permission.assert_called_once_with("read")
        encounter.apply_fieldlevel_read_permissions.assert_called_once()
        self.assertNotIn("2025550101", str(result))

    def test_inaccessible_patient_does_not_query_history(self):
        parent = MagicMock()
        parent.check_permission.side_effect = frappe.PermissionError
        with patch.object(frappe, "get_doc", return_value=parent), patch.object(frappe, "get_list") as query:
            with self.assertRaises(frappe.PermissionError):
                history.get_encounters.__wrapped__("PAT-1")
            query.assert_not_called()

    def test_hidden_comments_and_provider_fields_are_not_returned(self):
        result = history.project_history_document({**self.raw,
            "encounter_comment": "Phone: 2025550199", "provider_payload": "2025550101"}, Capabilities())
        self.assertNotIn("encounter_comment", result)
        self.assertNotIn("provider_payload", result)
