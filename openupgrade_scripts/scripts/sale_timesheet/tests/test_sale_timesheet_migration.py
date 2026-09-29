from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestSaleTimesheetMigration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.timesheet = cls.env["account.analytic.line"].search(
            [("name", "=", "OpenUpgrade timesheet entry")], limit=1
        )

    def test_invoice_link_renamed(self):
        """19.0's timesheet_invoice_id is 20.0's reinvoice_move_id."""
        self.assertNotIn("timesheet_invoice_id", self.timesheet._fields)
        self.assertTrue(self.timesheet.reinvoice_move_id)

    def test_billable_type_recomputed(self):
        """A stored compute without init_storage is filled in by the ORM."""
        self.assertTrue(self.timesheet.billable_type)

    def test_invoice_link_column_keeps_its_values(self):
        """openupgrade.rename_fields renames the column itself, so the 19.0 links
        are what the 20.0 field reads."""
        self.env.cr.execute(
            """
            SELECT count(*) FROM account_analytic_line
            WHERE reinvoice_move_id IS NOT NULL
            """
        )
        self.assertGreater(self.env.cr.fetchone()[0], 0)
        self.env.cr.execute(
            """
            SELECT count(*) FROM information_schema.columns
            WHERE table_name = 'account_analytic_line'
                AND column_name = 'timesheet_invoice_id'
            """
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)

    def test_invoice_templates_attach_timesheet_report(self):
        """sale_timesheet/data/mail_template_data.xml is noupdate data of 20.0
        that a plain upgrade never applies, so the overlay has to."""
        report = self.env.ref("sale_timesheet.timesheet_report_account_move")
        for xmlid in (
            "account.email_template_edi_invoice",
            "account.email_template_edi_self_billing_invoice",
        ):
            template = self.env.ref(xmlid)
            self.assertIn(report, template.report_template_ids, xmlid)
