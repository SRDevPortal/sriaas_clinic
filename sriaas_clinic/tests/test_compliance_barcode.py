from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from sriaas_clinic.api import compliance_barcode


class TestComplianceBarcode(FrappeTestCase):
	def test_update_stock_invoice_posts_item_stock_without_bundle(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.selling.doctype.customer.test_customer import get_customer_dict
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.utils import get_stock_balance

		customer_name = frappe.db.exists("Customer", "_Test Customer")
		if not customer_name:
			customer_name = frappe.get_doc(get_customer_dict("_Test Customer")).insert(
				ignore_permissions=True
			).name
		item_code = "_Test SR Compliance Item"
		warehouse = "_Test Warehouse - _TC"
		item = make_item(
			item_code,
			properties={
				"is_stock_item": 1,
				"has_batch_no": 0,
				"has_serial_no": 0,
				"sr_requires_compliance_batch": 1,
				"gst_hsn_code": "30049099",
			},
		)
		item.reload()
		self.assertFalse(item.has_batch_no)
		self.assertFalse(item.has_serial_no)

		barcode = "SR-COMPLIANCE-TEST-001"
		compliance = frappe.get_doc(
			{
				"doctype": "SR Compliance Batch",
				"barcode": barcode,
				"item": item_code,
				"compliance_batch_no": "LOT-TEST-001",
				"manufacturing_date": "2026-01-01",
				"expiry_date": "2027-12-31",
				"active": 1,
				"company": "_Test Company",
			}
		).insert()

		make_stock_entry(
			item_code=item_code,
			to_warehouse=warehouse,
			qty=10,
			rate=25,
			company="_Test Company",
		)
		stock_before = get_stock_balance(item_code, warehouse)
		bundles_before = frappe.db.count("Serial and Batch Bundle", {"item_code": item_code})

		invoice = create_sales_invoice(
			item=item_code,
			customer=customer_name,
			warehouse=warehouse,
			qty=2,
			rate=50,
			update_stock=1,
			do_not_save=True,
		)
		with patch.object(
			compliance_barcode,
			"get_compliance_config",
			return_value=frappe._dict(
				mode=compliance_barcode.MODE_HYBRID,
				expiry_policy="Block",
				stock_policy="Block",
			),
		):
			resolved = compliance_barcode.resolve_barcode(
				barcode,
				warehouse,
				company="_Test Company",
				context_doctype="Sales Invoice",
				doc=invoice.as_dict(),
			)
		self.assertEqual(resolved["tracking_mode"], "compliance")
		self.assertEqual(resolved["item_code"], item_code)
		self.assertEqual(resolved["compliance_batch_no"], "LOT-TEST-001")
		self.assertIsNone(resolved["batch_no"])

		row = invoice.items[0]
		row.sr_compliance_batch = resolved["compliance_batch"]
		row.sr_compliance_batch_no = resolved["compliance_batch_no"]
		row.sr_compliance_mfg_date = resolved["manufacturing_date"]
		row.sr_compliance_expiry_date = resolved["expiry_date"]
		row.sr_scanned_barcode = resolved["scanned_barcode"]
		row.batch_no = None
		row.serial_no = None
		row.serial_and_batch_bundle = None
		row.use_serial_batch_fields = 0
		invoice.insert()
		invoice.submit()
		invoice.reload()

		self.assertTrue(invoice.update_stock)
		self.assertEqual(get_stock_balance(item_code, warehouse), stock_before - 2)
		self.assertEqual(
			frappe.db.count("Serial and Batch Bundle", {"item_code": item_code}),
			bundles_before,
		)
		self.assertFalse(invoice.items[0].batch_no)
		self.assertFalse(invoice.items[0].serial_and_batch_bundle)
		self.assertEqual(invoice.items[0].sr_compliance_batch_no, "LOT-TEST-001")
		for print_format in ("Sales Invoice New", "Sales Invoice New2", "Kit Billing Invoice"):
			rendered = frappe.get_print("Sales Invoice", invoice.name, print_format)
			self.assertIn("LOT-TEST-001", rendered, msg=print_format)

		return_invoice = make_return_doc("Sales Invoice", invoice.name)
		return_invoice.submit()
		return_invoice.reload()
		self.assertTrue(return_invoice.update_stock)
		self.assertEqual(get_stock_balance(item_code, warehouse), stock_before)
		self.assertEqual(return_invoice.items[0].sr_compliance_batch, compliance.name)
		self.assertEqual(return_invoice.items[0].sr_compliance_batch_no, "LOT-TEST-001")
		self.assertEqual(return_invoice.items[0].sr_scanned_barcode, barcode)
		self.assertFalse(return_invoice.items[0].batch_no)
		self.assertFalse(return_invoice.items[0].serial_and_batch_bundle)
		self.assertEqual(
			frappe.db.count("Serial and Batch Bundle", {"item_code": item_code}),
			bundles_before,
		)

		return_invoice.cancel()
		self.assertEqual(get_stock_balance(item_code, warehouse), stock_before - 2)
		invoice.cancel()
		self.assertEqual(get_stock_balance(item_code, warehouse), stock_before)
		self.assertEqual(
			frappe.db.count("Serial and Batch Bundle", {"item_code": item_code}),
			bundles_before,
		)

	def test_config_falls_back_to_hybrid_without_batch_stock_guard(self):
		with patch.object(compliance_barcode.frappe.db, "exists", return_value=False):
			config = compliance_barcode.get_compliance_config()

		self.assertEqual(config.mode, compliance_barcode.MODE_HYBRID)
		self.assertEqual(config.expiry_policy, "Block")
		self.assertEqual(config.stock_policy, "Block")

	def test_compliance_response_uses_total_item_warehouse_stock(self):
		record = frappe._dict(
			name="BARCODE-001",
			barcode="BARCODE-001",
			item="ITEM-NEW",
			compliance_batch_no="LOT-001",
			manufacturing_date="2026-01-01",
			expiry_date="2027-01-01",
			active=1,
			company=None,
		)
		item = frappe._dict(
			name="ITEM-NEW",
			item_name="New Item",
			description="",
			is_stock_item=1,
			has_batch_no=0,
			stock_uom="Nos",
		)
		config = frappe._dict(expiry_policy="Block", stock_policy="Block")
		doc = frappe._dict(doctype="Sales Invoice", posting_date="2026-08-10")

		with (
			patch.object(compliance_barcode, "_get_item", return_value=item),
			patch.object(compliance_barcode, "_get_available_qty", return_value=12) as get_qty,
			patch.object(
				compliance_barcode,
				"_get_sales_item_details",
				return_value={"uom": "Nos", "stock_uom": "Nos", "conversion_factor": 1, "rate": 25},
			),
		):
			result = compliance_barcode._compliance_response(
				record, "Packaging Warehouse - SR", doc, 1, config
			)

		get_qty.assert_called_once_with("ITEM-NEW", "Packaging Warehouse - SR")
		self.assertEqual(result["tracking_mode"], "compliance")
		self.assertEqual(result["compliance_batch_no"], "LOT-001")
		self.assertIsNone(result["batch_no"])
		self.assertEqual(result["available_qty"], 12)

	def test_compliance_response_rejects_erpnext_batch_item(self):
		record = frappe._dict(
			name="BARCODE-001",
			barcode="BARCODE-001",
			item="ITEM-OLD",
			compliance_batch_no="LOT-001",
			active=1,
			company=None,
			expiry_date=None,
		)
		item = frappe._dict(name="ITEM-OLD", is_stock_item=1, has_batch_no=1)

		with patch.object(compliance_barcode, "_get_item", return_value=item):
			with self.assertRaises(frappe.ValidationError):
				compliance_barcode._compliance_response(
					record,
					"Packaging Warehouse - SR",
					frappe._dict(doctype="Sales Invoice"),
					1,
					frappe._dict(expiry_policy="Block", stock_policy="Block"),
				)

	def test_compliance_response_rejects_serialized_item(self):
		record = frappe._dict(
			name="BARCODE-001",
			barcode="BARCODE-001",
			item="ITEM-SERIAL",
			compliance_batch_no="LOT-001",
			active=1,
			company=None,
			expiry_date=None,
		)
		item = frappe._dict(
			name="ITEM-SERIAL",
			is_stock_item=1,
			has_batch_no=0,
			has_serial_no=1,
		)

		with patch.object(compliance_barcode, "_get_item", return_value=item):
			with self.assertRaises(frappe.ValidationError):
				compliance_barcode._compliance_response(
					record,
					"Packaging Warehouse - SR",
					frappe._dict(doctype="Sales Invoice"),
					1,
					frappe._dict(expiry_policy="Block", stock_policy="Block"),
				)

	def test_expired_compliance_batch_can_warn_without_blocking(self):
		record = frappe._dict(
			name="BARCODE-001",
			barcode="BARCODE-001",
			item="ITEM-NEW",
			compliance_batch_no="LOT-001",
			active=1,
			company=None,
			manufacturing_date="2025-01-01",
			expiry_date="2025-12-31",
		)
		item = frappe._dict(
			name="ITEM-NEW",
			item_name="New Item",
			description="",
			is_stock_item=1,
			has_batch_no=0,
			stock_uom="Nos",
		)

		with (
			patch.object(compliance_barcode, "_get_item", return_value=item),
			patch.object(compliance_barcode, "_get_available_qty", return_value=12),
			patch.object(compliance_barcode, "_get_sales_item_details", return_value={}),
		):
			result = compliance_barcode._compliance_response(
				record,
				"Packaging Warehouse - SR",
				frappe._dict(doctype="Sales Invoice", posting_date="2026-08-10"),
				1,
				frappe._dict(expiry_policy="Warn", stock_policy="Block"),
			)

		self.assertEqual(len(result["warnings"]), 1)

	def test_resolver_prefers_compliance_record_in_hybrid_mode(self):
		record = frappe._dict(name="BARCODE-001")
		expected = {"tracking_mode": "compliance"}

		with (
			patch.object(compliance_barcode, "_ensure_scan_permission"),
			patch.object(compliance_barcode, "_validate_warehouse"),
			patch.object(
				compliance_barcode,
				"get_compliance_config",
				return_value=frappe._dict(mode=compliance_barcode.MODE_HYBRID),
			),
			patch.object(compliance_barcode, "_get_compliance_record", return_value=record),
			patch.object(compliance_barcode, "_compliance_response", return_value=expected),
			patch.object(compliance_barcode, "_get_legacy_batch") as get_legacy,
		):
			result = compliance_barcode.resolve_barcode(
				"BARCODE-001", "Packaging Warehouse - SR", doc={"doctype": "Sales Invoice"}
			)

		self.assertEqual(result, expected)
		get_legacy.assert_not_called()

	def test_resolver_uses_legacy_batch_when_mode_is_off(self):
		batch = frappe._dict(name="BATCH-001")
		expected = {"tracking_mode": "erpnext_batch"}

		with (
			patch.object(compliance_barcode, "_ensure_scan_permission"),
			patch.object(compliance_barcode, "_validate_warehouse"),
			patch.object(
				compliance_barcode,
				"get_compliance_config",
				return_value=frappe._dict(mode=compliance_barcode.MODE_OFF),
			),
			patch.object(compliance_barcode, "_get_compliance_record") as get_compliance,
			patch.object(compliance_barcode, "_get_legacy_batch", return_value=batch),
			patch.object(compliance_barcode, "_legacy_response", return_value=expected),
		):
			result = compliance_barcode.resolve_barcode(
				"BARCODE-001", "Packaging Warehouse - SR", doc={"doctype": "Sales Invoice"}
			)

		self.assertEqual(result, expected)
		get_compliance.assert_not_called()

	def test_invoice_validation_accepts_matching_unbatched_snapshot(self):
		row = frappe._dict(
			idx=1,
			item_code="ITEM-NEW",
			sr_compliance_batch="BARCODE-001",
			sr_compliance_batch_no="LOT-001",
			sr_compliance_mfg_date="2026-01-01",
			sr_compliance_expiry_date="2027-01-01",
			sr_scanned_barcode="BARCODE-001",
			batch_no=None,
			serial_and_batch_bundle=None,
			use_serial_batch_fields=1,
		)
		record = frappe._dict(
			name="BARCODE-001",
			item="ITEM-NEW",
			barcode="BARCODE-001",
			compliance_batch_no="LOT-001",
			manufacturing_date="2026-01-01",
			expiry_date="2027-01-01",
			active=1,
		)
		doc = frappe._dict(items=[row], is_return=0, posting_date="2026-08-10")

		with (
			patch.object(
				compliance_barcode.frappe,
				"get_meta",
				return_value=frappe._dict(
					has_field=lambda fieldname: True,
					get_label=lambda fieldname: fieldname,
				),
			),
			patch.object(
				compliance_barcode,
				"get_compliance_config",
				return_value=frappe._dict(mode=compliance_barcode.MODE_HYBRID),
			),
			patch.object(
				compliance_barcode,
				"_get_item_compliance_flags",
				return_value={
					"ITEM-NEW": frappe._dict(
						name="ITEM-NEW", has_batch_no=0, sr_requires_compliance_batch=1
					)
				},
			),
			patch.object(
				compliance_barcode,
				"_get_compliance_records",
				return_value={"BARCODE-001": record},
			),
		):
			compliance_barcode.validate_sales_invoice_compliance(doc)

		self.assertEqual(row.use_serial_batch_fields, 0)

	def test_invoice_validation_rejects_standard_batch_on_compliance_item(self):
		row = frappe._dict(
			idx=1,
			item_code="ITEM-NEW",
			sr_compliance_batch="BARCODE-001",
			sr_compliance_batch_no="LOT-001",
			sr_compliance_mfg_date=None,
			sr_compliance_expiry_date=None,
			sr_scanned_barcode="BARCODE-001",
			batch_no="ERP-BATCH-001",
			serial_and_batch_bundle=None,
		)
		record = frappe._dict(
			name="BARCODE-001",
			item="ITEM-NEW",
			barcode="BARCODE-001",
			compliance_batch_no="LOT-001",
			manufacturing_date=None,
			expiry_date=None,
			active=1,
		)

		with (
			patch.object(
				compliance_barcode.frappe,
				"get_meta",
				return_value=frappe._dict(
					has_field=lambda fieldname: True,
					get_label=lambda fieldname: fieldname,
				),
			),
			patch.object(
				compliance_barcode,
				"get_compliance_config",
				return_value=frappe._dict(mode=compliance_barcode.MODE_HYBRID),
			),
			patch.object(
				compliance_barcode,
				"_get_item_compliance_flags",
				return_value={"ITEM-NEW": frappe._dict(has_batch_no=0, sr_requires_compliance_batch=1)},
			),
			patch.object(
				compliance_barcode,
				"_get_compliance_records",
				return_value={"BARCODE-001": record},
			),
		):
			with self.assertRaises(frappe.ValidationError):
				compliance_barcode.validate_sales_invoice_compliance(
					frappe._dict(items=[row], is_return=0)
				)
