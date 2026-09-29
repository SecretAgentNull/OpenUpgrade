# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""20.0 drops the 'inside' value of product.document#attached_on_sale, which in
19.0 embedded the PDF in the quotation report.

'quotation' is the closest successor: the document keeps reaching the customer, and
20.0 still stitches the PDFs of quote visible documents into the report (see
ir_actions_report.py::_get_product_documents_before_and_after_quote). This runs
before the registry is rebuilt, so no read ever sees the obsolete value.
"""

from openupgradelib import openupgrade


def remap_attached_inside_documents(env):
    if not openupgrade.column_exists(env.cr, "product_document", "attached_on_sale"):
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE product_document
        SET attached_on_sale = 'quotation'
        WHERE attached_on_sale = 'inside'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    remap_attached_inside_documents(env)
