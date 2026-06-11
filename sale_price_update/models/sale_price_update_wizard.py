from datetime import timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class SalePriceUpdateWizard(models.TransientModel):
    """
    Wizard para actualización masiva de precios de venta.
    Permite filtrar por categoría o selección de productos,
    definir un % de aumento global o por producto, y previsualizar
    el cambio antes de aplicarlo en una o varias listas de precios.
    """

    _name = "sale.price.update.wizard"
    _description = "Asistente de Actualización de Precios de Venta"

    # ── Configuración principal ───────────────────────────────────────
    pricelist_ids = fields.Many2many(
        "product.pricelist",
        "sale_price_update_wiz_pricelist_rel",
        "wizard_id",
        "pricelist_id",
        string="Listas de Precios",
        required=True,
    )
    increase_percent = fields.Float(
        "% Aumento Global",
        digits=(5, 2),
        default=0.0,
        help="Porcentaje de aumento global. Puede sobreescribirse por producto en la tabla.",
    )
    price_date_start = fields.Date(
        "Vigencia desde",
        default=fields.Date.today,
        required=True,
    )

    # ── Filtros ───────────────────────────────────────────────────────
    filter_categ_id = fields.Many2one(
        "product.category",
        string="Filtrar por Categoría",
        help="Filtra los productos a mostrar. Incluye subcategorías.",
    )

    # ── Líneas de productos ───────────────────────────────────────────
    line_ids = fields.One2many(
        "sale.price.update.wizard.line",
        "wizard_id",
        string="Productos",
    )

    # ── Helpers computados ────────────────────────────────────────────
    line_count = fields.Integer("Productos cargados", compute="_compute_line_count")
    selected_count = fields.Integer("Seleccionados", compute="_compute_line_count")

    @api.depends("line_ids", "line_ids.apply")
    def _compute_line_count(self):
        for wiz in self:
            wiz.line_count = len(wiz.line_ids)
            wiz.selected_count = len(wiz.line_ids.filtered("apply"))

    # ── Construcción de líneas (compartido por onchange y botón) ──────
    def _get_products_domain(self):
        """Dominio de productos según filtro de categoría y contexto."""
        # Si el wizard fue abierto con productos preseleccionados desde la
        # lista de productos, ese conjunto manda.
        active_ids = self.env.context.get("active_ids") or []
        active_model = self.env.context.get("active_model") or ""
        if active_ids and active_model == "product.product":
            domain = [("id", "in", active_ids)]
            if self.filter_categ_id:
                domain.append(("categ_id", "child_of", self.filter_categ_id.id))
            return domain
        if active_ids and active_model == "product.template":
            domain = [("product_tmpl_id", "in", active_ids), ("active", "=", True)]
            if self.filter_categ_id:
                domain.append(("categ_id", "child_of", self.filter_categ_id.id))
            return domain

        domain = [("sale_ok", "=", True), ("active", "=", True)]
        if self.filter_categ_id:
            domain.append(("categ_id", "child_of", self.filter_categ_id.id))
        return domain

    def _get_pricelist_prices(self, products, pricelist):
        """Precios vigentes de un lote de productos en la lista dada.

        Usa _compute_price_rule (una sola pasada del motor de precios para
        todos los productos) en vez de resolver producto por producto.
        Resuelve cualquier tipo de regla: fija, fórmula, descuento, por
        plantilla o categoría. Devuelve {product_id: precio}.
        """
        if not products:
            return {}
        if not pricelist:
            return {p.id: p.lst_price for p in products}
        try:
            rules = pricelist._compute_price_rule(
                products, 1.0, date=fields.Date.today()
            )
            return {pid: price for pid, (price, _rule) in rules.items()}
        except Exception:
            # Fallback defensivo ante cambios de firma entre versiones
            prices = {}
            for product in products:
                try:
                    prices[product.id] = pricelist._get_product_price(
                        product, 1.0, date=fields.Date.today()
                    )
                except Exception:
                    prices[product.id] = product.lst_price
            return prices

    def _get_current_pricelist_price(self, product, pricelist):
        """Precio vigente de un solo producto (wrapper del batch)."""
        return self._get_pricelist_prices(product, pricelist).get(
            product.id, product.lst_price
        )

    def _build_line_commands(self):
        """Arma los comandos One2many para recrear las líneas en memoria.

        No escribe en la base: apto para usarse dentro de @api.onchange.
        """
        products = self.env["product.product"].search(
            self._get_products_domain(), order="categ_id, default_code, name"
        )
        ref_pricelist = self.pricelist_ids[:1]
        pct = self.increase_percent or 0.0
        prices = self._get_pricelist_prices(products, ref_pricelist)

        commands = [Command.clear()]
        for product in products:
            current_price = prices.get(product.id, product.lst_price)
            commands.append(Command.create({
                "product_id": product.id,
                "categ_id": product.categ_id.id,
                "current_price": current_price,
                "increase_percent": 0.0,
                "new_price": current_price * (1.0 + pct / 100.0),
                "apply": True,
            }))
        return commands

    # ── Onchanges: solo memoria, nunca create/unlink reales ──────────
    @api.onchange("pricelist_ids", "filter_categ_id")
    def _onchange_reload_lines(self):
        """Recarga las líneas cuando cambia la lista de referencia o el filtro."""
        if self.pricelist_ids:
            self.line_ids = self._build_line_commands()
        else:
            self.line_ids = [Command.clear()]

    @api.onchange("increase_percent")
    def _onchange_increase_percent(self):
        """Propaga el % global a las líneas sin % propio."""
        for line in self.line_ids:
            if not line.increase_percent:
                line.new_price = line.current_price * (
                    1.0 + (self.increase_percent or 0.0) / 100.0
                )

    # ── Botones auxiliares ────────────────────────────────────────────
    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }

    def action_load_products(self):
        """Recarga las líneas (botón, opera sobre registro real)."""
        self.ensure_one()
        self.line_ids.unlink()
        self.write({"line_ids": self._build_line_commands()[1:]})  # sin el clear
        return self._reopen()

    def action_select_all(self):
        self.line_ids.write({"apply": True})
        return self._reopen()

    def action_deselect_all(self):
        self.line_ids.write({"apply": False})
        return self._reopen()

    def action_view_history(self):
        return {
            "name": _("Historial de Actualización de Precios"),
            "type": "ir.actions.act_window",
            "res_model": "sale.price.update.history",
            "view_mode": "tree,form",
            "target": "current",
        }

    # ── Aplicar precios ───────────────────────────────────────────────
    def action_apply_prices(self):
        self.ensure_one()
        if not self.pricelist_ids:
            raise UserError(_("Seleccioná al menos una lista de precios."))
        if not self.price_date_start:
            raise UserError(_("Indicá la fecha de vigencia."))

        lines_to_apply = self.line_ids.filtered(
            lambda l: l.apply and l.product_id and l.new_price > 0
        )
        if not lines_to_apply:
            raise UserError(_("No hay productos seleccionados con precio calculado."))
        if self.line_ids.filtered(lambda l: l.apply and not l.product_id):
            raise UserError(_(
                "Hay líneas sin producto (posible problema al guardar el wizard). "
                "Cerrá el asistente y volvé a abrirlo."
            ))

        PricelistItem = self.env["product.pricelist.item"]
        # sudo: el vendedor tiene solo lectura sobre el historial, pero el
        # registro de auditoría debe crearse siempre.
        History = self.env["sale.price.update.history"].sudo()
        date_start = self.price_date_start
        date_end_prev = date_start - timedelta(days=1)

        ref_pricelist = self.pricelist_ids[:1]
        applied_count = 0
        for pricelist in self.pricelist_ids:
            currency = pricelist.currency_id
            # Precios vigentes de esta lista en lote (solo listas secundarias;
            # la de referencia usa los precios ya previsualizados en pantalla)
            list_prices = {}
            if pricelist != ref_pricelist:
                list_prices = self._get_pricelist_prices(
                    lines_to_apply.mapped("product_id"), pricelist
                )
            for line in lines_to_apply:
                # % efectivo de la línea: si el usuario editó el precio nuevo
                # a mano, se deriva del cambio real; si no, el % cargado.
                if line.current_price:
                    effective_pct = (
                        line.new_price / line.current_price - 1.0
                    ) * 100.0
                else:
                    effective_pct = (
                        line.increase_percent or self.increase_percent or 0.0
                    )

                # Cada lista parte de SU propio precio vigente (puede diferir
                # en moneda y valor de la lista de referencia que se muestra
                # en pantalla). A la lista de referencia se le aplica el precio
                # tal cual fue previsualizado.
                if pricelist == ref_pricelist:
                    old_price = line.current_price
                    new_price = line.new_price
                else:
                    old_price = list_prices.get(
                        line.product_id.id, line.product_id.lst_price
                    )
                    if old_price:
                        new_price = old_price * (1.0 + effective_pct / 100.0)
                    else:
                        new_price = line.new_price
                new_price = currency.round(new_price)

                # Vencer ítems fijos vigentes para este producto en esta lista
                existing = PricelistItem.search([
                    ("pricelist_id", "=", pricelist.id),
                    ("product_id", "=", line.product_id.id),
                    ("compute_price", "=", "fixed"),
                    "|", ("date_end", "=", False), ("date_end", ">=", date_start),
                ])
                for item in existing:
                    item_start = item.date_start
                    if item_start and hasattr(item_start, "date"):
                        item_start = item_start.date()
                    if item_start and item_start >= date_end_prev:
                        item.unlink()
                    else:
                        item.write({"date_end": date_end_prev})

                note = "Aumento %.2f%% | Anterior: %.2f %s | Nuevo: %.2f %s | Lista: %s" % (
                    effective_pct,
                    old_price,
                    currency.name,
                    new_price,
                    currency.name,
                    pricelist.name,
                )

                PricelistItem.create({
                    "pricelist_id": pricelist.id,
                    "product_id": line.product_id.id,
                    "applied_on": "0_product_variant",
                    "compute_price": "fixed",
                    "fixed_price": new_price,
                    "date_start": date_start,
                    "date_end": False,
                    "sale_price_update_note": note,
                })

                History.create({
                    "pricelist_id": pricelist.id,
                    "product_id": line.product_id.id,
                    "categ_id": line.categ_id.id,
                    "date_applied": date_start,
                    "currency_id": currency.id,
                    "old_price": old_price,
                    "increase_percent": effective_pct,
                    "new_price": new_price,
                    "user_id": self.env.uid,
                    "note": note,
                })
                applied_count += 1

        pricelist_names = ", ".join(self.pricelist_ids.mapped("name"))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Precios actualizados"),
                "message": _(
                    "%d precios aplicados en: %s — vigencia desde %s."
                ) % (applied_count, pricelist_names, date_start.strftime("%d/%m/%Y")),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }


