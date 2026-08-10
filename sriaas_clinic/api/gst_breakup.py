from __future__ import annotations

import json
from collections import OrderedDict

import frappe
from frappe.utils import flt

from india_compliance.gst_india.utils.taxes_controller import (
    update_gst_details as update_india_compliance_gst_details,
)


BREAKUP_PRECISION = 2
TAX_HEADERS = ("IGST", "CGST", "SGST", "CESS", "CESS Non Advol")


def update_gst_breakup_table(doc, method=None, *args, **kwargs):
    if doc.doctype != "Sales Invoice":
        return

    if not getattr(doc, "items", None):
        doc.set("gst_breakup_table", "")
        return

    breakup_data = _get_reconciled_breakup_data(doc)
    doc.set("gst_breakup_table", _render_breakup_html(doc, breakup_data))



def prepare_gst_validation_fields(doc, method=None, *args, **kwargs):
    if doc.doctype != "Sales Invoice":
        return

    for item in doc.get("items") or []:
        taxable_amount = flt(
            item.get("base_net_amount")
            or item.get("net_amount")
            or item.get("taxable_value")
            or 0,
            BREAKUP_PRECISION,
        )
        item.taxable_value = taxable_amount
        if hasattr(item, "base_taxable_value"):
            item.base_taxable_value = taxable_amount
def refresh_gst_breakup_on_save(doc, method=None, *args, **kwargs):
    if doc.doctype != "Sales Invoice":
        return

    update_india_compliance_gst_details(doc, method=method)
    _sync_item_tax_fields(doc)
    _sync_tax_rows_with_item_totals(doc)
    update_gst_breakup_table(doc, method=method)


def _get_reconciled_breakup_data(doc) -> list[OrderedDict]:
    rows = _build_breakup_rows_from_items(doc)
    if not rows:
        return rows

    target_totals = _get_target_tax_totals(doc)
    current_totals = _get_current_breakup_totals(rows)

    for header in TAX_HEADERS:
        diff = flt(target_totals.get(header, 0) - current_totals.get(header, 0), BREAKUP_PRECISION)
        if not diff:
            continue

        for row in reversed(rows):
            tax_data = row.get(header)
            if not tax_data:
                continue
            tax_data["tax_amount"] = flt(tax_data.get("tax_amount", 0) + diff, BREAKUP_PRECISION)
            break

    return rows


def _build_breakup_rows_from_items(doc) -> list[OrderedDict]:
    rows_by_key: OrderedDict[tuple, OrderedDict] = OrderedDict()

    for item in doc.get("items") or []:
        taxable_amount = flt(
            item.get("taxable_value")
            or item.get("net_amount")
            or 0,
            BREAKUP_PRECISION,
        )
        row_tax_breakdown = _get_item_tax_breakdown(item)
        active_headers = [header for header in TAX_HEADERS if row_tax_breakdown.get(header)]
        primary_rate = next(
            (row_tax_breakdown[header]["tax_rate"] for header in TAX_HEADERS if row_tax_breakdown.get(header)),
            0.0,
        )
        row_key = (
            item.get("gst_hsn_code") or item.get("item_code") or item.get("item_name"),
            primary_rate,
            tuple(active_headers),
        )

        row = rows_by_key.setdefault(
            row_key,
            OrderedDict({
                "HSN/SAC": item.get("gst_hsn_code") or "",
                "Taxable Amount": 0.0,
            }),
        )
        row["Taxable Amount"] = flt(row["Taxable Amount"] + taxable_amount, BREAKUP_PRECISION)

        for header in active_headers:
            tax_data = row.setdefault(
                header,
                {"tax_rate": row_tax_breakdown[header]["tax_rate"], "tax_amount": 0.0},
            )
            tax_data["tax_amount"] = flt(
                tax_data["tax_amount"] + row_tax_breakdown[header]["tax_amount"],
                BREAKUP_PRECISION,
            )

    return list(rows_by_key.values())


def _get_target_tax_totals(doc) -> dict[str, float]:
    totals = {header: 0.0 for header in TAX_HEADERS}

    for tax in doc.get("taxes") or []:
        header = _map_tax_row_to_header(tax)
        if not header:
            continue

        totals[header] += flt(
            tax.get("tax_amount_after_discount_amount") or tax.get("tax_amount") or 0,
            BREAKUP_PRECISION,
        )

    return totals


