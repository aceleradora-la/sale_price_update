from odoo import _, fields, models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    sale_price_update_note = fields.Text(
        "Nota — Actualización de Precio",
        help="Detalle del cambio aplicado desde el asistente de actualización de precios.",
    )

    def action_spu_view_history(self):
        """Abre el historial de cambios de precio para este producto en esta lista."""
        self.ensure_one()
        domain = [("pricelist_id", "=", self.pricelist_id.id)]
        title_product = ""
        if self.product_id:
            domain.append(("product_id", "=", self.product_id.id))
            title_product = self.product_id.display_name
        elif self.product_tmpl_id:
            variant_ids = self.product_tmpl_id.product_variant_ids.ids
            domain.append(("product_id", "in", variant_ids))
            title_product = self.product_tmpl_id.display_name
        return {
            "name": _("Historial de Precios — %s", title_product or self.pricelist_id.name),
            "type": "ir.actions.act_window",
            "res_model": "sale.price.update.history",
            "view_mode": "list,form",
            "domain": domain,
            "target": "new",
        }
