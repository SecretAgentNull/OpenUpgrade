env = locals().get("env")

vendor = env["res.partner"].create({"name": "OpenUpgrade test vendor"})

# `service_to_purchase` is company dependent in 19.0, so it is stored as a jsonb
# column keyed by company id. 20.0 folds it into the `service_tracking` selection.
subcontracted = env["product.template"].create(
    {
        "name": "OpenUpgrade test subcontracted service",
        "type": "service",
        "expense_policy": "no",
        "service_tracking": "no",
        "purchase_ok": False,
        "service_to_purchase": True,
        "seller_ids": [
            (0, 0, {"partner_id": vendor.id, "min_qty": 1.0, "price": 10.0})
        ],
    }
)

# 20.0 only allows 'subcontract' together with `reinvoice_policy == 'no'`, so a
# re-invoiced service keeps 'no' and the script has to report it instead
not_subcontractable = env["product.template"].create(
    {
        "name": "OpenUpgrade test reinvoiced service",
        "type": "service",
        "expense_policy": "cost",
        "service_tracking": "no",
        "service_to_purchase": True,
        "seller_ids": [
            (0, 0, {"partner_id": vendor.id, "min_qty": 1.0, "price": 10.0})
        ],
    }
)

env.cr.commit()
