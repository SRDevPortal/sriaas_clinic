from __future__ import annotations

import frappe
from frappe.utils import quote
from frappe.utils.file_manager import save_file


SOURCE_DOCTYPE = "CRM Lead"
TARGET_DOCTYPE = "Patient Encounter"
SOURCE_FIELD = "sr_source_crm_lead"


def copy_crm_lead_attachments_to_encounter(doc, method=None):
	lead_name = (doc.get(SOURCE_FIELD) or "").strip()
	if not lead_name or not doc.name:
		return

	if not frappe.db.exists(SOURCE_DOCTYPE, lead_name):
		return

	for file_name in _get_lead_file_names(lead_name):
		try:
			_copy_file_to_encounter(file_name, doc.name)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"CRM_LEAD_ATTACHMENT_COPY_FAILED | lead={lead_name} | encounter={doc.name}",
			)


def _get_lead_file_names(lead_name: str) -> list[str]:
	return frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": SOURCE_DOCTYPE,
			"attached_to_name": lead_name,
			"is_folder": 0,
		},
		pluck="name",
		order_by="creation asc",
	)


def _copy_file_to_encounter(file_name: str, encounter_name: str) -> None:
	source_file = frappe.get_doc("File", file_name)
	file_url = (source_file.file_url or "").strip()
	file_name_value = source_file.file_name or source_file.name

	if _target_file_exists(encounter_name, file_url, file_name_value):
		return

	if file_url.startswith(("/files/", "/private/files/")):
		_copy_local_file_content(source_file, encounter_name)
		return

	copied_file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name_value,
			"file_url": source_file.file_url,
			"is_private": source_file.is_private,
			"attached_to_doctype": TARGET_DOCTYPE,
			"attached_to_name": encounter_name,
			"attached_to_field": source_file.attached_to_field,
			"folder": source_file.folder,
			"content_hash": source_file.content_hash,
		}
	).insert(ignore_permissions=True)

	if copied_file.is_private != source_file.is_private:
		copied_file.db_set("is_private", source_file.is_private, update_modified=False)

	_update_attachment_comment(copied_file)


def _copy_local_file_content(source_file, encounter_name: str) -> None:
	content = source_file.get_content()
	if isinstance(content, str):
		content = content.encode()

	save_file(
		source_file.file_name or source_file.name,
		content,
		TARGET_DOCTYPE,
		encounter_name,
		is_private=source_file.is_private,
	)


def _target_file_exists(encounter_name: str, file_url: str, file_name: str) -> bool:
	base_filters = {
		"attached_to_doctype": TARGET_DOCTYPE,
		"attached_to_name": encounter_name,
		"is_folder": 0,
	}

	if file_url:
		return bool(frappe.db.exists("File", {**base_filters, "file_url": file_url}))

	if file_name and frappe.db.exists("File", {**base_filters, "file_name": file_name}):
		return True

	return False


def _update_attachment_comment(file_doc) -> None:
	if not file_doc.file_url or not file_doc.attached_to_doctype or not file_doc.attached_to_name:
		return

	icon = ' <i class="fa fa-lock text-warning"></i>' if file_doc.is_private else ""
	file_url = quote(frappe.safe_encode(file_doc.file_url), safe="/:")
	file_name = file_doc.file_name or file_doc.file_url
	content = f"<a href='{file_url}' target='_blank'>{file_name}</a>{icon}"

	comment_name = frappe.db.get_value(
		"Comment",
		{
			"reference_doctype": file_doc.attached_to_doctype,
			"reference_name": file_doc.attached_to_name,
			"comment_type": "Attachment",
			"content": ["like", f"%>{file_name}</a>%"],
		},
		"name",
		order_by="creation desc",
	)

	if comment_name:
		frappe.db.set_value("Comment", comment_name, "content", content, update_modified=False)
