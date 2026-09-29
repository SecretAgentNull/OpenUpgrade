env = locals().get("env")

partner = env["res.partner"].create({"name": "OpenUpgrade test customer"})
employee = env["hr.employee"].create(
    {"name": "OpenUpgrade test employee", "company_id": env.company.id}
)
product = env["product.product"].create(
    {
        "name": "OpenUpgrade test timesheet service",
        "type": "service",
        "service_type": "timesheet",
        "invoice_policy": "delivery",
        "list_price": 50.0,
    }
)
project = env["project.project"].create(
    {
        "name": "OpenUpgrade migration project",
        "partner_id": partner.id,
        "allow_billable": True,
    }
)
task = env["project.task"].create(
    {"name": "OpenUpgrade migration task", "project_id": project.id}
)
order = env["sale.order"].create(
    {
        "partner_id": partner.id,
        "order_line": [
            (
                0,
                0,
                {
                    "product_id": product.id,
                    "name": product.name,
                    "product_uom_qty": 1.0,
                    "product_uom_id": product.uom_id.id,
                    "price_unit": 50.0,
                },
            )
        ],
    }
)
order.action_confirm()
timesheet = env["account.analytic.line"].create(
    {
        "name": "OpenUpgrade timesheet entry",
        "project_id": project.id,
        "task_id": task.id,
        "employee_id": employee.id,
        "unit_amount": 2.0,
        "so_line": order.order_line.id,
    }
)

# 19.0 stores the invoice link of a timesheet in `timesheet_invoice_id`, which
# 20.0 renames to `reinvoice_move_id` (and moves to the `sale` module)
invoice = order._create_invoices(final=True)
if not timesheet.timesheet_invoice_id and invoice:
    timesheet.sudo().timesheet_invoice_id = invoice.id

env.cr.commit()
