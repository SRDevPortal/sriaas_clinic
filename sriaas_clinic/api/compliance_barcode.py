from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate


MODE_OFF = "Off"
MODE_HYBRID = "Hybrid Transition"
MODE_COMPLIANCE = "SR Barcode Compliance"
SETTINGS_DOCTYPE = "Batch Stock Guard Settings"


def get_compliance_config() -> frappe._dict:
	"""Return transition settings without creating a hard app dependency."""
	defaults = frappe._dict(
		mode=MODE_HYBRID,
		expiry_policy="Block",
		stock_policy="Block",
	)
	if not frappe.db.exists("DocType", SETTINGS_DOCTYPE):
		return defaults

	meta = frappe.get_meta(SETTINGS_DOCTYPE)
	if not meta.has_field("sr_barcode_compliance_mode"):
		return defaults

	# get_single_value is safe for missing singleton rows and preserves defaults.
	mode = frappe.db.get_single_value(SETTINGS_DOCTYPE, "sr_barcode_compliance_mode") or MODE_OFF
	expiry_policy = (
		frappe.db.get_single_value(SETTINGS_DOCTYPE, "sr_compliance_expiry_policy") or "Block"
	)
	stock_policy = (
		frappe.db.get_single_value(SETTINGS_DOCTYPE, "sr_compliance_stock_policy") or "Block"
	)
	return frappe._dict(
		mode=mode,
		expiry_policy=expiry_policy,
		stock_policy=stock_policy,
	)


def _ensure_scan_permission(context_doctype: str):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please sign in before scanning a barcode."), frappe.PermissionError)

	doctype = context_doctype if context_doctype in {"Sales Invoice", "Stock Entry"} else "Sales Invoice"
	if not (
		frappe.has_permission(doctype, ptype="create")
		or frappe.has_permission(doctype, ptype="write")
	):
		frappe.throw(_("You are not allowed to create or edit {0}.").format(doctype), frappe.PermissionError)


def _get_compliance_record(barcode: str) -> frappe._dict:
	if not frappe.db.exists("DocType", "SR Compliance Batch"):
		return frappe._dict()

	rows = frappe.get_all(
		"SR Compliance Batch",
		filters={"barcode": barcode},
		fields=[
			"name",
			"barcode",
			"item",
			"compliance_batch_no",
			"manufacturing_date",
			"expiry_date",
			"active",
			"company",
		],
		limit_page_length=1,
	)
	return frappe._dict(rows[0]) if rows else frappe._dict()


def _legacy_batch_fields() -> list[str]:
	fields = ["name", "item", "expiry_date"]
	if frappe.get_meta("Batch").has_field("sr_barcode"):
		fields.append("sr_barcode")
	return fields


def _get_legacy_batch(barcode: str) -> frappe._dict:
	if not frappe.db.exists("DocType", "Batch") or not frappe.get_meta("Batch").has_field("sr_barcode"):
		return frappe._dict()
	rows = frappe.get_all(
		"Batch",
		filters={"sr_barcode": barcode, "disabled": 0},
		fields=_legacy_batch_fields(),
		limit_page_length=1,
	)
	return frappe._dict(rows[0]) if rows else frappe._dict()


def _get_item(item_code: str) -> frappe._dict:
	item = frappe.db.get_value(
		"Item",
		item_code,
		[
			"name",
			"item_name",
			"description",
			"disabled",
			"is_stock_item",
			"has_batch_no",
			"has_serial_no",
			"stock_uom",
		],
		as_dict=True,
	)
	if not item:
		frappe.throw(_("Item {0} does not exist.").format(frappe.bold(item_code)))
	if item.disabled:
		frappe.throw(_("Item {0} is disabled.").format(frappe.bold(item_code)))
	return frappe._dict(item)


