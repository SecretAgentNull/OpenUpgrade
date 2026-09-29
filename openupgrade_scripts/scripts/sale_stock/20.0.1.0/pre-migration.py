# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def convert_company_security_lead_to_integer(env):
    """res.company#security_lead counts days, so 20.0 makes it an Integer.

    Round up like sale.order.line#customer_lead does: a fractional safety margin
    that is truncated would schedule procurements later than 19.0 did. The NULL
    branch keeps the ALTER legal on databases whose column predates the NOT
    NULL constraint.
    """
    if not openupgrade.column_exists(env.cr, "res_company", "security_lead"):
        return
    env.cr.execute(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = 'res_company' AND column_name = 'security_lead'
        """
    )
    row = env.cr.fetchone()
    if not row or row[0] == "integer":
        return
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE res_company
        ALTER COLUMN security_lead TYPE integer
        USING CASE
            WHEN security_lead IS NULL THEN NULL
            ELSE CEIL(security_lead)::integer
        END
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    convert_company_security_lead_to_integer(env)
