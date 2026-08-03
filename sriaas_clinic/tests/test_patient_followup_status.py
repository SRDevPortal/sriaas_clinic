from unittest import TestCase
from unittest.mock import patch

import frappe

from sriaas_clinic.api.patient import validate_followup_status
from sriaas_clinic.patches.v15_0.migrate_patient_followup_status_to_master import (
    OBSOLETE_OPTIONS_PROPERTY_SETTER,
    _remove_obsolete_options_property_setter,
)
from sriaas_clinic.setup.masters import (
    FOLLOWUP_STATUS_DEFAULTS,
    FOLLOWUP_STATUS_PERMISSIONS,
    _complete_followup_status_permission,
)


class _PatientDoc(frappe._dict):
    def __init__(self, *, status_name, name="PAT-1", is_new=False):
        super().__init__(name=name, sr_followup_status=status_name)
        self._is_new = is_new

    def is_new(self):
        return self._is_new


class TestFollowupStatusConfiguration(TestCase):
    def test_canonical_statuses_and_activation_state(self):
        statuses = {
            row["status_name"]: row["is_active"]
            for row in FOLLOWUP_STATUS_DEFAULTS
        }

        self.assertEqual(
            statuses,
            {
                "Pending": 1,
                "Done": 1,
                "Agent Not Available": 1,
                "Missed": 0,
                "Rescheduled": 0,
                "Not Interested": 0,
            },
        )

    def test_agent_roles_are_explicitly_read_only(self):
        permissions = {
            row["role"]: _complete_followup_status_permission(row)
            for row in FOLLOWUP_STATUS_PERMISSIONS
        }

        for role in ("Agent", "Team Leader"):
            self.assertEqual(permissions[role]["read"], 1)
            self.assertEqual(permissions[role]["write"], 0)
            self.assertEqual(permissions[role]["create"], 0)
            self.assertEqual(permissions[role]["delete"], 0)

    @patch("sriaas_clinic.api.patient.frappe.db.get_value")
    def test_active_status_is_allowed(self, get_value):
        get_value.return_value = frappe._dict(name="Pending", is_active=1)

        validate_followup_status(_PatientDoc(status_name="Pending", is_new=True))

        get_value.assert_called_once()

    @patch("sriaas_clinic.api.patient.frappe.db.get_value")
    def test_new_inactive_status_is_rejected(self, get_value):
        get_value.return_value = frappe._dict(name="Missed", is_active=0)

        with self.assertRaises(frappe.ValidationError):
            validate_followup_status(
                _PatientDoc(status_name="Missed", is_new=True)
            )

    @patch("sriaas_clinic.api.patient.frappe.db.get_value")
    def test_unchanged_inactive_status_is_allowed(self, get_value):
        get_value.side_effect = (
            frappe._dict(name="Missed", is_active=0),
            "Missed",
        )

        validate_followup_status(_PatientDoc(status_name="Missed"))

        self.assertEqual(get_value.call_count, 2)

    @patch("sriaas_clinic.api.patient.frappe.db.get_value", return_value=None)
    def test_unknown_status_is_rejected(self, _get_value):
        with self.assertRaises(frappe.ValidationError):
            validate_followup_status(
                _PatientDoc(status_name="Unknown", is_new=True)
            )

    @patch(
        "sriaas_clinic.patches.v15_0."
        "migrate_patient_followup_status_to_master.frappe.delete_doc"
    )
    @patch(
        "sriaas_clinic.patches.v15_0."
        "migrate_patient_followup_status_to_master.frappe.db.exists",
        return_value=True,
    )
    def test_obsolete_options_property_setter_is_removed(
        self,
        _exists,
        delete_doc,
    ):
        _remove_obsolete_options_property_setter()

        delete_doc.assert_called_once_with(
            "Property Setter",
            OBSOLETE_OPTIONS_PROPERTY_SETTER,
            force=True,
            ignore_permissions=True,
            delete_permanently=True,
        )
