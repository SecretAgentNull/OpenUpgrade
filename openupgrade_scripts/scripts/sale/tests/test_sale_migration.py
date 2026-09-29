from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestSaleMigration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.product = cls.env["product.product"].search(
            [("name", "=", "OpenUpgrade test service")], limit=1
        )
        cls.order = cls.env["sale.order"].search(
            [("order_line.product_id", "=", cls.product.id)], limit=1
        )

    def test_automatic_invoice_moved_to_company(self):
        """The global config parameter became a per company field."""
        self.assertTrue(self.company.sale_automatic_invoice)
        self.assertFalse(
            self.env["ir.config_parameter"].search_count(
                [("key", "=", "sale.automatic_invoice")]
            )
        )

    def test_invoice_policy_default_moved_to_company(self):
        self.assertEqual(self.company.sale_invoice_policy, "delivery")
        self.assertFalse(
            self.env["ir.default"].search_count(
                [
                    ("field_id.model", "=", "product.template"),
                    ("field_id.name", "=", "invoice_policy"),
                ]
            )
        )

    def test_expense_policy_renamed(self):
        self.assertEqual(self.product.reinvoice_policy, "cost")
        self.assertNotIn("expense_policy", self.product._fields)

    def test_sale_delay_is_company_dependent(self):
        """The old global integer is now readable for every company."""
        for company in self.env["res.company"].search([]):
            self.assertEqual(
                self.product.with_company(company).sale_delay, 3, company.name
            )

    def test_customer_lead_rounded_up(self):
        line = self.order.order_line.filtered(
            lambda sol: sol.product_id == self.product
        )
        self.assertEqual(line.customer_lead, 3)

    def test_document_tax_mode_populated(self):
        """A new required stored selection must not be left empty."""
        self.env.cr.execute(
            "SELECT count(*) FROM sale_order WHERE document_tax_mode IS NULL"
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)

    def test_mail_templates_updated(self):
        template = self.env.ref("sale.email_template_edi_sale")
        self.assertIn("object.client_order_ref", template.subject)
        self.assertEqual(
            template.email_layout_xmlid,
            "mail.mail_notification_layout_with_responsible_signature",
        )
