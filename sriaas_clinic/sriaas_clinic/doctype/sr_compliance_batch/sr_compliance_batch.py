from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class SRComplianceBatch(Document):
	def autoname(self):
		self.barcode = (self.barcode or "").strip()
		self.name = self.barcode

	def validate(self):
		self.barcode = (self.barcode or "").strip()
		self.compliance_batch_no = (self.compliance_batch_no or "").strip()
		self._validate_unique_barcode()
		self._validate_item()
		self._validate_dates()

	def on_trash(self):
		if not frappe.db.table_exists("Sales Invoice Item"):
			return
		if not frappe.get_meta("Sales Invoice Item").has_field("sr_compliance_batch"):
			return

		reference = frappe.db.get_value(
			"Sales Invoice Item",
			{"sr_compliance_batch": self.name, "docstatus": 1},
			["parent", "parenttype"],
			as_dict=True,
		)
		if reference:
			frappe.throw(
				_("Compliance batch {0} is used by submitted Sales Invoice {1}. Disable it instead of deleting it.").format(
					frappe.bold(self.name),
					frappe.bold(reference.parent),
				)
			)

	def _validate_unique_barcode(self):
		if not self.barcode:
			frappe.throw(_("Barcode is required."))

		existing = frappe.db.get_value("SR Compliance Batch", {"barcode": self.barcode}, "name")
		if existing and existing != self.name:
			frappe.throw(_("Barcode {0} is already assigned to compliance batch {1}.").format(
				frappe.bold(self.barcode), frappe.bold(existing)
			))

	def _validate_item(self):
		item = frappe.db.get_value(
			"Item",
			self.item,
			["name", "disabled", "is_stock_item", "has_batch_no", "has_serial_no"],
			as_dict=True,
		)
		if not item:
			frappe.throw(_("Item {0} does not exist.").format(frappe.bold(self.item)))
		if item.disabled:
			frappe.throw(_("Item {0} is disabled.").format(frappe.bold(self.item)))
		if not item.is_stock_item:
			frappe.throw(_("Compliance barcode Item {0} must be a stock Item.").format(frappe.bold(self.item)))
		if item.has_batch_no:
			frappe.throw(
				_("Item {0} uses ERPNext Batch tracking. SR Compliance Batch can only map to an Item with Has Batch No disabled.").format(
					frappe.bold(self.item)
				)
			)
		if item.has_serial_no:
			frappe.throw(
				_("Item {0} uses ERPNext Serial No tracking. SR Compliance Batch requires a non-serialized Item so no Serial and Batch Bundle is created.").format(
					frappe.bold(self.item)
				)
			)

	def _validate_dates(self):
		if self.manufacturing_date and self.expiry_date:
			if getdate(self.expiry_date) < getdate(self.manufacturing_date):
				frappe.throw(_("Expiry Date cannot be before Manufacturing Date."))
