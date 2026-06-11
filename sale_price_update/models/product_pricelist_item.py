from odoo import fields, models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    sale_price_update_note = fields.Text(
        "Nota — Actualización de Precio",
        help="Detalle del cambio aplicado desde el asistente de actualización de precios.",
    )
