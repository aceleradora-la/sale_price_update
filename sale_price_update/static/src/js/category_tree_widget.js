/** @odoo-module **/

import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * CategoryTreeWidget
 *
 * Panel lateral de árbol de categorías para el wizard de actualización de precios.
 * Muestra la jerarquía de product.category con conteo de productos, expandible.
 * Al hacer clic en una categoría dispara el onchange del wizard.
 */
export class CategoryTreeWidget extends Component {
    static template = "sale_price_update.CategoryTreeWidget";
    static props = {
        value: { optional: true },        // id de la categoría seleccionada (o false)
        readonly: { type: Boolean, optional: true },
        update: Function,                  // callback para actualizar el campo
        record: { optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            nodes: [],           // raíces del árbol
            expanded: new Set(), // ids expandidos
            loading: true,
        });

        onWillStart(() => this._loadTree());

        // Re-cargar si el record cambia (p.ej. se recarga el wizard)
        onWillUpdateProps((nextProps) => {
            if (nextProps.record?.resId !== this.props.record?.resId) {
                this._loadTree();
            }
        });
    }

    async _loadTree() {
        this.state.loading = true;
        try {
            // 1. Todas las categorías
            const categories = await this.orm.searchRead(
                "product.category",
                [],
                ["id", "name", "parent_id"],
                { order: "name" }
            );

            // 2. Conteo de productos activos y vendibles por categoría
            // webReadGroup es la API correcta en Odoo 17+
            const groupResult = await this.orm.webReadGroup(
                "product.product",
                [["active", "=", true], ["sale_ok", "=", true]],
                ["categ_id"],
                ["categ_id"],
                {}
            );
            const directCount = {};
            const rawGroups = groupResult.groups || groupResult;
            for (const g of rawGroups) {
                if (g.categ_id) directCount[g.categ_id[0]] = g.categ_id_count;
            }

            // 3. Construir árbol
            const byId = {};
            for (const cat of categories) {
                byId[cat.id] = {
                    id: cat.id,
                    name: cat.name,
                    parentId: cat.parent_id ? cat.parent_id[0] : null,
                    children: [],
                    directCount: directCount[cat.id] || 0,
                    totalCount: 0,
                };
            }

            const roots = [];
            for (const cat of categories) {
                const node = byId[cat.id];
                if (node.parentId && byId[node.parentId]) {
                    byId[node.parentId].children.push(node);
                } else {
                    roots.push(node);
                }
            }

            // 4. Propagar conteos hacia arriba
            this._propagateCounts(roots);

            // 5. Expandir nodos con hijos por defecto (primer nivel)
            const expanded = new Set();
            for (const root of roots) {
                if (root.children.length > 0 && root.totalCount > 0) {
                    expanded.add(root.id);
                }
            }

            this.state.nodes = roots.filter((n) => n.totalCount > 0);
            this.state.expanded = expanded;
        } finally {
            this.state.loading = false;
        }
    }

    _propagateCounts(nodes) {
        for (const node of nodes) {
            this._propagateCounts(node.children);
            node.totalCount =
                node.directCount +
                node.children.reduce((s, c) => s + c.totalCount, 0);
        }
    }

    isExpanded(nodeId) {
        return this.state.expanded.has(nodeId);
    }

    isSelected(nodeId) {
        return this.props.value === nodeId;
    }

    toggleExpand(ev, nodeId) {
        ev.stopPropagation();
        if (this.state.expanded.has(nodeId)) {
            this.state.expanded.delete(nodeId);
        } else {
            this.state.expanded.add(nodeId);
        }
    }

    selectCategory(nodeId) {
        if (this.props.readonly) return;
        // Toggle: si ya está seleccionada, deseleccionar (volver a "Todos")
        const newVal = this.isSelected(nodeId) ? false : nodeId;
        this.props.update(newVal ? [nodeId, ""] : false);
    }

    selectAll() {
        if (this.props.readonly) return;
        this.props.update(false);
    }
}

// ── Registrar como field widget ───────────────────────────────────────────────
registry.category("fields").add("category_tree_widget", {
    component: CategoryTreeWidget,
    supportedTypes: ["many2one"],
    extractProps({ attrs }) {
        return {};
    },
});
