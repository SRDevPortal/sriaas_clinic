import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
from sriaas_clinic.api.s3 import access, pending_proofs as proofs


class PendingPaymentProofTests(unittest.TestCase):
    def setUp(self):
        self.cache = MagicMock()
        self.receipts = {}
        self.cache.set_value.side_effect = lambda key, value, **kw: self.receipts.update({key: value})
        self.cache.get_value.side_effect = lambda key: self.receipts.get(key)
        self.cache.delete_value.side_effect = lambda key: self.receipts.pop(key, None)
        self.rollback = MagicMock()
        self.doc = MagicMock()
        self.doc.doctype = "Patient Encounter"
        self.doc.name = "PE-TEST"
        self.doc.has_permission.return_value = True
        self.file = SimpleNamespace(attached_to_doctype="Patient Encounter", attached_to_field="mmp_payment_proof", attached_to_name="PE-TEST")
        self.session = SimpleNamespace(user="uploader")
        for mocked in [
            patch.object(frappe, "session", self.session),
            patch.object(frappe, "cache", self.cache),
            patch.object(frappe, "db", SimpleNamespace(after_rollback=self.rollback)),
            patch.object(frappe, "get_doc", return_value=self.doc),
            patch.object(proofs, "_fields_allowed", return_value=True),
        ]:
            mocked.start()
            self.addCleanup(mocked.stop)

    def remember(self):
        proofs.remember_upload(self.file, "synthetic/proof.pdf", "test-bucket")

    def test_uploader_can_preview_with_current_write_permission(self):
        self.remember()
        self.assertTrue(proofs.allows_preview(self.doc, "synthetic/proof.pdf", "test-bucket"))
        self.doc.check_permission.assert_called_once_with("write")
        self.assertEqual(self.cache.set_value.call_args.kwargs["expires_in_sec"], 1800)

    def test_user_parent_object_and_bucket_are_bound(self):
        self.remember()
        self.session.user = "other-user"
        self.assertFalse(proofs.allows_preview(self.doc, "synthetic/proof.pdf", "test-bucket"))
        self.session.user = "uploader"
        self.assertFalse(proofs.allows_preview(self.doc, "other.pdf", "test-bucket"))
        self.assertFalse(proofs.allows_preview(self.doc, "synthetic/proof.pdf", "other-bucket"))
        self.doc.name = "PE-OTHER"
        self.assertFalse(proofs.allows_preview(self.doc, "synthetic/proof.pdf", "test-bucket"))
        self.doc.name = "PE-TEST"
        self.doc.doctype = "Other"
        self.assertFalse(proofs.allows_preview(self.doc, "synthetic/proof.pdf", "test-bucket"))

    def test_expired_or_rolled_back_upload_is_denied(self):
        self.remember()
        self.rollback.add.call_args.args[0]()
        self.assertFalse(proofs.allows_preview(self.doc, "synthetic/proof.pdf", "test-bucket"))

    def test_revoked_write_or_field_permission_is_denied(self):
        self.remember()
        self.doc.check_permission.side_effect = frappe.PermissionError
        with self.assertRaises(frappe.PermissionError):
            proofs.allows_preview(self.doc, "synthetic/proof.pdf", "test-bucket")
        self.doc.check_permission.side_effect = None
        proofs._fields_allowed.return_value = False
        self.assertFalse(proofs.allows_preview(self.doc, "synthetic/proof.pdf", "test-bucket"))

    def test_guest_wrong_field_and_non_writer_create_no_receipt(self):
        self.session.user = "Guest"
        self.remember()
        self.session.user = "uploader"
        self.file.attached_to_field = "other"
        self.remember()
        self.file.attached_to_field = "mmp_payment_proof"
        self.doc.has_permission.return_value = False
        self.remember()
        self.cache.set_value.assert_not_called()

    def test_signer_checks_read_before_pending_preview(self):
        self.remember()
        with patch.object(frappe, "conf", {}), patch.object(frappe, "get_all", return_value=[]), patch.object(frappe, "get_meta", return_value=SimpleNamespace(istable=False)), patch.object(access, "references_attachment", return_value=False):
            access.authorize_source("s3://synthetic/proof.pdf", "synthetic/proof.pdf", "test-bucket", "test-region", "Patient Encounter", "PE-TEST")
            self.doc.check_permission.assert_any_call("read")
            self.doc.check_permission.assert_any_call("write")
            self.doc.check_permission.side_effect = frappe.PermissionError
            with self.assertRaises(frappe.PermissionError):
                access.authorize_source("s3://synthetic/proof.pdf", "synthetic/proof.pdf", "test-bucket", "test-region", "Patient Encounter", "PE-TEST")

    def test_parent_and_child_field_permissions_both_required(self):
        meta = SimpleNamespace(
            get_field=lambda _: SimpleNamespace(fieldtype="Table", options="SR Multi Mode Payment", permlevel=1),
            get_permlevel_access=MagicMock(return_value=[0, 1]),
        )
        with patch.object(frappe, "get_meta", return_value=meta), patch.object(proofs, "get_permitted_fields") as fields:
            real_helper = self._fields_helper
            fields.return_value = ["mmp_payment_proof"]
            self.assertTrue(real_helper())
            fields.return_value = []
            self.assertFalse(real_helper())
            fields.return_value = ["mmp_payment_proof"]
            meta.get_permlevel_access.return_value = [0]
            self.assertFalse(real_helper())

    _fields_helper = staticmethod(proofs._fields_allowed)
