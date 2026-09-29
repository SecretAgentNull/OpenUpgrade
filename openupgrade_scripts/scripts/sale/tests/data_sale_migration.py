env = locals().get("env")

# 19.0 stored the automatic invoicing switch in a global config parameter
env["ir.config_parameter"].set_param("sale.automatic_invoice", "True")

# ... and the default invoicing policy as an ir.default on product.template
env["ir.default"].set(
    "product.template", "invoice_policy", "delivery", company_id=env.company.id
)

# a product carrying the values that 20.0 renames / reshapes
product = env["product.product"].create(
    {
        "name": "OpenUpgrade test service",
        "type": "service",
        "expense_policy": "cost",
        "sale_delay": 3,
    }
)

# an order with a fractional customer lead (2.5 days) and a delivered line
partner = env["res.partner"].create({"name": "OpenUpgrade test customer"})
order = env["sale.order"].create(
    {
        "partner_id": partner.id,
        "order_line": [
            (
                0,
                0,
                {
                    "product_id": product.id,
                    "product_uom_qty": 2,
                    "product_uom_id": product.uom_id.id,
                    "price_unit": 100.0,
                    "customer_lead": 2.5,
                },
            )
        ],
    }
)
order.action_confirm()
# leave it confirmed: 20.0 must not recompute customer_lead on the existing line

env.cr.commit()