def _validate_warehouse(warehouse: str, company: str | None) -> str:
	warehouse = (warehouse or "").strip()
	if not warehouse:
		frappe.throw(_("Select a Warehouse before scanning a barcode."))

	warehouse_company = frappe.db.get_value("Warehouse", warehouse, "company")
	if not warehouse_company:
		frappe.throw(_("Warehouse {0} does not exist.").format(frappe.bold(warehouse)))
	if company and warehouse_company != company:
		frappe.throw(
			_("Warehouse {0} belongs to company {1}, not {2}.").format(
				frappe.bold(warehouse), frappe.bold(warehouse_company), frappe.bold(company)
			)
		)
	return warehouse_company


def _get_available_qty(item_code: str, warehouse: str) -> float:
	return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"))


def _policy_result(policy: str, message: str, warnings: list[str]):
	if policy == "Block":
		frappe.throw(message)
	if policy == "Warn":
		warnings.append(message)


def _get_sales_item_details(item: frappe._dict, warehouse: str, doc: frappe._dict, qty: float) -> dict:
	if doc.get("doctype") != "Sales Invoice":
		return {
			"uom": item.stock_uom,
			"stock_uom": item.stock_uom,
			"conversion_factor": 1,
			"price_list_rate": None,
			"rate": None,
		}

	from erpnext.stock.get_item_details import get_item_details

	company = doc.get("company")
	company_currency = frappe.get_cached_value("Company", company, "default_currency") if company else None
	args = frappe._dict(
		item_code=item.name,
		warehouse=warehouse,
		set_warehouse=warehouse,
		customer=doc.get("customer"),
		company=company,
		currency=doc.get("currency") or company_currency,
		conversion_rate=flt(doc.get("conversion_rate")) or 1,
		selling_price_list=doc.get("selling_price_list"),
		price_list_currency=doc.get("price_list_currency") or doc.get("currency") or company_currency,
		plc_conversion_rate=flt(doc.get("plc_conversion_rate")) or 1,
		doctype="Sales Invoice",
		name=doc.get("name"),
		transaction_date=doc.get("posting_date") or nowdate(),
		posting_date=doc.get("posting_date") or nowdate(),
		qty=qty,
		uom=item.stock_uom,
		stock_uom=item.stock_uom,
		is_pos=cint(doc.get("is_pos")),
		ignore_pricing_rule=cint(doc.get("ignore_pricing_rule")),
	)
	details = frappe._dict(get_item_details(args, doc=doc))
	return {
		"uom": details.get("uom") or item.stock_uom,
		"stock_uom": details.get("stock_uom") or item.stock_uom,
		"conversion_factor": flt(details.get("conversion_factor")) or 1,
		"price_list_rate": details.get("price_list_rate"),
		"rate": details.get("rate"),
		"item_tax_template": details.get("item_tax_template"),
	}


def _parse_doc(doc, *, company=None, context_doctype="Sales Invoice") -> frappe._dict:
	if isinstance(doc, str):
		doc = frappe.parse_json(doc)
	doc = frappe._dict(doc or {})
	doc.setdefault("doctype", context_doctype)
	if company:
		doc["company"] = company
	return doc


