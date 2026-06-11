{
    "name": "Sale Price Update Assistant",
    "version": "19.0.1.0.0",
    "category": "Sales/Sales",
    "summary": "Wizard para actualización masiva de precios de venta por categoría o selección, con historial y preview de cambios.",
    "author": "Aceleradora LA",
    "website": "https://aceleradora.la",
    "maintainer": "Aceleradora LA",
    "support": "info@aceleradora.la",
    "depends": [
        "sale_management",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_price_update_history_views.xml",
        "views/sale_price_update_wizard_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sale_price_update/static/src/scss/sale_price_update.scss",
            "sale_price_update/static/src/xml/category_tree_widget.xml",
            "sale_price_update/static/src/js/category_tree_widget.js",
        ],
    },
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3",
}
