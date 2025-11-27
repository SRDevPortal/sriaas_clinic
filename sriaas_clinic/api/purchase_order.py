# apps/sriaas_clinic/sriaas_clinic/api/purchase_order.py
from __future__ import unicode_literals
import frappe
import time
import re
import traceback

ALNUM_RE = re.compile(r'[^A-Z0-9]')

def _sanitize_for_code(s, length):
    if not s:
        return ""
    s_up = (s or "").upper()
    clean = ALNUM_RE.sub("", s_up)
    return clean[:length]

def _next_sequence_for_prefix(prefix):
    like_pattern = prefix + "-%"
    try:
        row = frappe.db.sql("""
            SELECT MAX(CAST(RIGHT(`name`, 3) AS UNSIGNED)) AS max_seq
            FROM `tabBatch`
            WHERE `name` LIKE %(like)s
              AND RIGHT(`name`, 4) REGEXP '-[0-9]{3}$'
        """, {"like": like_pattern}, as_dict=1)
        max_seq = row and row[0].get("max_seq") or 0
        if max_seq is None:
            max_seq = 0
        return int(max_seq or 0) + 1
    except Exception:
        frappe.log_error(traceback.format_exc(), "sriaas_clinic._next_sequence_for_prefix")
        return 1

def create_batches_before_submit(doc, method=None):
    """
    For each Purchase Order item row without batch_no:
      - If the Item has is_stock_item=True and has_batch_no=True -> create batch and set row.batch_no
      - If not enabled -> COLLECT and then THROW to block submit (user must enable item first)
    """
    skipped = []   # collect tuples (item_code, reason)
    created = []

    for row in (doc.get("items") or []):
        try:
            item_code = (row.get("item_code") or row.get("item") or "").strip()
            if not item_code:
                continue

            # skip if user already set batch_no (but still ensure the item is allowed to have batch)
            if row.get("batch_no"):
                # still validate that item supports batch; if not, treat as skipped/error
                try:
                    item_doc = frappe.get_cached_doc("Item", item_code)
                except Exception:
                    skipped.append((item_code, "Item not found"))
                    continue
                if not (bool(item_doc.get("is_stock_item")) and bool(item_doc.get("has_batch_no"))):
                    reason_parts = []
                    if not item_doc.get("is_stock_item"):
                        reason_parts.append("is_stock_item disabled")
                    if not item_doc.get("has_batch_no"):
                        reason_parts.append("has_batch_no disabled")
                    skipped.append((item_code, ", ".join(reason_parts)))
                continue

            # fetch item once (cached)
            try:
                item_doc = frappe.get_cached_doc("Item", item_code)
            except Exception:
                # If Item not found, mark and continue
                skipped.append((item_code, "Item not found"))
                continue

            # Check item inventory/batch flags
            is_stock_item = bool(item_doc.get("is_stock_item"))
            has_batch_no = bool(item_doc.get("has_batch_no"))

            if not (is_stock_item and has_batch_no):
                reason_parts = []
                if not is_stock_item:
                    reason_parts.append("is_stock_item disabled")
                if not has_batch_no:
                    reason_parts.append("has_batch_no disabled")
                skipped.append((item_code, ", ".join(reason_parts)))
                continue

            # supplier from Purchase Order (doc)
            supplier_name = (getattr(doc, "supplier", "") or "").strip()

            sup_code = _sanitize_for_code(supplier_name, 2) or "ZZ"
            item_code_part = _sanitize_for_code(item_code, 4) or "ITEM"

            prefix = f"{sup_code}-{item_code_part}"

            seq = _next_sequence_for_prefix(prefix)
            seq_str = f"{seq:03d}"

            batch_name = f"{prefix}-{seq_str}"

            # if batch not exists, create it; else reuse
            if not frappe.db.exists("Batch", batch_name):
                b = frappe.get_doc({
                    "doctype": "Batch",
                    "batch_id": batch_name,
                    "item": item_code
                })
                if row.get("expiry_date"):
                    b.expiry_date = row.get("expiry_date")
                b.insert(ignore_permissions=True)
                created_batch_id = getattr(b, "batch_id", None) or b.name
            else:
                created_batch_id = batch_name

            # Assign batch to the child row (mutation in before_submit persists)
            row.batch_no = created_batch_id
            created.append(created_batch_id)

        except Exception:
            frappe.log_error(traceback.format_exc(), "sriaas_clinic.create_batches_before_submit")
            # continue collecting other errors

    # If any skipped items found, block submit with a clear message
    if skipped:
        lines = []
        for item_code, reason in skipped:
            # create clickable link to the Item doc for convenience
            try:
                item_link = frappe.utils.get_link_to_form("Item", item_code)
            except Exception:
                item_link = frappe.utils.escape_html(item_code)
            lines.append(f"- {item_link}: {frappe.utils.escape_html(reason)}")

        message = "<b>Cannot Submit Purchase Order</b><br><br>"
        message += "The following items are not configured to allow Batch. Please enable <i>is_stock_item</i> and <i>has_batch_no</i> on their Item master, then try again:<br><br>"
        message += "<br>".join(lines)
        # This will raise ValidationError and stop the submit
        frappe.throw(message)

    # No explicit commit — submit flow will commit the transaction.