def _compliance_response(
	record: frappe._dict,
	warehouse: str,
	doc: frappe._dict,
	qty: float,
	config: frappe._dict,
) -> dict:
	if not record.active:
		frappe.throw(_("Compliance barcode {0} is disabled.").format(frappe.bold(record.barcode)))
	if record.company and doc.get("company") and record.company != doc.company:
		frappe.throw(
			_("Compliance barcode {0} belongs to company {1}.").format(
				frappe.bold(record.barcode), frappe.bold(record.company)
			)
		)

	item = _get_item(record.item)
	if not item.is_stock_item:
		frappe.throw(_("Compliance barcode Item {0} is not a stock Item.").format(frappe.bold(item.name)))
	if item.has_batch_no:
		frappe.throw(
			_("Item {0} still uses ERPNext Batch inventory. Use a replacement Item with Has Batch No disabled.").format(
				frappe.bold(item.name)
			)
		)
	if item.has_serial_no:
		frappe.throw(
			_("Item {0} still uses ERPNext Serial No inventory. Use a replacement Item with serial tracking disabled.").format(
				frappe.bold(item.name)
			)
		)

	warnings = []
	posting_date = getdate(doc.get("posting_date") or nowdate())
	if record.expiry_date and getdate(record.expiry_date) < posting_date:
		_policy_result(
			config.expiry_policy,
			_("Compliance batch {0} expired on {1}.").format(
				frappe.bold(record.compliance_batch_no), frappe.format(record.expiry_date, {"fieldtype": "Date"})
			),
			warnings,
		)

	available_qty = _get_available_qty(item.name, warehouse)
	if available_qty < qty:
		_policy_result(
			config.stock_policy,
			_("Only {0} of Item {1} is available in Warehouse {2}. This is total Item stock, not batch stock.").format(
				available_qty, frappe.bold(item.name), frappe.bold(warehouse)
			),
			warnings,
		)

	return {
		"tracking_mode": "compliance",
		"item_code": item.name,
		"item_name": item.item_name,
		"description": item.description,
		"compliance_batch": record.name,
		"compliance_batch_no": record.compliance_batch_no,
		"manufacturing_date": record.manufacturing_date,
		"expiry_date": record.expiry_date,
		"scanned_barcode": record.barcode,
		"batch_no": None,
		"available_qty": available_qty,
		"stock_policy": config.stock_policy,
		"warnings": warnings,
		**_get_sales_item_details(item, warehouse, doc, qty),
	}


def _legacy_response(batch: frappe._dict, warehouse: str, doc: frappe._dict, qty: float) -> dict:
	from erpnext.stock.doctype.batch.batch import get_batch_qty

	item = _get_item(batch.item)
	available_qty = flt(get_batch_qty(batch.name, warehouse))
	if available_qty < qty:
		frappe.throw(
			_("Only {0} is available in ERPNext Batch {1} at Warehouse {2}.").format(
				available_qty, frappe.bold(batch.name), frappe.bold(warehouse)
			)
		)
	return {
		"tracking_mode": "erpnext_batch",
		"item_code": item.name,
		"item_name": item.item_name,
		"description": item.description,
		"batch_no": batch.name,
		"compliance_batch": None,
		"compliance_batch_no": None,
		"manufacturing_date": None,
		"expiry_date": batch.expiry_date,
		"scanned_barcode": batch.get("sr_barcode"),
		"available_qty": available_qty,
		"stock_policy": "Block",
		"warnings": [],
		**_get_sales_item_details(item, warehouse, doc, qty),
	}


@frappe.whitelist()
def resolve_barcode(
	barcode: str,
	warehouse: str,
	doc=None,
	company: str | None = None,
	context_doctype: str = "Sales Invoice",
	qty: float | str = 1,
):
	"""Resolve either a compliance-only barcode or a legacy ERPNext Batch barcode."""
	barcode = (barcode or "").strip()
	if not barcode:
		frappe.throw(_("Scan or enter a barcode."))

	_ensure_scan_permission(context_doctype)
	doc = _parse_doc(doc, company=company, context_doctype=context_doctype)
	_validate_warehouse(warehouse, doc.get("company"))
	qty = abs(flt(qty)) or 1
	config = get_compliance_config()

	if config.mode in {MODE_HYBRID, MODE_COMPLIANCE}:
		if record := _get_compliance_record(barcode):
			return _compliance_response(record, warehouse, doc, qty, config)

	if config.mode in {MODE_OFF, MODE_HYBRID}:
		if batch := _get_legacy_batch(barcode):
			return _legacy_response(batch, warehouse, doc, qty)

	if config.mode == MODE_COMPLIANCE:
		frappe.throw(_("No active SR Compliance Batch found for barcode {0}.").format(frappe.bold(barcode)))
	frappe.throw(_("No barcode mapping found for {0}.").format(frappe.bold(barcode)))


