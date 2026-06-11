from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class SalePricelistReportWizard(models.TransientModel):
    """
    Reporte de precios vigentes de una lista a una fecha determinada,
    con envío por email a los clientes que tienen esa lista asignada.
    """

    _name = "sale.pricelist.report.wizard"
    _description = "Reporte de Lista de Precios"

    pricelist_id = fields.Many2one(
        "product.pricelist", string="Lista de Precios", required=True,
    )
    currency_id = fields.Many2one(
        "res.currency", related="pricelist_id.currency_id",
    )
    date = fields.Date(
        "Precios vigentes al",
        default=fields.Date.today,
        required=True,
        help="Fecha de vigencia. Permite previsualizar precios futuros ya "
             "cargados (ej: los que rigen desde la próxima semana).",
    )
    filter_categ_id = fields.Many2one(
        "product.category",
        string="Filtrar por Categoría",
        help="Limita el reporte a una categoría (incluye subcategorías).",
    )
    line_ids = fields.One2many(
        "sale.pricelist.report.wizard.line", "wizard_id", string="Precios",
    )
    partner_ids = fields.Many2many(
        "res.partner",
        "sale_pricelist_report_wiz_partner_rel",
        "wizard_id",
        "partner_id",
        string="Clientes",
        help="Clientes que tienen esta lista de precios asignada. "
             "Podés quitar los que no deban recibir el reporte.",
    )
    line_count = fields.Integer(compute="_compute_counts")
    partner_count = fields.Integer(compute="_compute_counts")
    partner_no_email_count = fields.Integer(compute="_compute_counts")

    @api.depends("line_ids", "partner_ids", "partner_ids.email")
    def _compute_counts(self):
        for wiz in self:
            wiz.line_count = len(wiz.line_ids)
            wiz.partner_count = len(wiz.partner_ids)
            wiz.partner_no_email_count = len(
                wiz.partner_ids.filtered(lambda p: not p.email)
            )

    # ── Carga de líneas y clientes ────────────────────────────────────
    def _get_products_domain(self):
        domain = [("sale_ok", "=", True), ("active", "=", True)]
        if self.filter_categ_id:
            domain.append(("categ_id", "child_of", self.filter_categ_id.id))
        return domain

    def _build_line_commands(self):
        """Reconstruye las líneas en memoria (apto para onchange)."""
        if not self.pricelist_id:
            return [Command.clear()]
        products = self.env["product.product"].search(
            self._get_products_domain(), order="categ_id, default_code, name"
        )
        prices = self.pricelist_id._spu_get_prices(products, date=self.date)
        weighing = self.pricelist_id._spu_weighing_enabled()

        commands = [Command.clear()]
        for product in products:
            price = prices.get(product.id, 0.0)
            if price <= 0:
                continue
            is_weighed = weighing and getattr(product, "is_weighed_product", False)
            uom_name = ""
            if is_weighed:
                weighing_uom = getattr(product, "weighing_uom_id", False)
                uom_name = weighing_uom.name if weighing_uom else "kg"
            commands.append(Command.create({
                "product_id": product.id,
                "categ_id": product.categ_id.id,
                "price": price,
                "is_weighed": is_weighed,
                "weighing_uom_name": uom_name,
            }))
        return commands

    @api.onchange("pricelist_id", "date", "filter_categ_id")
    def _onchange_reload_lines(self):
        self.line_ids = self._build_line_commands()

    @api.onchange("pricelist_id")
    def _onchange_pricelist_partners(self):
        """Precarga los clientes que tienen asignada esta lista de precios."""
        if not self.pricelist_id:
            self.partner_ids = [Command.clear()]
            return
        partners = self.env["res.partner"].search([
            ("property_product_pricelist", "=", self.pricelist_id.id),
            ("parent_id", "=", False),
        ])
        self.partner_ids = [Command.set(partners.ids)]

    # ── Reporte para el PDF (recomputa server-side, no depende de UI) ──
    def _get_report_groups(self):
        """Líneas agrupadas por categoría para el template QWeb.

        Recalcula los precios al momento de renderizar: el PDF nunca
        depende de lo que el cliente web haya guardado.
        """
        self.ensure_one()
        products = self.env["product.product"].search(
            self._get_products_domain(), order="categ_id, default_code, name"
        )
        prices = self.pricelist_id._spu_get_prices(products, date=self.date)
        weighing = self.pricelist_id._spu_weighing_enabled()

        groups = {}
        for product in products:
            price = prices.get(product.id, 0.0)
            if price <= 0:
                continue
            categ = product.categ_id
            key = categ.id
            if key not in groups:
                groups[key] = {
                    "name": categ.display_name or _("Sin Categoría"),
                    "lines": [],
                }
            uom_suffix = ""
            if weighing and getattr(product, "is_weighed_product", False):
                weighing_uom = getattr(product, "weighing_uom_id", False)
                uom_suffix = " / %s" % (
                    weighing_uom.name if weighing_uom else "kg"
                )
            groups[key]["lines"].append({
                "name": product.display_name,
                "price": price,
                "uom_suffix": uom_suffix,
            })
        return sorted(groups.values(), key=lambda g: g["name"])

    # ── Acciones ──────────────────────────────────────────────────────
    def action_print_pdf(self):
        self.ensure_one()
        if not self.pricelist_id:
            raise UserError(_("Seleccioná una lista de precios."))
        return self.env.ref(
            "sale_pricelist_report.action_report_pricelist"
        ).report_action(self)

    def action_send_emails(self):
        self.ensure_one()
        if not self.pricelist_id:
            raise UserError(_("Seleccioná una lista de precios."))
        partners = self.partner_ids.filtered(lambda p: p.email)
        skipped = self.partner_ids - partners
        if not partners:
            raise UserError(_(
                "No hay clientes con email para enviar. "
                "Verificá la pestaña Clientes."
            ))

        # Renderizar el PDF una sola vez
        report = self.env.ref("sale_pricelist_report.action_report_pricelist")
        pdf_content, _dummy = self.env["ir.actions.report"]._render_qweb_pdf(
            report, res_ids=self.ids
        )
        date_str = self.date.strftime("%d/%m/%Y")
        filename = "Lista de Precios - %s - %s.pdf" % (
            self.pricelist_id.name, self.date.strftime("%d-%m-%Y"),
        )
        subject = _("Lista de Precios %s — vigencia %s") % (
            self.pricelist_id.name, date_str,
        )
        company = self.env.company

        for partner in partners:
            body = _(
                "<p>Estimado/a %(partner)s,</p>"
                "<p>Le adjuntamos la lista de precios <b>%(pricelist)s</b> "
                "con vigencia a partir del <b>%(date)s</b>.</p>"
                "<p>Ante cualquier consulta, no dude en contactarnos.</p>"
                "<p>Saludos cordiales,<br/>%(company)s</p>"
            ) % {
                "partner": partner.name,
                "pricelist": self.pricelist_id.name,
                "date": date_str,
                "company": company.name,
            }
            attachment = self.env["ir.attachment"].create({
                "name": filename,
                "raw": pdf_content,
                "mimetype": "application/pdf",
                "res_model": "res.partner",
                "res_id": partner.id,
            })
            # message_post: envía el mail por la cola de correo de Odoo y
            # deja registro en el chatter del cliente (historial de envíos).
            partner.message_post(
                subject=subject,
                body=body,
                attachment_ids=[attachment.id],
                partner_ids=[partner.id],
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )

        message = _("Lista enviada a %d clientes.") % len(partners)
        if skipped:
            message += _(" %d clientes sin email fueron omitidos.") % len(skipped)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Envío realizado"),
                "message": message,
                "type": "success" if not skipped else "warning",
                "sticky": bool(skipped),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }


class SalePricelistReportWizardLine(models.TransientModel):
    _name = "sale.pricelist.report.wizard.line"
    _description = "Línea — Reporte de Lista de Precios"
    _order = "categ_id, product_id"

    wizard_id = fields.Many2one(
        "sale.pricelist.report.wizard", ondelete="cascade"
    )
    currency_id = fields.Many2one(
        "res.currency", related="wizard_id.currency_id"
    )
    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    categ_id = fields.Many2one("product.category", string="Categoría", readonly=True)
    price = fields.Monetary("Precio", currency_field="currency_id", readonly=True)
    is_weighed = fields.Boolean("Por Peso", readonly=True)
    weighing_uom_name = fields.Char("UdM Peso", readonly=True)
