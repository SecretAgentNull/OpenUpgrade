# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def setup_accrual_accounts(env):
    """20.0 discovers the accrual accounts through the `sale` post init hook,
    which does not fire for a database that already has `sale` installed. Re-run
    the same chart template loading so upgraded companies end up with the same
    accounts as a fresh 20.0 database.

    This has to be an end script: it reads the chart template data files of the
    localization module, which are only all available once every module of the
    upgrade has been loaded.
    """
    if not env["res.company"].search_count(
        [("chart_template", "!=", False), ("account_invoices_to_issue_id", "=", False)]
    ):
        return
    env["account.chart.template"]._load_pre_defined_data(
        {
            "res.company": {
                "account_invoices_to_issue_id",
                "account_invoiced_not_delivered_id",
            }
        }
    )


@openupgrade.migrate()
def migrate(env, version):
    setup_accrual_accounts(env)