def _get_item_derived_tax_totals(doc) -> dict[str, float]:
    totals = {header: 0.0 for header in TAX_HEADERS}

    for item in doc.get("items") or []:
        row_tax_breakdown = _get_item_tax_breakdown(item)
        for header, tax_data in row_tax_breakdown.items():
            totals[header] = flt(
                totals[header] + flt(tax_data.get("tax_amount"), BREAKUP_PRECISION),
                BREAKUP_PRECISION,
            )

    return totals


def _get_item_tax_breakdown(item) -> dict[str, dict[str, float]]:
    taxable_amount = flt(
        item.get("taxable_value")
        or item.get("net_amount")
        or 0,
        BREAKUP_PRECISION,
    )
    if taxable_amount <= 0:
        return {}

    tax_rates = {
        "IGST": flt(item.get("igst_rate"), BREAKUP_PRECISION),
        "CGST": flt(item.get("cgst_rate"), BREAKUP_PRECISION),
        "SGST": flt(item.get("sgst_rate"), BREAKUP_PRECISION),
        "CESS": flt(item.get("cess_rate"), BREAKUP_PRECISION),
        "CESS Non Advol": flt(item.get("cess_non_advol_rate"), BREAKUP_PRECISION),
    }
    active_headers = [header for header, rate in tax_rates.items() if rate]
    if not active_headers:
        return {}

    breakdown = {}
    for header in active_headers:
        header_rate = tax_rates[header]
        header_tax_amount = flt((taxable_amount * header_rate) / 100, BREAKUP_PRECISION)

        breakdown[header] = {
            "tax_rate": header_rate,
            "tax_amount": header_tax_amount,
        }

    return breakdown


def _sync_item_tax_fields(doc) -> None:
    for item in doc.get("items") or []:
        taxable_amount = flt(
            item.get("taxable_value")
            or item.get("net_amount")
            or 0,
            BREAKUP_PRECISION,
        )
        row_tax_breakdown = _get_item_tax_breakdown(item)

        item.taxable_value = taxable_amount
        if hasattr(item, "base_taxable_value"):
            item.base_taxable_value = flt(
                item.get("base_taxable_value")
                or item.get("base_net_amount")
                or taxable_amount,
                BREAKUP_PRECISION,
            )

        item.igst_amount = flt(row_tax_breakdown.get("IGST", {}).get("tax_amount", 0), BREAKUP_PRECISION)
        item.cgst_amount = flt(row_tax_breakdown.get("CGST", {}).get("tax_amount", 0), BREAKUP_PRECISION)
        item.sgst_amount = flt(row_tax_breakdown.get("SGST", {}).get("tax_amount", 0), BREAKUP_PRECISION)
        item.cess_amount = flt(row_tax_breakdown.get("CESS", {}).get("tax_amount", 0), BREAKUP_PRECISION)
        item.cess_non_advol_amount = flt(
            row_tax_breakdown.get("CESS Non Advol", {}).get("tax_amount", 0),
            BREAKUP_PRECISION,
        )