def _copy_return_snapshots(doc):
	if not doc.get("is_return"):
		return

	for row in doc.get("items") or []:
		source_row = row.get("sales_invoice_item")
		if not source_row:
			continue
		values = frappe.db.get_value(
			"Sales Invoice Item",
			source_row,
			[
				"sr_compliance_batch",
				"sr_compliance_batch_no",
				"sr_compliance_mfg_date",
				"sr_compliance_expiry_date",
				"sr_scanned_barcode",
			],
			as_dict=True,
		)
		for fieldname, value in (values or {}).items():
			if not row.get(fieldname):
				row.set(fieldname, value)


def _get_item_compliance_flags(item_codes: set[str]) -> dict[str, frappe._dict]:
	if not item_codes:
		return {}
	fields = ["name", "has_batch_no", "has_serial_no"]
	if frappe.get_meta("Item").has_field("sr_requires_compliance_batch"):
		fields.append("sr_requires_compliance_batch")
	rows = frappe.get_all("Item", filters={"name": ("in", list(item_codes))}, fields=fields)
	return {row.name: frappe._dict(row) for row in rows}


def _get_compliance_records(names: set[str]) -> dict[str, frappe._dict]:
	if not names:
		return {}
	rows = frappe.get_all(
		"SR Compliance Batch",
		filters={"name": ("in", list(names))},
		fields=[
			"name",
			"item",
			"barcode",
			"compliance_batch_no",
			"manufacturing_date",
			"expiry_date",
			"active",
			"company",
		],
	)
	return {row.name: frappe._dict(row) for row in rows}


def prepare_sales_invoice_compliance(doc, method=None):
	"""Populate return/snapshot fields without changing stock or standard Batch fields."""
	if not frappe.get_meta("Sales Invoice Item").has_field("sr_compliance_batch"):
		return
	_copy_return_snapshots(doc)

	names = {row.get("sr_compliance_batch") for row in doc.get("items") or [] if row.get("sr_compliance_batch")}
	records = _get_compliance_records(names)
	for row in doc.get("items") or []:
		name = row.get("sr_compliance_batch")
		if not name or name not in records:
			continue
		record = records[name]
		for fieldname, value in {
			"sr_compliance_batch_no": record.compliance_batch_no,
			"sr_compliance_mfg_date": record.manufacturing_date,
			"sr_compliance_expiry_date": record.expiry_date,
			"sr_scanned_barcode": record.barcode,
		}.items():
			if not row.get(fieldname):
				row.set(fieldname, value)