class SalePriceUpdateWizardLine(models.TransientModel):
    """Una fila por producto en el wizard de actualización de precios."""

    _name = "sale.price.update.wizard.line"
    _description = "Línea — Asistente Actualización de Precios"
    _order = "categ_id, product_id"

    wizard_id = fields.Many2one("sale.price.update.wizard", ondelete="cascade")
    apply = fields.Boolean("Aplicar", default=True)
    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    categ_id = fields.Many2one("product.category", string="Categoría", readonly=True)
    currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_currency_id",
        string="Moneda",
    )
    current_price = fields.Monetary("Precio Actual", currency_field="currency_id", readonly=True)
    increase_percent = fields.Float(
        "% Aumento",
        digits=(5, 2),
        help="Deja en 0 para usar el % global del wizard.",
    )
    new_price = fields.Monetary(
        "Precio Nuevo",
        currency_field="currency_id",
        help="Editable manualmente. Se recalcula si cambia el % de aumento.",
    )
    diff_amount = fields.Monetary(
        "Diferencia",
        currency_field="currency_id",
        compute="_compute_diff",
    )
    diff_percent_display = fields.Char(
        "Δ%",
        compute="_compute_diff",
    )

    @api.depends("wizard_id.pricelist_ids")
    def _compute_currency_id(self):
        for line in self:
            pricelist = line.wizard_id.pricelist_ids[:1]
            line.currency_id = (
                pricelist.currency_id if pricelist else self.env.company.currency_id
            )

    @api.depends("new_price", "current_price")
    def _compute_diff(self):
        for line in self:
            line.diff_amount = (line.new_price or 0.0) - (line.current_price or 0.0)
            if line.current_price:
                pct = (
                    ((line.new_price or 0.0) - line.current_price)
                    / line.current_price * 100
                )
                line.diff_percent_display = "%+.2f%%" % pct
            else:
                line.diff_percent_display = "—"

    @api.onchange("increase_percent")
    def _onchange_increase_percent(self):
        for line in self:
            pct = line.increase_percent or line.wizard_id.increase_percent or 0.0
            line.new_price = (line.current_price or 0.0) * (1.0 + pct / 100.0)
