from datetime import timedelta

from odoo import _, api, fields, models
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

    # ── Pricelist detalle (preview por lista) ─────────────────────────
    pricelist_preview_ids = fields.One2many(
        "sale.price.update.wizard.pricelist",
        "wizard_id",
        string="Preview por Lista",
    )

    # ── Helpers computados ────────────────────────────────────────────
    line_count = fields.Integer("Productos cargados", compute="_compute_line_count")
    selected_count = fields.Integer("Seleccionados", compute="_compute_line_count")

    @api.depends("line_ids", "line_ids.apply")
    def _compute_line_count(self):
        for wiz in self:
            wiz.line_count = len(wiz.line_ids)
            wiz.selected_count = len(wiz.line_ids.filtered("apply"))

    # ── Carga de productos ────────────────────────────────────────────
    def action_load_products(self):
        """Carga/recarga los productos según el filtro de categoría activo."""
        self.ensure_one()
        domain = [
            ("sale_ok", "=", True),
            ("active", "=", True),
        ]
        if self.filter_categ_id:
            categ_ids = self._get_categ_and_children(self.filter_categ_id)
            domain.append(("categ_id", "in", categ_ids))

        # Contexto: si el wizard fue abierto con productos preseleccionados
        active_ids = self.env.context.get("active_ids") or []
        active_model = self.env.context.get("active_model") or ""
        if active_ids and active_model == "product.product":
            domain = [("id", "in", active_ids)]
        elif active_ids and active_model == "product.template":
            products = self.env["product.product"].search([
                ("product_tmpl_id", "in", active_ids),
                ("active", "=", True),
            ])
            domain = [("id", "in", products.ids)]

        products = self.env["product.product"].search(domain, order="categ_id, name")

        # Obtener precio actual de la primera lista seleccionada (referencia)
        ref_pricelist = self.pricelist_ids[:1]

        lines_vals = []
        for product in products:
            current_price = self._get_current_pricelist_price(product, ref_pricelist)
            lines_vals.append({
                "wizard_id": self.id,
                "product_id": product.id,
                "categ_id": product.categ_id.id,
                "current_price": current_price,
                "increase_percent": 0.0,
                "apply": True,
            })

        self.line_ids.unlink()
        if lines_vals:
            self.env["sale.price.update.wizard.line"].create(lines_vals)

        return self._reopen()

    def _get_categ_and_children(self, categ):
        """Retorna IDs de la categoría y todas sus subcategorías recursivamente."""
        result = categ.ids
        children = self.env["product.category"].search([("parent_id", "child_of", categ.id)])
        result += children.ids
        return list(set(result))

    def _get_current_pricelist_price(self, product, pricelist):
        """Obtiene el precio vigente del producto en la lista dada."""
        if not pricelist:
            return product.lst_price
        # Buscar ítem fixed vigente
        today = fields.Date.today()
        item = self.env["product.pricelist.item"].search([
            ("pricelist_id", "=", pricelist.id),
            ("product_id", "=", product.id),
            ("compute_price", "=", "fixed"),
            "|", ("date_start", "=", False), ("date_start", "<=", today),
            "|", ("date_end", "=", False), ("date_end", ">=", today),
        ], limit=1, order="date_start desc")
        if item:
            return item.fixed_price
        return product.lst_price

    # ── Propagación del % global ──────────────────────────────────────
    @api.onchange("increase_percent")
    def _onchange_increase_percent(self):
        for line in self.line_ids.filtered("apply"):
            if not line.increase_percent:
                line._recompute_new_price(self.increase_percent)

    @api.onchange("filter_categ_id")
    def _onchange_filter_categ_id(self):
        if self.pricelist_ids:
            return self.action_load_products()

    @api.onchange("pricelist_ids")
    def _onchange_pricelist_ids(self):
        if self.pricelist_ids and not self.line_ids:
            return self.action_load_products()
        # Recalcular precio actual con la nueva lista de referencia
        ref_pricelist = self.pricelist_ids[:1]
        for line in self.line_ids:
            line.current_price = self._get_current_pricelist_price(line.product_id, ref_pricelist)
            line._recompute_new_price(line.increase_percent or self.increase_percent)

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }

    # ── Selección masiva ──────────────────────────────────────────────
    def action_select_all(self):
        self.line_ids.write({"apply": True})
        return self._reopen()

    def action_deselect_all(self):
        self.line_ids.write({"apply": False})
        return self._reopen()

    # ── Historial ─────────────────────────────────────────────────────
    def action_view_history(self):
        return {
            "name": _("Historial de Actualización de Precios"),
            "type": "ir.actions.act_window",
            "res_model": "sale.price.update.history",
            "view_mode": "list,form",
            "target": "current",
        }

    # ── Aplicar precios ───────────────────────────────────────────────
    def action_apply_prices(self):
        self.ensure_one()
        if not self.pricelist_ids:
            raise UserError(_("Seleccioná al menos una lista de precios."))
        if not self.price_date_start:
            raise UserError(_("Indicá la fecha de vigencia."))

        lines_to_apply = self.line_ids.filtered(lambda l: l.apply and l.new_price > 0)
        if not lines_to_apply:
            raise UserError(_("No hay productos seleccionados con precio calculado."))

        PricelistItem = self.env["product.pricelist.item"]
        History = self.env["sale.price.update.history"]
        date_start = self.price_date_start
        date_end_prev = date_start - timedelta(days=1)

        applied_count = 0
        for pricelist in self.pricelist_ids:
            currency = pricelist.currency_id
            for line in lines_to_apply:
                pct = line.increase_percent if line.increase_percent else self.increase_percent

                # Vencer ítems vigentes existentes
                existing = PricelistItem.search([
                    ("pricelist_id", "=", pricelist.id),
                    ("product_id", "=", line.product_id.id),
                    ("compute_price", "=", "fixed"),
                    "|", ("date_end", "=", False), ("date_end", ">=", date_start),
                ])
                for item in existing:
                    item_start = item.date_start
                    if item_start and item_start >= date_end_prev:
                        item.unlink()
                    else:
                        item.write({"date_end": date_end_prev})

                note = "Aumento %.2f%% | Anterior: %.2f %s | Nuevo: %.2f %s | Lista: %s" % (
                    pct,
                    line.current_price,
                    currency.name,
                    line.new_price,
                    currency.name,
                    pricelist.name,
                )

                PricelistItem.create({
                    "pricelist_id": pricelist.id,
                    "product_id": line.product_id.id,
                    "applied_on": "0_product_variant",
                    "compute_price": "fixed",
                    "fixed_price": line.new_price,
                    "date_start": date_start,
                    "date_end": False,
                })

                History.create({
                    "pricelist_id": pricelist.id,
                    "product_id": line.product_id.id,
                    "categ_id": line.categ_id.id,
                    "date_applied": date_start,
                    "currency_id": currency.id,
                    "old_price": line.current_price,
                    "increase_percent": pct,
                    "new_price": line.new_price,
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
        store=True,
    )
    diff_percent_display = fields.Char(
        "Δ%",
        compute="_compute_diff",
        store=True,
    )

    @api.depends("wizard_id.pricelist_ids")
    def _compute_currency_id(self):
        for line in self:
            pricelist = line.wizard_id.pricelist_ids[:1]
            line.currency_id = pricelist.currency_id if pricelist else self.env.company.currency_id

    @api.depends("new_price", "current_price")
    def _compute_diff(self):
        for line in self:
            line.diff_amount = line.new_price - line.current_price
            if line.current_price:
                pct = (line.new_price - line.current_price) / line.current_price * 100
                line.diff_percent_display = "%+.2f%%" % pct
            else:
                line.diff_percent_display = "—"

    @api.onchange("increase_percent")
    def _onchange_increase_percent(self):
        for line in self:
            pct = line.increase_percent or line.wizard_id.increase_percent
            line.new_price = line.current_price * (1.0 + pct / 100.0)

    def _recompute_new_price(self, pct):
        self.new_price = self.current_price * (1.0 + pct / 100.0)


class SalePriceUpdateWizardPricelist(models.TransientModel):
    """Preview de precio nuevo por lista de precios (uso informativo)."""

    _name = "sale.price.update.wizard.pricelist"
    _description = "Preview por Lista — Asistente Actualización de Precios"
    _order = "pricelist_id, product_id"

    wizard_id = fields.Many2one("sale.price.update.wizard", ondelete="cascade")
    pricelist_id = fields.Many2one("product.pricelist", string="Lista", readonly=True)
    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    currency_id = fields.Many2one("res.currency", related="pricelist_id.currency_id")
    current_price = fields.Monetary("Precio Actual", currency_field="currency_id", readonly=True)
    new_price = fields.Monetary("Precio Nuevo", currency_field="currency_id", readonly=True)