def validate_sales_invoice_compliance(doc, method=None):
	if not frappe.get_meta("Sales Invoice Item").has_field("sr_compliance_batch"):
		return
	config = get_compliance_config()
	if config.mode == MODE_OFF and not any(row.get("sr_compliance_batch") for row in doc.get("items") or []):
		return

	item_codes = {row.get("item_code") for row in doc.get("items") or [] if row.get("item_code")}
	items = _get_item_compliance_flags(item_codes)
	names = {row.get("sr_compliance_batch") for row in doc.get("items") or [] if row.get("sr_compliance_batch")}
	records = _get_compliance_records(names)

	problems = defaultdict(list)
	for row in doc.get("items") or []:
		item = items.get(row.get("item_code"), frappe._dict())
		requires = cint(item.get("sr_requires_compliance_batch"))
		compliance_name = row.get("sr_compliance_batch")
		if requires and not compliance_name:
			problems[row.idx].append(_("Compliance Batch is required."))
		if not compliance_name:
			continue

		record = records.get(compliance_name)
		if not record:
			problems[row.idx].append(_("Compliance Batch {0} does not exist.").format(compliance_name))
			continue
		if record.item != row.get("item_code"):
			problems[row.idx].append(_("Compliance Batch belongs to Item {0}.").format(record.item))
		if record.company and doc.get("company") and record.company != doc.get("company"):
			problems[row.idx].append(_("Compliance Batch belongs to Company {0}.").format(record.company))
		if not record.active and not doc.get("is_return"):
			problems[row.idx].append(_("Compliance Batch is disabled."))
		if (
			record.expiry_date
			and getdate(record.expiry_date) < getdate(doc.get("posting_date") or nowdate())
			and not doc.get("is_return")
		):
			message = _("Compliance Batch expired on {0}.").format(
				frappe.format(record.expiry_date, {"fieldtype": "Date"})
			)
			if config.expiry_policy == "Block":
				problems[row.idx].append(message)
			elif config.expiry_policy == "Warn":
				frappe.msgprint(message, indicator="orange", alert=True)

		expected = {
			"sr_compliance_batch_no": record.compliance_batch_no,
			"sr_compliance_mfg_date": record.manufacturing_date,
			"sr_compliance_expiry_date": record.expiry_date,
			"sr_scanned_barcode": record.barcode,
		}
		for fieldname, value in expected.items():
			actual = row.get(fieldname)
			if fieldname in {"sr_compliance_mfg_date", "sr_compliance_expiry_date"}:
				actual = getdate(actual) if actual else None
				value = getdate(value) if value else None
			if actual != value:
				problems[row.idx].append(_("{0} no longer matches the selected Compliance Batch; rescan the barcode.").format(
					frappe.get_meta("Sales Invoice Item").get_label(fieldname)
				))

		if not item.get("has_batch_no"):
			if item.get("has_serial_no"):
				problems[row.idx].append(_("Compliance-only Item must have serial tracking disabled."))
			if row.get("batch_no"):
				problems[row.idx].append(_("ERPNext Batch No must remain empty for a compliance-only Item."))
			if row.get("serial_no"):
				problems[row.idx].append(_("ERPNext Serial No must remain empty for a compliance-only Item."))
			if row.get("serial_and_batch_bundle"):
				problems[row.idx].append(_("Serial and Batch Bundle must remain empty for a compliance-only Item."))
			# Stock Settings can enable this field globally during validation. Clear it
			# again before stock posting so a compliance-only row stays out of ERPNext's
			# serial/batch bundle workflow.
			row.use_serial_batch_fields = 0

	if problems:
		lines = []
		for idx, messages in problems.items():
			lines.append(_("Row {0}: {1}").format(idx, " ".join(messages)))
		frappe.throw("<br>".join(lines), title=_("SR Barcode Compliance Validation"))


def _ensure_migration_permission():
	if frappe.session.user == "Administrator":
		return
	if not {"System Manager", "Stock Manager"}.intersection(set(frappe.get_roles())):
		frappe.throw(_("Only System Manager or Stock Manager can use compliance migration tools."), frappe.PermissionError)


def _validate_replacement_item(legacy_item: str, replacement_item: str):
	replacement = _get_item(replacement_item)
	if replacement.has_batch_no:
		frappe.throw(_("Replacement Item must have Has Batch No disabled."))
	if replacement.has_serial_no:
		frappe.throw(_("Replacement Item must have serial tracking disabled."))
	if not replacement.is_stock_item:
		frappe.throw(_("Replacement Item must remain a stock Item."))
	if frappe.get_meta("Item").has_field("sr_legacy_item"):
		linked_legacy = frappe.db.get_value("Item", replacement.name, "sr_legacy_item")
		if linked_legacy != legacy_item:
			frappe.throw(
				_("Replacement Item {0} must link to legacy Item {1}.").format(
					frappe.bold(replacement.name), frappe.bold(legacy_item)
				)
			)
	return replacement


