# Sale Price Update Suite

Odoo addons repo by [Aceleradora LA](https://aceleradora.la). Compatible with **Odoo 17, 18, 19** — Community and Enterprise (branches `17.0`, `18.0`, `19.0`).

## Modules

### `sale_price_update` — Sale Price Update Assistant
Bulk sale price updates with:
- **Category tree panel** (like the Inventory stock view) for filtering products
- **Multi-pricelist support** — update several pricelists in one shot, each from its own current price
- **% increase per product or global** — with live preview of old vs. new price
- **Date-based validity** — current prices are expired the day before the new ones start
- **Price history** — permanent log of every change with user, %, and previous price
- **Weighing support** — integrates with `sale_stock_weighing` ($/kg prices) when installed and enabled

### `sale_pricelist_report` — Pricelist Report & Send to Customers
- **PDF report** of the prices in force for a pricelist at any date (past or future)
- Grouped by category, with $/kg suffix for weighed products
- **Customer tab**: shows partners with that pricelist assigned, flags missing emails
- **Send by email**: one message per customer with the PDF attached, logged in each partner's chatter

## Installation

1. Copy the module folders into your Odoo addons path.
2. Update the app list and install.

## Usage

- **Ventas → Catálogo → Actualización de Precios**

## License

LGPL-3
