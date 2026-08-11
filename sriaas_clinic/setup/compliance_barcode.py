from __future__ import annotations

import frappe

from .utils import create_cf_with_module, ensure_field_after, upsert_property_setter


ITEM = "Item"
SALES_INVOICE_ITEM = "Sales Invoice Item"


def apply():
	_create_item_fields()
	_create_sales_invoice_item_fields()
	_configure_fields()


def _create_item_fields():
	create_cf_with_module(
		{
			ITEM: [
				{
					"fieldname": "sr_compliance_tracking_section",
					"label": "SR Barcode Compliance",
					"fieldtype": "Section Break",
					"insert_after": "serial_nos_and_batches",
					"collapsible": 1,
				},
				{
					"fieldname": "sr_requires_compliance_batch",
					"label": "Requires Compliance Batch",
					"fieldtype": "Check",
					"default": "0",
					"insert_after": "sr_compliance_tracking_section",
					"description": "Require a compliance-only barcode/batch snapshot on invoices. This does not enable ERPNext Batch inventory.",
					"in_standard_filter": 1,
				},
				{
					"fieldname": "sr_legacy_item",
					"label": "Legacy Batch-Tracked Item",
					"fieldtype": "Link",
					"options": "Item",
					"insert_after": "sr_requires_compliance_batch",
					"description": "Optional audit link to the historical batch-enabled Item replaced by this Item.",
					"in_standard_filter": 1,
				},
			]
		}
	)


def _create_sales_invoice_item_fields():
	create_cf_with_module(
		{
			SALES_INVOICE_ITEM: [
				{
					"fieldname": "sr_compliance_batch",
					"label": "Compliance Batch",
					"fieldtype": "Link",
					"options": "SR Compliance Batch",
					"insert_after": "item_code",
					"read_only": 1,
					"print_hide": 1,
				},
				{
					"fieldname": "sr_compliance_batch_no",
					"label": "Compliance Batch No",
					"fieldtype": "Data",
					"insert_after": "sr_compliance_batch",
					"read_only": 1,
					"in_list_view": 1,
					"columns": 2,
				},
				{
					"fieldname": "sr_compliance_mfg_date",
					"label": "Manufacturing Date",
					"fieldtype": "Date",
					"insert_after": "sr_compliance_batch_no",
					"read_only": 1,
				},
				{
					"fieldname": "sr_compliance_expiry_date",
					"label": "Expiry Date",
					"fieldtype": "Date",
					"insert_after": "sr_compliance_mfg_date",
					"read_only": 1,
					"in_list_view": 1,
					"columns": 1,
				},
				{
					"fieldname": "sr_scanned_barcode",
					"label": "Scanned Compliance Barcode",
					"fieldtype": "Data",
					"insert_after": "sr_compliance_expiry_date",
					"read_only": 1,
					"print_hide": 1,
				},
			]
		}
	)


def _configure_fields():
	if frappe.db.exists("DocType", SALES_INVOICE_ITEM):
		ensure_field_after(SALES_INVOICE_ITEM, "sr_compliance_batch", "item_code")
		ensure_field_after(SALES_INVOICE_ITEM, "sr_compliance_batch_no", "sr_compliance_batch")
		ensure_field_after(SALES_INVOICE_ITEM, "sr_compliance_mfg_date", "sr_compliance_batch_no")
		ensure_field_after(SALES_INVOICE_ITEM, "sr_compliance_expiry_date", "sr_compliance_mfg_date")
		ensure_field_after(SALES_INVOICE_ITEM, "sr_scanned_barcode", "sr_compliance_expiry_date")

	meta = frappe.get_meta(SALES_INVOICE_ITEM)
	if meta.has_field("batch_no"):
		# Legacy rows remain readable and printable. The client script reveals this
		# field only when the scanned barcode resolves to an ERPNext Batch.
		upsert_property_setter(SALES_INVOICE_ITEM, "batch_no", "hidden", "1", "Check")
		upsert_property_setter(SALES_INVOICE_ITEM, "batch_no", "in_list_view", "0", "Check")

