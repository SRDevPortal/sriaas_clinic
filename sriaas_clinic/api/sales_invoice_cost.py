# sriaas_clinic/api/sales_invoice_cost.py
import frappe


def _get_buying_price_list():
    return (
        frappe.db.get_single_value("Buying Settings", "buying_price_list")
        or "Standard Buying"
    )


def _get_item_cost(item_code, buying_price_list):
    if not item_code or not buying_price_list:
        return 0.0

    rows = frappe.get_all(
        "Item Price",
        filters={
            "item_code": item_code,
            "price_list": buying_price_list,
            "buying": 1,
        },
        fields=["price_list_rate"],
        order_by='IFNULL(valid_from, "1900-01-01") DESC, modified DESC',
        limit=1,
    )
    return float((rows[0].price_list_rate if rows else 0) or 0)


# before_save handler
def before_save(doc, method=None):
    """Compute per-row cost from the default buying price list and update totals."""

    buying_price_list = _get_buying_price_list()
    total_cost = 0.0
    total_net = 0.0

    for it in (doc.items or []):
        rate = float(it.rate or 0)
        cp = _get_item_cost(it.item_code, buying_price_list)
        it.sr_cost_price = cp
        it.sr_cost_amount = round((it.qty or 0) * (cp or 0), 2)

        # Rate may be zero (free item); guard divide by zero
        it.sr_cost_pct = round(((cp / rate) * 100) if rate else 0, 2)

        total_cost += float(it.sr_cost_amount or 0)
        total_net += float(it.net_amount or 0)

    doc.sr_total_cost = round(total_cost, 2)

    # Prefer grand_total, else sum of net_amount
    denom = float(doc.grand_total or 0) or total_net or 0.0
    doc.sr_cost_pct_overall = round((total_cost / denom * 100), 2) if denom else 0.0
    doc.sr_margin_overall = round(((denom - total_cost) / denom * 100), 2) if denom else 0.0


def backfill_from_buying_price(batch_size=500, max_batches=None):
    """Backfill costs from the configured buying price list."""
    batch_size = max(int(batch_size), 1)
    max_batches = int(max_batches) if max_batches else None
    buying_price_list = _get_buying_price_list()
    invoice_filters = {"docstatus": ["in", [0, 1]]}
    item_filters = {"docstatus": ["in", [0, 1]]}

    result = {
        "eligible_invoices": frappe.db.count("Sales Invoice", invoice_filters),
        "eligible_items": frappe.db.count("Sales Invoice Item", item_filters),
        "buying_price_list": buying_price_list,
        "processed_invoices": 0,
        "updated_items": 0,
        "updated_invoices": 0,
    }

    last_name = ""
    batch_number = 0

    while True:
        invoice_names = frappe.get_all(
            "Sales Invoice",
            filters={
                "docstatus": ["in", [0, 1]],
                "name": [">", last_name],
            },
            pluck="name",
            order_by="name asc",
            limit_page_length=batch_size,
        )
        if not invoice_names:
            break

        params = {
            "buying_price_list": buying_price_list,
            "invoice_names": tuple(invoice_names),
        }

        try:
            frappe.db.sql(
                """
                UPDATE `tabSales Invoice Item` AS item
                LEFT JOIN (
                    SELECT ranked.item_code, ranked.price_list_rate
                    FROM (
                        SELECT
                            price.item_code,
                            price.price_list_rate,
                            ROW_NUMBER() OVER (
                                PARTITION BY price.item_code
                                ORDER BY
                                    IFNULL(price.valid_from, "1900-01-01") DESC,
                                    price.modified DESC
                            ) AS price_rank
                        FROM `tabItem Price` AS price
                        WHERE
                            price.price_list = %(buying_price_list)s
                            AND price.buying = 1
                    ) AS ranked
                    WHERE ranked.price_rank = 1
                ) AS buying_price ON buying_price.item_code = item.item_code
                SET
                    item.sr_cost_price = IFNULL(buying_price.price_list_rate, 0),
                    item.sr_cost_amount = ROUND(
                        IFNULL(item.qty, 0)
                        * IFNULL(buying_price.price_list_rate, 0),
                        2
                    ),
                    item.sr_cost_pct = CASE
                        WHEN IFNULL(item.rate, 0) = 0 THEN 0
                        ELSE ROUND(
                            IFNULL(buying_price.price_list_rate, 0)
                            / item.rate * 100,
                            2
                        )
                    END
                WHERE
                    item.parent IN %(invoice_names)s
                    AND NOT (
                        item.sr_cost_price
                            <=> IFNULL(buying_price.price_list_rate, 0)
                        AND item.sr_cost_amount <=> ROUND(
                            IFNULL(item.qty, 0)
                            * IFNULL(buying_price.price_list_rate, 0),
                            2
                        )
                        AND item.sr_cost_pct <=> CASE
                            WHEN IFNULL(item.rate, 0) = 0 THEN 0
                            ELSE ROUND(
                                IFNULL(buying_price.price_list_rate, 0)
                                / item.rate * 100,
                                2
                            )
                        END
                    )
                """,
                params,
            )
            result["updated_items"] += frappe.db._cursor.rowcount

            frappe.db.sql(
                """
                UPDATE `tabSales Invoice` AS invoice
                LEFT JOIN (
                    SELECT
                        item.parent,
                        ROUND(SUM(IFNULL(item.sr_cost_amount, 0)), 2) AS total_cost,
                        SUM(IFNULL(item.net_amount, 0)) AS total_net
                    FROM `tabSales Invoice Item` AS item
                    WHERE item.parent IN %(invoice_names)s
                    GROUP BY item.parent
                ) AS costs ON costs.parent = invoice.name
                SET
                    invoice.sr_total_cost = IFNULL(costs.total_cost, 0),
                    invoice.sr_cost_pct_overall = CASE
                        WHEN COALESCE(
                            NULLIF(invoice.grand_total, 0),
                            NULLIF(costs.total_net, 0),
                            0
                        ) = 0 THEN 0
                        ELSE ROUND(
                            IFNULL(costs.total_cost, 0)
                            / COALESCE(
                                NULLIF(invoice.grand_total, 0),
                                NULLIF(costs.total_net, 0),
                                0
                            ) * 100,
                            2
                        )
                    END,
                    invoice.sr_margin_overall = CASE
                        WHEN COALESCE(
                            NULLIF(invoice.grand_total, 0),
                            NULLIF(costs.total_net, 0),
                            0
                        ) = 0 THEN 0
                        ELSE ROUND(
                            (
                                COALESCE(
                                    NULLIF(invoice.grand_total, 0),
                                    NULLIF(costs.total_net, 0),
                                    0
                                ) - IFNULL(costs.total_cost, 0)
                            )
                            / COALESCE(
                                NULLIF(invoice.grand_total, 0),
                                NULLIF(costs.total_net, 0),
                                0
                            ) * 100,
                            2
                        )
                    END
                WHERE invoice.name IN %(invoice_names)s
                """,
                params,
            )
            result["updated_invoices"] += frappe.db._cursor.rowcount
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            raise

        result["processed_invoices"] += len(invoice_names)
        batch_number += 1
        last_name = invoice_names[-1]

        if batch_number % 10 == 0:
            print(
                f"Processed {result['processed_invoices']} "
                f"of {result['eligible_invoices']} invoices",
                flush=True,
            )

        if max_batches and batch_number >= max_batches:
            break

    return result
