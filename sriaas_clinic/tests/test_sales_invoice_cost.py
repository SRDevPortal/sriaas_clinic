from types import SimpleNamespace
from unittest.mock import call, patch

from frappe.tests import UnitTestCase

from sriaas_clinic.api.sales_invoice_cost import _get_item_cost, before_save


class TestSalesInvoiceCost(UnitTestCase):
    @patch("sriaas_clinic.api.sales_invoice_cost.frappe.get_all")
    def test_item_cost_uses_frappe_safe_ordering(self, get_all):
        get_all.return_value = [SimpleNamespace(price_list_rate=125)]

        cost = _get_item_cost("ITEM-001", "Standard Buying")

        self.assertEqual(cost, 125.0)
        get_all.assert_called_once_with(
            "Item Price",
            filters={
                "item_code": "ITEM-001",
                "price_list": "Standard Buying",
                "buying": 1,
            },
            fields=["price_list_rate"],
            order_by="valid_from desc, modified desc",
            limit=1,
        )

    @patch("sriaas_clinic.api.sales_invoice_cost.frappe.get_all")
    def test_item_cost_returns_zero_when_no_price_exists(self, get_all):
        get_all.return_value = []

        self.assertEqual(_get_item_cost("ITEM-001", "Standard Buying"), 0.0)

    @patch("sriaas_clinic.api.sales_invoice_cost._get_buying_price_list", return_value="Standard Buying")
    @patch("sriaas_clinic.api.sales_invoice_cost._get_item_cost", side_effect=[40, 0])
    def test_before_save_calculates_costs_and_handles_zero_rate(self, get_item_cost, _get_price_list):
        first_item = SimpleNamespace(
            item_code="ITEM-001",
            qty=2,
            rate=100,
            net_amount=200,
        )
        free_item = SimpleNamespace(
            item_code="ITEM-002",
            qty=1,
            rate=0,
            net_amount=0,
        )
        invoice = SimpleNamespace(
            items=[first_item, free_item],
            grand_total=200,
        )

        before_save(invoice)

        self.assertEqual(first_item.sr_cost_price, 40)
        self.assertEqual(first_item.sr_cost_amount, 80)
        self.assertEqual(first_item.sr_cost_pct, 40)
        self.assertEqual(free_item.sr_cost_pct, 0)
        self.assertEqual(invoice.sr_total_cost, 80)
        self.assertEqual(invoice.sr_cost_pct_overall, 40)
        self.assertEqual(invoice.sr_margin_overall, 60)
        get_item_cost.assert_has_calls(
            [
                call("ITEM-001", "Standard Buying"),
                call("ITEM-002", "Standard Buying"),
            ],
        )
