import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import frappe
from sriaas_clinic.api.s3 import upload, delete, practitioner_images as images, file_hooks

class PractitionerImageTests(unittest.TestCase):
    def setUp(self):
        self.conf = patch.object(frappe, "conf", {"aws_s3_bucket": "sriaas-frappe-test", "aws_s3_region": "ap-south-1"})
        self.conf.start()
        self.addCleanup(self.conf.stop)
        session = patch.object(frappe, "session", SimpleNamespace(user="Administrator"))
        session.start()
        self.addCleanup(session.stop)

    def doc(self, field="image"):
        return SimpleNamespace(attached_to_doctype="Healthcare Practitioner",
            attached_to_field=field, attached_to_name="Dr Test", name="unique",
            file_name="Portrait.JPG", file_url="/private/files/Portrait.JPG")

    def test_only_profile_field_is_public(self):
        self.assertTrue(images.is_practitioner_image(self.doc()))
        self.assertFalse(images.is_practitioner_image(self.doc("certificate")))
        doc = self.doc()
        doc.attached_to_doctype = "Patient"
        self.assertFalse(images.is_practitioner_image(doc))

    def test_url_and_endpoint_validation(self):
        url = images.image_url("doctor/unique_portrait.jpg")
        self.assertEqual(url, "https://sriaas-frappe-test.s3.ap-south-1.amazonaws.com/doctor/unique_portrait.jpg")
        self.assertEqual(images.public_image_key(url), "doctor/unique_portrait.jpg")
        for url in ["https://evil.example/doctor/a.jpg",
                    "https://sriaas-frappe-test.s3.ap-south-1.amazonaws.com/private/a.jpg",
                    images.image_url("doctor/../private/a.jpg")]:
            self.assertIsNone(images.public_image_key(url))

    def test_upload_bucket_key_and_private_routing(self):
        with tempfile.NamedTemporaryFile() as local:
            local.write(b"test")
            local.flush()
            for field in ("image", "certificate"):
                client = MagicMock()
                with patch.object(upload, "get_s3_client", return_value=client), patch.object(upload, "get_bucket", return_value="private-bucket"), patch.object(upload, "_get_company_abbr", return_value="test"), patch.object(upload, "get_file_path", return_value=local.name), patch.object(upload, "get_logger"):
                    key = upload.upload_file_to_s3(self.doc(field))
                params = client.put_object.call_args.kwargs
                if field == "image":
                    self.assertEqual(params["Bucket"], "sriaas-frappe-test")
                    self.assertEqual(key, "doctor/unique_portrait.jpg")
                else:
                    self.assertEqual(params["Bucket"], "private-bucket")
                    self.assertTrue(key.startswith("test/healthcare-practitioner/"))
                self.assertNotIn("ACL", params)

    def test_public_image_delete_uses_public_bucket(self):
        client = MagicMock()
        with patch.object(delete, "get_s3_client", return_value=client):
            delete.delete_file_from_s3(images.image_url("doctor/test.jpg"))
        client.delete_object.assert_called_once_with(Bucket="sriaas-frappe-test", Key="doctor/test.jpg")

    def test_hook_saves_public_url_and_privacy(self):
        doc = self.doc()
        doc.is_folder = False
        doc.db_set = MagicMock()
        with patch.object(file_hooks, "is_s3_enabled", return_value=True), patch.object(file_hooks, "get_file_path", return_value="/missing"), patch.object(file_hooks, "upload_file_to_s3", return_value="doctor/test.jpg"):
            file_hooks.handle_file_after_insert(doc)
        doc.db_set.assert_called_once_with({"file_url": images.image_url("doctor/test.jpg"), "is_private": 0}, update_modified=False)

    def test_trash_preserves_bucket_in_url(self):
        doc = self.doc()
        doc.file_url = images.image_url("doctor/test.jpg")
        with patch.object(file_hooks, "_file_url_used_by_another_file", return_value=False), patch.object(file_hooks, "_skip_s3_delete_file_names", return_value=set()), patch.object(file_hooks, "delete_file_from_s3") as remove:
            file_hooks.handle_file_on_trash(doc)
        remove.assert_called_once_with(doc.file_url)
