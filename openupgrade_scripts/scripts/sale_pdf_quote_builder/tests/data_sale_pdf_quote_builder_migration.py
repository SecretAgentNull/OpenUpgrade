from base64 import b64encode
from io import BytesIO

from reportlab.pdfgen import canvas

env = locals().get("env")

# sale_pdf_quote_builder parses the file with PyPDF2 on write, so the fixture has
# to hold a real pdf and not just a %PDF header
_buffer = BytesIO()
_page = canvas.Canvas(_buffer)
_page.drawString(72, 720, "OpenUpgrade migration fixture")
_page.showPage()
_page.save()
pdf_data = b64encode(_buffer.getvalue())

product = env["product.product"].create(
    {"name": "OpenUpgrade test documented product", "type": "consu", "list_price": 5.0}
)
attachment = env["ir.attachment"].create(
    {"name": "OpenUpgrade inside document", "datas": pdf_data}
)
env["product.document"].create(
    {
        "name": "OpenUpgrade inside document",
        "ir_attachment_id": attachment.id,
        "res_model": "product.product",
        "res_id": product.id,
        # 'inside' is dropped in 20.0: the value has to become 'quotation', the
        # option that still embeds the file in the quote pdf
        "attached_on_sale": "inside",
    }
)

env.cr.commit()
