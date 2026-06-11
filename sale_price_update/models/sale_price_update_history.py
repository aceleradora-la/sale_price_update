from odoo import fields, models


class SalePriceUpdateHistory(models.Model):
    """Historial permanente de actualizaciones de precios de venta."""

    _name = "sale.price.update.history"
    _description = "Historial de Actualización de Precios de Venta"
    _order = "date_applied desc, id desc"
    _rec_name = "product_id"

    pricelist_id = fields.Many2one("product.pricelist", string="Lista de Precios", readonly=True, index=True)
    product_id = fields.Many2one("product.product", string="Producto", readonly=True, index=True)
    categ_id = fields.Many2one("product.category", string="Categoría", readonly=True, index=True)
    date_applied = fields.Date("Vigencia desde", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Moneda", readonly=True)
    old_price = fields.Monetary("Precio Anterior", currency_field="currency_id", readonly=True)
    increase_percent = fields.Float("% Aumento", digits=(5, 2), readonly=True)
    new_price = fields.Monetary("Precio Nuevo", currency_field="currency_id", readonly=True)
    user_id = fields.Many2one("res.users", string="Aplicado por", readonly=True)
    note = fields.Text("Detalle", readonly=True)
