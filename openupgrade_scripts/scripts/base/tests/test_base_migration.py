from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestBaseMigration(TransactionCase):
    """base has no fixture of its own: everything below is about the data files
    and the security files the upgrade itself loads."""

    def test_state_xmlids_follow_the_csv(self):
        """20.0 re-keys the ids of base/data/res.country.state.csv to the state
        codes, so the pre-migration has to rename them first."""
        state = self.env.ref("base.state_in_od")
        self.assertEqual((state.code, state.country_id.code), ("OD", "IN"))
        self.assertEqual(state.name, "Odisha")
        self.assertFalse(
            self.env["ir.model.data"].search_count(
                [("module", "=", "base"), ("name", "=", "state_in_or")]
            )
        )

    def test_no_state_duplicated(self):
        """Without the rename the csv inserts a second Odisha and the file stops
        on res_country_state_name_code_uniq."""
        self.env.cr.execute(
            """
            SELECT count(*)
            FROM (
                SELECT country_id, code
                FROM res_country_state
                GROUP BY country_id, code
                HAVING count(*) > 1
            ) duplicates
            """
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)
        self.env.cr.execute(
            """
            SELECT count(*)
            FROM res_country_state state
            LEFT JOIN ir_model_data data
                ON data.res_id = state.id AND data.model = 'res.country.state'
            WHERE data.id IS NULL
            """
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)

    def test_access_xmlids_handed_over_to_ir_access(self):
        """The ids of the 19.0 access rights are reused by 20.0 for its
        ir.access records, the old rows keep a prefixed copy."""
        reused = self.env.ref("base.access_decimal_precision_config")
        self.assertEqual(reused._name, "ir.access")
        legacy = self.env["ir.model.data"].search(
            [
                ("module", "=", "base"),
                ("name", "=", "openupgrade_legacy_access_decimal_precision_config"),
            ]
        )
        self.assertEqual(legacy.model, "ir.model.access")
        self.assertTrue(legacy.res_id)

    def test_legacy_access_rows_survive(self):
        """20.0 ignores both tables, but deleting their metadata would cascade
        into them through model_id, so they have to be left alone."""
        self.env.cr.execute("SELECT count(*) FROM ir_model_access")
        self.assertGreater(self.env.cr.fetchone()[0], 100)
        self.env.cr.execute("SELECT count(*) FROM ir_rule")
        self.assertGreater(self.env.cr.fetchone()[0], 50)
        self.assertEqual(
            self.env["ir.model"].search_count(
                [("model", "in", ("ir.rule", "ir.model.access"))]
            ),
            2,
            "the metadata of the removed models must stay, without external id",
        )
        self.assertFalse(
            self.env["ir.model.data"].search_count(
                [
                    ("module", "=", "base"),
                    ("name", "in", ("model_ir_rule", "model_ir_model_access")),
                ]
            )
        )
