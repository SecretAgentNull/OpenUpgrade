# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from openupgradelib import openupgrade

_translated_templates = [
    "email_template_edi_sale",
    "email_template_proforma",
    "mail_template_sale_confirmation",
    "mail_template_sale_payment_executed",
]


def fill_product_sale_delay(env):
    """Reinstate the archived global sale_delay as a company dependent value:
    in 19.0 one integer applied to every company, so spread it over all of them.

    Overwrite unconditionally, do not test the column for NULL: the field has a
    default in 20.0, so ``Field._init_column_data()`` already filled the freshly
    created jsonb column with ``{"<env.company id>": 0}`` before this script
    runs. The archived value is the real data and wins over that placeholder.
    """
    legacy = openupgrade.get_legacy_name("sale_delay")
    if not (
        openupgrade.column_exists(env.cr, "product_template", legacy)
        and openupgrade.column_exists(env.cr, "product_template", "sale_delay")
    ):
        return
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE product_template pt
        SET sale_delay = company_values.payload
        FROM (
            SELECT pt2.id AS tid,
                jsonb_object_agg(rc.id::text, to_jsonb(pt2."{legacy}")) AS payload
            FROM product_template pt2
            CROSS JOIN res_company rc
            WHERE pt2."{legacy}" IS NOT NULL
            GROUP BY pt2.id
        ) company_values
        WHERE pt.id = company_values.tid
        """,
    )


def move_automatic_invoice_to_company(env):
    """The global `sale.automatic_invoice` config parameter becomes the
    res.company#sale_automatic_invoice field. Nothing in 20.0 reads the
    parameter any more (sale.const.PARAM_CRON_MAPPING only knows about
    `sale.async_emails`), so it is removed after the move."""
    env.cr.execute(
        """
        SELECT value FROM ir_config_parameter
        WHERE key = 'sale.automatic_invoice'
        """
    )
    row = env.cr.fetchone()
    if not row:
        return
    enabled = row[0].lower() in ("true", "1", "yes", "on")
    # Go through the ORM: res.company.write() activates sale.send_invoice_cron,
    # the only mechanism that now drives automatic invoicing. Raw SQL would set
    # the flag on the companies and leave the cron dormant.
    env["res.company"].with_context(active_test=False).search([]).write(
        {"sale_automatic_invoice": enabled}
    )
    openupgrade.logged_query(
        env.cr,
        "DELETE FROM ir_config_parameter WHERE key = 'sale.automatic_invoice'",
    )
    openupgrade.message(
        env.cr,
        "sale",
        "res.company",
        "sale_automatic_invoice",
        f"Moved the global sale.automatic_invoice parameter ({row[0]}) to every "
        "company: 20.0 makes it a per company setting.",
    )


def move_invoice_policy_default_to_company(env):
    """`Default Invoice Policy` used to be an ir.default on product.template;
    20.0 replaces it with the required res.company#sale_invoice_policy field.

    Defaults that carry a condition stay where they are: a company field cannot
    reproduce a conditional default.
    """
    if not openupgrade.column_exists(env.cr, "res_company", "sale_invoice_policy"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        SELECT d.company_id, d.json_value
        FROM ir_default d
        JOIN ir_model_fields f ON f.id = d.field_id
        JOIN ir_model m ON m.id = f.model_id
        WHERE m.model = 'product.template' AND f.name = 'invoice_policy'
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
                "UPDATE res_company SET sale_invoice_policy = %s WHERE id = %s",
                (policy, company_id),
            )
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM ir_default d
        USING ir_model_fields f, ir_model m
        WHERE f.id = d.field_id AND m.id = f.model_id
            AND m.model = 'product.template' AND f.name = 'invoice_policy'
            AND d.condition IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "sale", "20.0.1.2/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "sale",
        _translated_templates,
        ["name", "subject", "description", "body_html"],
    )
    fill_product_sale_delay(env)
    move_automatic_invoice_to_company(env)
    move_invoice_policy_default_to_company(env)
