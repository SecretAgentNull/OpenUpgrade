# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

# NOTHING TO DO for `account.analytic.line#timesheet_invoice_type`: 20.0 replaces
# it with the generic stored compute `billable_type`, which has no init_storage,
# so the ORM recomputes every row from so_line / product / project during
# registry init. The old column keeps its values for third party code.
#
# NOTHING TO DO for `so_line`, `order_id`, `allow_billable`, `sale_order_state`,
# `is_so_line_edited`, `commercial_partner_id`: same names, same tables, already
# populated in 19.0 (declared with `init_storage=lambda model: None` in 20.0).
#
# NOTHING TO DO for `account.analytic.line#reinvoice_move_id`: the column rename
# from `timesheet_invoice_id` is done by sale/pre-migration.py, because `sale`
# (20.0) declares the field while `sale_timesheet` (19.0) owned it, and `sale`
# is loaded first.


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "sale_timesheet", "20.0.1.0/noupdate_changes.xml")
