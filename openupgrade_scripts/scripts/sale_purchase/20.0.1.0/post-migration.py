# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""`Subcontract Service` (product.template#service_to_purchase) is gone in 20.0:
the option becomes one more value of the global
product.template#service_tracking selection ('subcontract').

This is a post-migration because service_tracking may only be set to
'subcontract' together with a `reinvoice_policy` value that sale's pre-migration
has just produced by renaming expense_policy.
"""

from openupgradelib import openupgrade

# jsonpath: any company had the company dependent flag on
ANY_COMPANY_ON = "$.* ? (@ == true)"


def subcontract_service_to_service_tracking(env):
    if not openupgrade.column_exists(env.cr, "product_template", "service_to_purchase"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_template
        SET service_tracking = 'subcontract', purchase_ok = True
        WHERE type = 'service'
            AND reinvoice_policy = 'no'
            AND service_tracking = 'no'
            AND service_to_purchase IS NOT NULL
            AND jsonb_path_exists(service_to_purchase, %s::jsonpath)
        """,
        (ANY_COMPANY_ON,),
    )
    env.cr.execute(
        """
        SELECT count(*)
        FROM product_template
        WHERE type = 'service'
            AND service_to_purchase IS NOT NULL
            AND jsonb_path_exists(service_to_purchase, %s::jsonpath)
            AND service_tracking != 'subcontract'
        """,
        (ANY_COMPANY_ON,),
    )
    dropped = env.cr.fetchone()[0]
    if dropped:
        openupgrade.message(
            env.cr,
            "sale_purchase",
            "product.template",
            "service_tracking",
            "%d service products asked for a subcontracting RFQ in 19.0 but keep "
            "'no' as Create on Order in 20.0, because 20.0 refuses subcontracting "
            "together with a reinvoicing policy other than 'no' (see "
            "sale_purchase/models/product_template.py::_compute_service_tracking).",
            dropped,
        )


@openupgrade.migrate()
def migrate(env, version):
    subcontract_service_to_service_tracking(env)
