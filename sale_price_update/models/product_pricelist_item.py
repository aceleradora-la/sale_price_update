from odoo import _, api, fields, models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    sale_price_update_note = fields.Text(
        "Nota — Actualización de Precio",
        help="Detalle del cambio aplicado desde el asistente de actualización de precios.",
    )

    spu_price_display = fields.Char(
        "Precio",
        compute="_compute_spu_price_display",
        help="Precio legible del ítem: por kg si es precio por peso, importe "
             "fijo, o la descripción de la fórmula/descuento.",
    )

    @api.depends(
        "compute_price", "fixed_price", "price_discount", "price_surcharge",
    )
    def _compute_spu_price_display(self):
        for item in self:
            # Pesable (sale_stock_weighing): reutiliza su display si existe.
            if getattr(item, "is_weighed_price", False):
                wdisp = getattr(item, "weight_price_display", False)
                if wdisp:
                    item.spu_price_display = wdisp
                    continue
                uom = getattr(item, "weighing_uom_name", "") or "kg"
                ppw = getattr(item, "price_per_weight", 0.0) or 0.0
                item.spu_price_display = "%.2f / %s" % (ppw, uom)
                continue
            if item.compute_price == "fixed":
                item.spu_price_display = "%.2f" % (item.fixed_price or 0.0)
                continue
            # Fórmula/descuento normal: usar el texto estándar de Odoo.
            item.spu_price_display = item.price or ""

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
