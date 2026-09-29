env = locals().get("env")

# res.company#security_lead is a Float in 19.0 and an Integer in 20.0
env.company.security_lead = 1.5

# `Default Shipping Policy` is an ir.default on sale.order in 19.0 and a
# res.company#picking_policy field in 20.0
env["ir.default"].set("sale.order", "picking_policy", "one", company_id=env.company.id)

# a user level default that must survive as an ir.default
env["ir.default"].set(
    "sale.order",
    "picking_policy",
    "direct",
    user_id=env.ref("base.user_admin").id,
    company_id=env.company.id,
)

# a storable product delivered through a picking, so stock.picking#sale_id has a
# value to keep. The picking is created directly instead of confirming the order:
# confirming would run the procurement group, which needs demo route data.
storable = env["product.product"].create(
    {
        "name": "OpenUpgrade test storable",
        "type": "consu",
        "is_storable": True,
        "list_price": 10.0,
    }
)
order = env["sale.order"].create(
    {
        "partner_id": env.company.partner_id.id,
        "order_line": [
            (
                0,
                0,
                {
                    "product_id": storable.id,
                    "name": storable.name,
                    "product_uom_qty": 2.0,
                    "product_uom_id": storable.uom_id.id,
                    "price_unit": 10.0,
                },
            )
        ],
    }
)
line = order.order_line
warehouse = env["stock.warehouse"].search(
    [("company_id", "=", env.company.id)], limit=1
)
shipping = order.partner_shipping_id
env["stock.picking"].create(
    {
        "picking_type_id": warehouse.out_type_id.id,
        "location_id": warehouse.lot_stock_id.id,
        "location_dest_id": warehouse.out_type_id.default_location_dest_id.id,
        "move_ids": [
            (
                0,
                0,
                {
                    "product_id": storable.id,
                    "product_uom_qty": 2.0,
                    "location_id": warehouse.lot_stock_id.id,
                    "location_dest_id": shipping.property_stock_customer.id,
                    "sale_line_id": line.id,
                },
            )
        ],
    }
)

env.cr.commit()
