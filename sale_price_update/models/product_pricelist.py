from odoo import fields, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def _spu_weighing_enabled(self):
        """True si sale_stock_weighing está instalado y la empresa lo usa."""
        self.ensure_one()
        if "is_weighed_price" not in self.env["product.pricelist.item"]._fields:
            return False
        company = self.company_id or self.env.company
        return bool(getattr(company, "use_stock_weighing", False))

    def _spu_get_prices(self, products, date=None):
        """Precios vigentes de un lote de productos a la fecha dada.

        Devuelve {product_id: precio}. Usa _compute_price_rule en lote
        (una sola pasada del motor de precios); los productos pesables
        (sale_stock_weighing) se resuelven vía _get_product_price, que ese
        módulo sobreescribe para devolver $/unidad de peso.
        """
        self.ensure_one()
        if not products:
            return {}
        date = date or fields.Date.today()

        prices = {}
        weighed = products.browse()
        if self._spu_weighing_enabled():
            weighed = products.filtered(
                lambda p: getattr(p, "is_weighed_product", False)
            )
            for product in weighed:
                try:
                    prices[product.id] = self._get_product_price(
                        product, 1.0, date=date
                    )
                except Exception:
                    prices[product.id] = product.lst_price

        normal = products - weighed
        if normal:
            try:
                rules = self._compute_price_rule(normal, 1.0, date=date)
                prices.update(
                    {pid: price for pid, (price, _rule) in rules.items()}
                )
            except Exception:
                # Fallback defensivo ante cambios de firma entre versiones
                for product in normal:
                    try:
                        prices[product.id] = self._get_product_price(
                            product, 1.0, date=date
                        )
                    except Exception:
                        prices[product.id] = product.lst_price
        return prices
