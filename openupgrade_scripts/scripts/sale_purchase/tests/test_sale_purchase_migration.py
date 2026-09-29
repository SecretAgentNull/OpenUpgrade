from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestSalePurchaseMigration(TransactionCase):
    def test_subcontract_service_moved_to_service_tracking(self):
        template = self.env["product.template"].search(
            [("name", "=", "OpenUpgrade test subcontracted service")], limit=1
        )
        self.assertEqual(template.service_tracking, "subcontract")
        # 20.0 requires the product to be purchasable to raise a RfQ
        self.assertTrue(template.purchase_ok)

    def test_reinvoiced_service_not_converted(self):
        """20.0 refuses 'subcontract' next to a reinvoicing policy other than
        'no', so the flag is dropped and reported instead."""
        template = self.env["product.template"].search(
            [("name", "=", "OpenUpgrade test reinvoiced service")], limit=1
        )
        self.assertEqual(template.service_tracking, "no")
        self.assertEqual(template.reinvoice_policy, "cost")

    def test_service_to_purchase_column_preserved(self):
        """The old company dependent flag is not dropped by OpenUpgrade, so
        third party code reading the column still finds the 19.0 values."""
        self.env.cr.execute(
            """
            SELECT count(*) FROM product_template
            WHERE jsonb_path_exists(service_to_purchase, '$.* ? (@ == true)')
            """
        )
        self.assertEqual(self.env.cr.fetchone()[0], 2)
