from odoo import api, models


class PricelistReport(models.AbstractModel):
    """Modelo de reporte QWeb para la lista de precios."""

    _name = "report.sale_pricelist_report.report_pricelist"
    _description = "Reporte QWeb — Lista de Precios"

    @api.model
    def _get_report_values(self, docids, data=None):
        wizards = self.env["sale.pricelist.report.wizard"].browse(docids)
        return {
            "doc_ids": docids,
            "doc_model": "sale.pricelist.report.wizard",
            "docs": wizards,
        }
