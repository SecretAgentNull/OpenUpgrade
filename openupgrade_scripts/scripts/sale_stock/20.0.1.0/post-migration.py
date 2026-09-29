# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from openupgradelib import openupgrade


def move_picking_policy_default_to_company(env):
    """The `Default Shipping Policy` setting used to store an ir.default on
    sale.order#picking_policy; 20.0 reads the same value from the new
    res.company#picking_policy field (stock declares it) and uses it as the
    default of the order.

    Defaults that a single user set for himself, or that are bound to a
    condition, keep working as ir.default: only the plain company wide ones have
    a successor field.
    """
    if not openupgrade.column_exists(env.cr, "res_company", "picking_policy"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        SELECT d.company_id, d.json_value
        FROM ir_default d
        JOIN ir_model_fields f ON f.id = d.field_id
        JOIN ir_model m ON m.id = f.model_id
        WHERE m.model = 'sale.order' AND f.name = 'picking_policy'
            AND d.user_id IS NULL
            AND d.condition IS NULL
        """,
    )
    rows = env.cr.fetchall()
    if not rows:
        return
    # ir.default keeps the value in its json representation
    company_policies = {
        company_id: json.loads(value) for company_id, value in rows if company_id
    }
    global_policy = next(
        (json.loads(value) for company_id, value in rows if not company_id), None
    )
    env.cr.execute("SELECT id FROM res_company")
    for (company_id,) in env.cr.fetchall():
        policy = company_policies.get(company_id, global_policy)
        if policy:
            openupgrade.logged_query(
                env.cr,
                "UPDATE res_company SET picking_policy = %s WHERE id = %s",
                (policy, company_id),
            )
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM ir_default d
        USING ir_model_fields f, ir_model m
        WHERE f.id = d.field_id AND m.id = f.model_id
            AND m.model = 'sale.order' AND f.name = 'picking_policy'
            AND d.user_id IS NULL
            AND d.condition IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    move_picking_policy_default_to_company(env)
