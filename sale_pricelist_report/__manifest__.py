{
    "name": "Pricelist Report & Send to Customers",
    "version": "18.0.1.0.1",
    "category": "Sales/Sales",
    "summary": "Reporte PDF de precios vigentes de una lista a una fecha, con envío por email a los clientes que tienen esa lista asignada.",
    "author": "Aceleradora LA",
    "website": "https://aceleradora.la",
    "maintainer": "Aceleradora LA",
    "support": "info@aceleradora.la",
    "depends": [
        "sale_price_update",
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/pricelist_report_templates.xml",
        "views/sale_pricelist_report_wizard_views.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3",
}