def _copy_item_prices(legacy_item: str, replacement_item: str) -> dict:
	"""Copy non-batch prices without converting batch-specific commercial rules."""
	fields = [
		"price_list",
		"uom",
		"packing_unit",
		"valid_from",
		"valid_upto",
		"customer",
		"supplier",
		"batch_no",
	]

	def price_key(doc):
		return tuple(doc.get(fieldname) or None for fieldname in fields)

	existing_keys = {
		price_key(row)
		for row in frappe.get_all("Item Price", filters={"item_code": replacement_item}, fields=fields)
	}
	created = []
	skipped = []
	for row in frappe.get_all(
		"Item Price", filters={"item_code": legacy_item}, fields=["name", *fields], order_by="creation asc"
	):
		if row.batch_no:
			skipped.append({"name": row.name, "reason": "batch_specific_price_requires_review"})
			continue
		if price_key(row) in existing_keys:
			skipped.append({"name": row.name, "reason": "already_copied"})
			continue

		price = frappe.copy_doc(frappe.get_doc("Item Price", row.name))
		price.item_code = replacement_item
		price.batch_no = None
		price.insert(ignore_permissions=True)
		created.append(price.name)
		existing_keys.add(price_key(price))

	return {"created": created, "skipped": skipped}


@frappe.whitelist()
def create_compliance_replacement_item(
	legacy_item: str,
	replacement_item: str | None = None,
	confirm: bool | str = False,
):
	"""Create an unbatched replacement Item without making any stock or valuation entry."""
	_ensure_migration_permission()
	if str(confirm).lower() not in {"1", "true", "yes"}:
		frappe.throw(_("Set confirm=1 after reviewing preview_item_migration."))

	legacy = _get_item(legacy_item)
	if not legacy.is_stock_item or not legacy.has_batch_no:
		frappe.throw(_("Legacy Item must be a batch-enabled stock Item."))
	if legacy.has_serial_no:
		frappe.throw(_("Serialized Items require a separate migration design."))

	replacement_item = (replacement_item or f"{legacy.name}-COMPLIANCE").strip()
	if not replacement_item or replacement_item == legacy.name:
		frappe.throw(_("Use a distinct replacement Item Code."))

	item_created = False
	if frappe.db.exists("Item", replacement_item):
		replacement = _validate_replacement_item(legacy.name, replacement_item)
	else:
		source = frappe.get_doc("Item", legacy.name)
		if source.get("variant_of") or source.get("has_variants"):
			frappe.throw(_("Variant Items require a separately reviewed replacement Item."))

		replacement = frappe.copy_doc(source)
		replacement.item_code = replacement_item
		replacement.item_name = _("{0} (Compliance)").format(source.item_name or source.name)
		replacement.is_stock_item = 1
		replacement.has_batch_no = 0
		replacement.create_new_batch = 0
		replacement.batch_number_series = None
		replacement.has_expiry_date = 0
		replacement.shelf_life_in_days = 0
		replacement.retain_sample = 0
		replacement.has_serial_no = 0
		replacement.serial_no_series = None
		replacement.opening_stock = 0
		replacement.valuation_rate = 0
		# Prevent after_insert from creating a second price. Existing Item Price
		# records are copied explicitly below.
		replacement.standard_rate = 0
		replacement.set("barcodes", [])
		replacement.sr_requires_compliance_batch = 1
		replacement.sr_legacy_item = legacy.name
		replacement.insert(ignore_permissions=True)
		item_created = True

	replacement = _validate_replacement_item(legacy.name, replacement.name)
	prices = _copy_item_prices(legacy.name, replacement.name)
	batches = import_legacy_batches(legacy.name, replacement.name, confirm=True)
	return {
		"legacy_item": legacy.name,
		"replacement_item": replacement.name,
		"item_created": item_created,
		"item_prices": prices,
		"compliance_batches": batches,
		"stock_or_valuation_writes": False,
	}