def _sync_tax_rows_with_item_totals(doc) -> None:
    if not getattr(doc, "taxes", None):
        return

    target_totals = _get_item_derived_tax_totals(doc)
    item_wise_details = {header: {} for header in TAX_HEADERS}
    for item in doc.get("items") or []:
        item_key = item.get("item_code") or item.get("item_name")
        if not item_key:
            continue

        row_tax_breakdown = _get_item_tax_breakdown(item)
        for header, tax_data in row_tax_breakdown.items():
            item_wise_details[header][item_key] = [
                flt(tax_data.get("tax_rate"), BREAKUP_PRECISION),
                flt(
                    item_wise_details[header].get(item_key, [0, 0])[1]
                    + flt(tax_data.get("tax_amount"), BREAKUP_PRECISION),
                    BREAKUP_PRECISION,
                ),
            ]

    cumulative_total = flt(doc.get("net_total"), BREAKUP_PRECISION)
    total_taxes = 0.0

    for tax in doc.get("taxes") or []:
        header = _map_tax_row_to_header(tax)
        tax_amount = flt(target_totals.get(header, 0), BREAKUP_PRECISION) if header else flt(
            tax.get("tax_amount_after_discount_amount") or tax.get("tax_amount") or 0,
            BREAKUP_PRECISION,
        )

        total_taxes = flt(total_taxes + tax_amount, BREAKUP_PRECISION)
        cumulative_total = flt(doc.get("net_total") + total_taxes, BREAKUP_PRECISION)

        tax.tax_amount = tax_amount
        tax.tax_amount_after_discount_amount = tax_amount
        tax.base_tax_amount = tax_amount
        tax.base_tax_amount_after_discount_amount = tax_amount
        tax.total = cumulative_total
        tax.base_total = cumulative_total
        if header:
            tax.item_wise_tax_detail = json.dumps(item_wise_details.get(header, {}), separators=(",", ":"))

    doc.total_taxes_and_charges = total_taxes
    doc.base_total_taxes_and_charges = total_taxes
    doc.grand_total = flt(doc.get("net_total") + total_taxes, BREAKUP_PRECISION)
    doc.base_grand_total = doc.grand_total
    doc.total = doc.grand_total
    doc.base_total = doc.base_grand_total


def _get_current_breakup_totals(rows: list[OrderedDict]) -> dict[str, float]:
    totals = {header: 0.0 for header in TAX_HEADERS}

    for row in rows:
        for header in TAX_HEADERS:
            tax_data = row.get(header)
            if not tax_data:
                continue
            totals[header] += flt(tax_data.get("tax_amount", 0), BREAKUP_PRECISION)

    return totals


def _map_tax_row_to_header(tax) -> str | None:
    gst_tax_type = (tax.get("gst_tax_type") or "").lower()
    account_head = (tax.get("account_head") or "").lower()
    description = (tax.get("description") or "").lower()
    source = " ".join((gst_tax_type, account_head, description))

    if "cess_non_advol" in source:
        return "CESS Non Advol"
    if "cess" in source:
        return "CESS"
    if "igst" in source:
        return "IGST"
    if "cgst" in source:
        return "CGST"
    if "sgst" in source:
        return "SGST"
    return None


def _render_breakup_html(doc, breakup_data: list[OrderedDict]) -> str:
    if not breakup_data:
        return ""

    first_row = breakup_data[0]
    columns = list(first_row.keys())
    lines = ['<div class="tax-break-up" style="overflow-x: auto;">', '\t<table class="table table-bordered table-hover">']

    lines.append("\t\t<thead>")
    lines.append("\t\t\t<tr>")
    for column in columns:
        cls = "text-left" if column in ("HSN/SAC", "Item") else "text-right"
        lines.append(f"\t\t\t\t<th class=\"{cls}\">{frappe.as_unicode(column)}</th>")
    lines.append("\t\t\t</tr>")
    lines.append("\t\t</thead>")
    lines.append("\t\t<tbody>")

    is_return = bool(doc.get("is_return"))

    for row in breakup_data:
        lines.append("\t\t\t<tr>")
        for column in columns:
            value = row.get(column)
            if column in ("HSN/SAC", "Item"):
                lines.append(f"\t\t\t\t<td class=\"text-left\">{frappe.as_unicode(value or '')}</td>")
                continue

            if column == "Taxable Amount":
                amount = abs(flt(value)) if is_return else flt(value)
                lines.append(
                    "\t\t\t\t<td class=\"text-right\">{0}</td>".format(
                        frappe.utils.fmt_money(amount, currency="INR")
                    )
                )
                continue

            tax_rate = flt((value or {}).get("tax_rate", 0), BREAKUP_PRECISION)
            tax_amount = flt((value or {}).get("tax_amount", 0), BREAKUP_PRECISION)
            if is_return:
                tax_amount = abs(tax_amount)

            rate_text = f"({tax_rate}%)&nbsp;" if tax_rate or not tax_amount else ""
            amount_text = frappe.utils.fmt_money(tax_amount, currency="INR")
            lines.append(f"\t\t\t\t<td class=\"text-right\">{rate_text}{amount_text}</td>")

        lines.append("\t\t\t</tr>")

    lines.append("\t\t</tbody>")
    lines.append("\t</table>")
    lines.append("</div>")
    return "".join(lines)

