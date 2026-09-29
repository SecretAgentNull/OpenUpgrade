from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestSaleStockMigration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.product = cls.env["product.product"].search(
            [("name", "=", "OpenUpgrade test storable")], limit=1
        )
        cls.order = cls.env["sale.order"].search(
            [("order_line.product_id", "=", cls.product.id)], limit=1
        )

    def test_security_lead_is_integer(self):
        """1.5 safety days became 2, rounded up like customer_lead."""
        self.env.cr.execute(
            """
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'res_company' AND column_name = 'security_lead'
            """
        )
        self.assertEqual(self.env.cr.fetchone()[0], "integer")
        self.assertEqual(self.company.security_lead, 2)

    def test_picking_policy_default_moved_to_company(self):
        self.assertEqual(self.company.picking_policy, "one")
        self.assertFalse(
            self.env["ir.default"].search_count(
                [
                    ("field_id.model", "=", "sale.order"),
                    ("field_id.name", "=", "picking_policy"),
                    ("company_id", "=", self.company.id),
                    ("user_id", "=", False),
                ]
            )
        )

    def test_user_level_picking_policy_default_kept(self):
        """Only the company wide default has a successor field."""
        self.assertEqual(
            self.env["ir.default"]._get(
                "sale.order",
                "picking_policy",
                user_id=self.env.ref("base.user_admin").id,
                company_id=self.company.id,
            ),
            "direct",
        )

    def test_picking_sale_id_kept(self):
        """stock.picking#sale_id is not recomputed on upgrade (init_storage is a
        no-op in 20.0), so the 19.0 links must still be there."""
        picking = self.env["stock.picking"].search(
            [("sale_id", "=", self.order.id)], limit=1
        )
        self.assertTrue(picking)
        self.assertEqual(picking.sale_id, self.order)
