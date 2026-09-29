from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestSalePdfQuoteBuilderMigration(TransactionCase):
    def test_inside_document_now_visible_on_quote(self):
        document = self.env["product.document"].search(
            [("name", "=", "OpenUpgrade inside document")], limit=1
        )
        self.assertTrue(document)
        self.assertEqual(document.attached_on_sale, "quotation")

    def test_no_obsolete_selection_value_left(self):
        self.env.cr.execute(
            "SELECT count(*) FROM product_document WHERE attached_on_sale = 'inside'"
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)
