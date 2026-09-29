# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_renamed_fields = [
    # same model, same table, same selection keys (no/cost/sales_price):
    # only the name changed in 20.0.
    ("product.template", "product_template", "expense_policy", "reinvoice_policy"),
    # 19.0 declares the invoice link of an analytic line on sale_timesheet, 20.0
    # declares it on sale as reinvoice_move_id. The rename has to happen here:
    # sale is upgraded before sale_timesheet, and its own _auto_init would create
    # an empty reinvoice_move_id column next to the populated old one otherwise.
    (
        "account.analytic.line",
        "account_analytic_line",
        "timesheet_invoice_id",
        "reinvoice_move_id",
    ),
]

# NOTHING TO DO for the fields that 20.0 drops without a successor
# (sale.order#require_payment, sale.order#amount_undiscounted and the non stored
# show_update_fpos / show_update_pricelist): openupgrade_framework never drops
# columns, so the values stay available for third party code and nothing breaks,
# because none of those columns carries a NOT NULL constraint.


def _column_data_type(cr, table, column):
    cr.execute(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    row = cr.fetchone()
    return row and row[0]


def convert_customer_lead_to_integer(env):
    """sale.order.line#customer_lead is an Integer (a number of days) in 20.0.

    Round up: a fractional lead time that is truncated could promise a delivery
    date that is too early for an existing line.
    """
    table, column = "sale_order_line", "customer_lead"
    if not openupgrade.column_exists(env.cr, table, column):
        return
    if _column_data_type(env.cr, table, column) == "integer":
        return
    openupgrade.logged_query(
        env.cr,
        f"""
        ALTER TABLE {table}
        ALTER COLUMN {column} TYPE integer
        USING CASE
            WHEN {column} IS NULL THEN NULL
            ELSE CEIL({column})::integer
        END
        """,
    )


def archive_product_sale_delay(env):
    """product.template#sale_delay became company dependent, so its column turns
    from int4 into jsonb. Postgres cannot cast an integer to jsonb, and the value
    has to be keyed by company id anyway, so move the old global value aside and
    let the ORM create a clean column. post-migration fills it in.

    In 19.0 the field is owned by the `stock` module, in 20.0 by `sale`, but this
    script is safe in either upgrade order: `stock` 2.0 no longer declares the
    field, so nobody writes the column between the two module loads.
    """
    if openupgrade.column_exists(env.cr, "product_template", "sale_delay"):
        openupgrade.rename_columns(env.cr, {"product_template": [("sale_delay", None)]})


def drop_obsolete_actions(env):
    """Delete the 19.0 actions that 20.0 redeclares under the same external id but
    as another kind of action.

    ``sale.action_accrued_revenue_entry_sale_order_line`` opens the accrual wizard
    through an ir.actions.act_window in 19.0; 20.0 makes it an ir.actions.server
    that calls ``sale.order.line.action_open_accrual_wizard()``, like purchase
    already does for its expense entry. Imports match records on the external id
    only, and the loader stops on "found record of different model
    ir.actions.act_window" when it then has to create the server action, which
    aborts the whole module.
    """
    openupgrade.delete_records_safely_by_xml_id(
        env, ["sale.action_accrued_revenue_entry_sale_order_line"]
    )
    openupgrade.message(
        env.cr,
        "sale",
        "ir.actions.act_window",
        False,
        "Deleted the 19.0 ir.actions.act_window "
        "sale.action_accrued_revenue_entry_sale_order_line: 20.0 uses that external "
        "id for an ir.actions.server on sale.order.line, and the two cannot coexist.",
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _renamed_fields)
    convert_customer_lead_to_integer(env)
    archive_product_sale_delay(env)
    drop_obsolete_actions(env)