@frappe.whitelist()
def preview_item_migration(legacy_item: str, replacement_item: str | None = None):
	"""Read-only pilot snapshot. It never changes stock, valuation, Batch, or bundles."""
	_ensure_migration_permission()
	legacy = _get_item(legacy_item)
	replacement = _get_item(replacement_item) if replacement_item else None
	if replacement and replacement.has_batch_no:
		frappe.throw(_("Replacement Item must have Has Batch No disabled."))
	if replacement and replacement.has_serial_no:
		frappe.throw(_("Replacement Item must have serial tracking disabled."))

	batch_fields = ["name", "item", "manufacturing_date", "expiry_date", "disabled"]
	if frappe.get_meta("Batch").has_field("sr_barcode"):
		batch_fields.append("sr_barcode")
	batches = frappe.get_all("Batch", filters={"item": legacy.name}, fields=batch_fields, order_by="creation asc")
	bins = frappe.get_all(
		"Bin",
		filters={"item_code": legacy.name},
		fields=["warehouse", "actual_qty", "valuation_rate", "stock_value", "projected_qty"],
		order_by="warehouse asc",
	)

	open_documents = {}
	for child_doctype in ("Sales Order Item", "Delivery Note Item", "Purchase Order Item", "Purchase Receipt Item", "Sales Invoice Item"):
		if not frappe.db.exists("DocType", child_doctype):
			continue
		open_documents[child_doctype] = frappe.db.count(
			child_doctype,
			{"item_code": legacy.name, "docstatus": 0},
		)

	return {
		"legacy_item": legacy,
		"replacement_item": replacement,
		"bins": bins,
		"batches": batches,
		"open_documents": open_documents,
		"totals": {
			"actual_qty": sum(flt(row.actual_qty) for row in bins),
			"stock_value": sum(flt(row.stock_value) for row in bins),
			"batch_count": len(batches),
			"barcoded_batch_count": len([row for row in batches if row.get("sr_barcode")]),
		},
		"writes_performed": False,
	}


@frappe.whitelist()
def import_legacy_batches(
	legacy_item: str,
	replacement_item: str,
	confirm: bool | str = False,
):
	"""Idempotently copy legacy barcode metadata. Never copy batch quantities or valuation."""
	_ensure_migration_permission()
	if str(confirm).lower() not in {"1", "true", "yes"}:
		frappe.throw(_("Set confirm=1 after reviewing preview_item_migration."))

	legacy = _get_item(legacy_item)
	replacement = _get_item(replacement_item)
	if not legacy.has_batch_no:
		frappe.throw(_("Legacy Item must be an ERPNext batch-enabled Item."))
	if replacement.has_batch_no:
		frappe.throw(_("Replacement Item must have Has Batch No disabled."))
	if replacement.has_serial_no:
		frappe.throw(_("Replacement Item must have serial tracking disabled."))

	fields = ["name", "manufacturing_date", "expiry_date", "disabled"]
	if not frappe.get_meta("Batch").has_field("sr_barcode"):
		frappe.throw(_("Batch does not have the legacy sr_barcode field."))
	fields.append("sr_barcode")
	batches = frappe.get_all("Batch", filters={"item": legacy.name}, fields=fields, order_by="creation asc")

	created = []
	skipped = []
	conflicts = []
	for batch in batches:
		barcode = (batch.get("sr_barcode") or "").strip()
		if not barcode:
			skipped.append({"batch": batch.name, "reason": "missing_barcode"})
			continue
		existing = frappe.db.get_value(
			"SR Compliance Batch", {"barcode": barcode}, ["name", "item"], as_dict=True
		)
		if existing:
			if existing.item == replacement.name:
				skipped.append({"batch": batch.name, "reason": "already_imported", "name": existing.name})
			else:
				conflicts.append({"batch": batch.name, "barcode": barcode, "existing_item": existing.item})
			continue

		doc = frappe.get_doc(
			{
				"doctype": "SR Compliance Batch",
				"barcode": barcode,
				"item": replacement.name,
				"compliance_batch_no": batch.name,
				"manufacturing_date": batch.manufacturing_date,
				"expiry_date": batch.expiry_date,
				"active": 0 if batch.disabled else 1,
				"legacy_batch": batch.name,
			}
		).insert(ignore_permissions=True)
		created.append(doc.name)

	return {
		"created": created,
		"skipped": skipped,
		"conflicts": conflicts,
		"stock_or_valuation_writes": False,
	}
