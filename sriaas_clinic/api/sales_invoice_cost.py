# sriaas_clinic/api/sales_invoice_cost.py
import frappe

def _get_item_cost(item_code: str, price_list: str) -> float:
    """Fetch sr_cost_price from Item Price matching item + price_list (selling=1).
    Pick the newest by valid_from (NULLs last) then modified."""
    if not item_code or not price_list:
        return 0.0

    rows = frappe.get_all(
        "Item Price",
        filters={"item_code": item_code, "price_list": price_list, "selling": 1},
        fields=["sr_cost_price", "valid_from", "modified"],
        # Put NULL valid_from last, then newest first; works on MariaDB/MySQL
        order_by='IFNULL(valid_from, "1900-01-01") DESC, modified DESC',
        limit=1,
    )
    cp = (rows[0]["sr_cost_price"] if rows else 0) or 0
    try:
        return float(cp)
    except Exception:
        return 0.0


def before_save(doc, method=None):
    """Compute per-row cost & totals on Sales Invoice before save."""
    selling_pl = getattr(doc, "selling_price_list", None) or getattr(doc, "price_list", None)

    total_cost = 0.0
    total_net = 0.0

    for it in (doc.items or []):
        # Determine price list context for the item
        effective_pl = getattr(it, "price_list", None) or selling_pl

        cp = _get_item_cost(it.item_code, effective_pl)
        it.sr_cost_price = cp
        it.sr_cost_amount = round((it.qty or 0) * (cp or 0), 2)

        # Rate may be zero (free item); guard divide by zero
        rate = float(it.rate or 0)
        it.sr_cost_pct = round(((cp / rate) * 100) if rate else 0, 2)

        total_cost += float(it.sr_cost_amount or 0)
        total_net += float(it.net_amount or 0)

    doc.sr_total_cost = round(total_cost, 2)

    # Prefer grand_total, else sum of net_amount
    denom = float(doc.grand_total or 0) or total_net or 0.0
    doc.sr_cost_pct_overall = round((total_cost / denom * 100), 2) if denom else 0.0
    doc.sr_margin_overall = round(((denom - total_cost) / denom * 100), 2) if denom else 0.0
