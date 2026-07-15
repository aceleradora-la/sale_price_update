from datetime import datetime, time as dtime, timedelta

import pytz

from odoo import _, api, fields, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    # ── Vista de precios vigentes / futuros ───────────────────────────
    spu_current_item_ids = fields.One2many(
        "product.pricelist.item",
        "pricelist_id",
        string="Precios Vigentes y Futuros",
        compute="_compute_spu_current_item_ids",
        help="Ítems de la lista cuyo precio sigue vigente o rige a futuro "
             "(sin fecha de vencimiento o con vencimiento posterior a hoy).",
    )

    def _compute_spu_current_item_ids(self):
        ftype = self.env["product.pricelist.item"]._fields["date_end"].type
        now = fields.Datetime.now()
        ref = now.date() if ftype == "date" else now
        for pricelist in self:
            pricelist.spu_current_item_ids = pricelist.item_ids.filtered(
                lambda i: not i.date_end or i.date_end >= ref
            )

    # ── Detección de pesaje ───────────────────────────────────────────
    def _spu_weighing_enabled(self):
        """True si sale_stock_weighing está instalado y la empresa lo usa."""
        self.ensure_one()
        if "is_weighed_price" not in self.env["product.pricelist.item"]._fields:
            return False
        company = self.company_id or self.env.company
        return bool(getattr(company, "use_stock_weighing", False))

    # ── Helpers de fecha/hora (Date del usuario → límites del ítem) ────
    def _spu_start_dt(self, date_value):
        """Inicio del día `date_value` en la zona del usuario, como datetime UTC naive."""
        tz = pytz.timezone(self.env.user.tz or "UTC")
        local = tz.localize(datetime.combine(date_value, dtime.min))
        return local.astimezone(pytz.utc).replace(tzinfo=None)

    def _spu_period_bounds(self, date_value):
        """Devuelve (nuevo_inicio, fin_anterior) con el tipo correcto según
        el campo date_start del ítem (datetime en Odoo 17+, date en versiones
        anteriores)."""
        ftype = self.env["product.pricelist.item"]._fields["date_start"].type
        if ftype == "datetime":
            start = self._spu_start_dt(date_value)
            prev_end = start - timedelta(seconds=1)
            return start, prev_end
        return date_value, date_value - timedelta(days=1)

    def _spu_coerce_dt(self, value):
        """Normaliza una fecha/fechahora/None a datetime comparable con los ítems."""
        if not value:
            return fields.Datetime.now()
        if isinstance(value, datetime):
            return value
        # date → inicio del día en zona del usuario
        return self._spu_start_dt(value)

    # ── Búsqueda del ítem más específico vigente ──────────────────────
    def _spu_best_item(self, items, product):
        """De un conjunto de ítems ya filtrados por vigencia, devuelve el que
        aplica al producto con mayor especificidad (variante > plantilla >
        categoría > global), y a igual especificidad el de mayor min_quantity
        y fecha de inicio más reciente."""
        tmpl = product.product_tmpl_id
        categ_ids = set()
        cat = product.categ_id
        while cat:
            categ_ids.add(cat.id)
            cat = cat.parent_id

        def rank(item):
            if item.applied_on == "0_product_variant" and item.product_id.id == product.id:
                return 3
            if item.applied_on == "1_product" and item.product_tmpl_id.id == tmpl.id:
                return 2
            if item.applied_on == "2_product_category" and item.categ_id.id in categ_ids:
                return 1
            if item.applied_on == "3_global":
                return 0
            return -1

        candidates = [(rank(i), i) for i in items]
        candidates = [(r, i) for r, i in candidates if r >= 0]
        if not candidates:
            return self.env["product.pricelist.item"]

        def sort_key(entry):
            r, item = entry
            start = item.date_start
            if start and hasattr(start, "timestamp"):
                start_ts = start.timestamp()
            elif start:
                start_ts = float(start.toordinal()) * 86400.0
            else:
                start_ts = 0.0
            return (r, item.min_quantity or 0.0, start_ts)

        candidates.sort(key=sort_key, reverse=True)
        return candidates[0][1]

    # ── Lectura de precios (directa de los ítems, sin fallback a maestro) ─
    def _spu_get_price_info(self, products, at_date=None):
        """Precio de cada producto en ESTA lista, leído de sus ítems vigentes
        a la fecha dada.

        Devuelve {product_id: {"price", "is_weighed", "uom_name", "has_item"}}.
        Si no hay ítem vigente para el producto, price=0 y has_item=False
        (no se cae al precio de venta del maestro, para no confundir).
        """
        self.ensure_one()
        if not products:
            return {}
        at_dt = self._spu_coerce_dt(at_date)
        weighing = self._spu_weighing_enabled()

        # Comparar con el mismo tipo que usan los campos del ítem.
        ftype = self.env["product.pricelist.item"]._fields["date_start"].type
        at_val = at_dt.date() if ftype == "date" else at_dt

        # Un solo pase sobre los ítems de la lista, filtrados por vigencia.
        in_force = self.item_ids.filtered(
            lambda i: (not i.date_start or i.date_start <= at_val)
            and (not i.date_end or i.date_end >= at_val)
        )

        info = {}
        for product in products:
            item = self._spu_best_item(in_force, product)
            if not item:
                info[product.id] = {
                    "price": 0.0, "is_weighed": False,
                    "uom_name": "", "has_item": False,
                }
                continue
            is_weighed = bool(
                weighing and getattr(item, "is_weighed_price", False)
            )
            if is_weighed:
                price = item.price_per_weight
            elif item.compute_price == "fixed":
                price = item.fixed_price
            else:
                # fórmula/descuento: dejar que el motor lo calcule
                try:
                    price = self._get_product_price(product, 1.0, date=at_dt)
                except Exception:
                    price = item.fixed_price
            uom_name = ""
            if is_weighed:
                wuom = getattr(product, "weighing_uom_id", False)
                uom_name = wuom.name if wuom else "kg"
            info[product.id] = {
                "price": price, "is_weighed": is_weighed,
                "uom_name": uom_name, "has_item": True,
            }
        return info

    def _spu_get_prices(self, products, date=None):
        """Compatibilidad: {product_id: precio} leído de los ítems vigentes."""
        info = self._spu_get_price_info(products, at_date=date)
        return {pid: d["price"] for pid, d in info.items()}

    # ── Abrir el asistente de actualización con esta lista ya elegida ──
    def action_spu_open_price_update(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Actualizar Precios de Venta"),
            "res_model": "sale.price.update.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_pricelist_ids": [(6, 0, self.ids)],
            },
        }
