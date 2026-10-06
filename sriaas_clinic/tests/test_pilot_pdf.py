import unittest
from unittest.mock import patch, MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path
import hashlib
import frappe
from sriaas_clinic import pilot_pdf as pilot


class PilotPDFTests(unittest.TestCase):
    def setUp(self):
        self.stack = __import__('contextlib').ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(frappe.local, 'site', 'privacy-pilot.local', create=True))
        self.stack.enter_context(patch.object(frappe.local, 'conf', frappe._dict(privacy_shield_desk_enabled=True, clinic_pdf_pilot_enabled=True), create=True))
        self.stack.enter_context(patch.object(frappe.local, 'form_dict', frappe._dict(doctype='Sales Invoice', name='TEST'), create=True))

    def test_other_generator_is_untouched(self):
        with patch.object(pilot, 'require_access') as guard:
            self.assertIsNone(pilot.generate(None, '', pdf_generator='wkhtmltopdf'))
            guard.assert_not_called()

    def test_shared_site_denied(self):
        frappe.local.site='sriaas.local'
        with self.assertRaises(frappe.PermissionError):pilot.require_access('Kit Billing Invoice')

    def test_either_gate_off_denied(self):
        for key in ['privacy_shield_desk_enabled','clinic_pdf_pilot_enabled']:
            with self.subTest(key=key):
                frappe.conf[key]=False
                with self.assertRaises(frappe.PermissionError):pilot.require_access('Kit Billing Invoice')
                frappe.conf[key]=True

    def test_restricted_viewer_denied(self):
        with patch('privacy_shield.import_access.restricted',return_value=True):
            with self.assertRaises(frappe.PermissionError):pilot.require_access('Kit Billing Invoice')

    def test_supplied_document_denied(self):
        frappe.local.form_dict.doc={'name':'TEST'}
        with patch('privacy_shield.import_access.restricted',return_value=False):
            with self.assertRaises(frappe.PermissionError):pilot.require_access('Kit Billing Invoice')

    def test_native_permissions_required(self):
        with patch('privacy_shield.import_access.restricted',return_value=False),patch.object(frappe,'get_doc') as get:
            get.return_value.check_permission.side_effect=frappe.PermissionError
            with self.assertRaises(frappe.PermissionError):pilot.require_access('Kit Billing Invoice')

    def test_matching_format_and_doctype_required(self):
        with patch('privacy_shield.import_access.restricted',return_value=False):
            with self.assertRaises(frappe.PermissionError):pilot.require_access('Patient Encounter New')

    def test_pin_required_and_verified(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'renderer';path.write_bytes(b'synthetic binary')
            frappe.conf.clinic_pdf_pilot_binary=str(path)
            with self.assertRaises(ValueError):pilot.renderer_path()
            frappe.conf.clinic_pdf_pilot_sha256=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(pilot.renderer_path(),str(path))
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):pilot.renderer_path()

    def test_unknown_format_rejected(self):
        with self.assertRaises(ValueError):pilot.compatible_html('', 'Other')

    def test_stylesheet_drift_rejected(self):
        with self.assertRaises(ValueError):pilot.compatible_html('<style>:root {--sr-color:#fff;}</style>','Kit Billing Invoice')

    def test_remote_and_traversal_styles_rejected(self):
        for href in ['https://example.invalid/x.css','/assets/../../../../etc/passwd']:
            with self.subTest(href=href),self.assertRaises(ValueError):
                pilot.inline_print_styles('<link rel="stylesheet" href="'+href+'">')
