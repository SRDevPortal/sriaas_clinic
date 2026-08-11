from unittest.mock import call, patch

from frappe.tests import UnitTestCase

from sriaas_clinic.setup.sales_invoice import (
    HIDDEN_INVOICE_FIELDS,
    LEGACY_CUSTOMER_PROPERTY_SETTERS,
    _restore_customer_field_defaults,
)


class TestSalesInvoiceSetup(UnitTestCase):
    def test_mandatory_customer_field_is_not_hidden(self):
        self.assertNotIn("customer", HIDDEN_INVOICE_FIELDS)

    @patch("sriaas_clinic.setup.sales_invoice.frappe.clear_cache")
    @patch("sriaas_clinic.setup.sales_invoice.frappe.delete_doc")
    @patch("sriaas_clinic.setup.sales_invoice.frappe.db.exists", return_value=True)
    def test_legacy_customer_property_setters_are_removed(self, _exists, delete_doc, clear_cache):
        _restore_customer_field_defaults()

        delete_doc.assert_has_calls(
            [
                call(
                    "Property Setter",
                    f"Sales Invoice-customer-{prop}",
                    ignore_permissions=True,
                    force=True,
                )
                for prop in LEGACY_CUSTOMER_PROPERTY_SETTERS
            ]
        )
        clear_cache.assert_called_once_with(doctype="Sales Invoice")
