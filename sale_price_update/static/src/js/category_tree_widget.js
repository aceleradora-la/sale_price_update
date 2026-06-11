/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * CategoryTreeWidget
 *
 * Panel lateral de árbol de categorías para el wizard de actualización de precios.
 * Muestra la jerarquía de product.category con conteo de productos, expandible.
 * Al hacer clic en una categoría escribe el many2one del wizard y dispara
 * su onchange (que recarga las líneas).
 *
 * Field widget estándar Odoo 17/18/19: recibe props { record, name, readonly }.
 */
export class CategoryTreeWidget extends Component {
    static template = "sale_price_update.CategoryTreeWidget";
    // Los field widgets reciben más props de las que usamos (record, name,
    // readonly, id, etc.). Validación laxa para compatibilidad 17/18/19.
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            nodes: [],           // raíces del árbol
            expanded: new Set(), // ids expandidos
            loading: true,
        });

        onWillStart(() => this._loadTree());
    }

    /** Id de la categoría seleccionada según el valor actual del campo. */
    get selectedId() {
        const value = this.props.record.data[this.props.name];
        if (!value) {
            return false;
        }
        if (Array.isArray(value)) {
            return value[0]; // formato [id, display_name] (Odoo 17/18)
        }
        if (typeof value === "object") {
            return value.id; // formato { id, display_name } (Odoo 19)
        }
        return value;
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

            // 2. Conteo de productos activos y vendibles por categoría.
            // searchRead + conteo en cliente: funciona igual en Odoo 17/18/19
            // (la firma de webReadGroup cambió entre versiones).
            const products = await this.orm.searchRead(
                "product.product",
                [["active", "=", true], ["sale_ok", "=", true]],
                ["categ_id"]
            );
            const directCount = {};
            for (const p of products) {
                if (p.categ_id) {
                    const cid = Array.isArray(p.categ_id) ? p.categ_id[0] : p.categ_id.id;
                    directCount[cid] = (directCount[cid] || 0) + 1;
                }
            }

            // 3. Construir árbol
            const byId = {};
            for (const cat of categories) {
                const parentId = cat.parent_id
                    ? (Array.isArray(cat.parent_id) ? cat.parent_id[0] : cat.parent_id.id)
                    : null;
                byId[cat.id] = {
                    id: cat.id,
                    name: cat.name,
                    parentId,
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

            // 5. Expandir nodos raíz con contenido por defecto
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
        return this.selectedId === nodeId;
    }

    toggleExpand(ev, nodeId) {
        ev.stopPropagation();
        if (this.state.expanded.has(nodeId)) {
            this.state.expanded.delete(nodeId);
        } else {
            this.state.expanded.add(nodeId);
        }
    }

    async _updateField(value) {
        // record.update escribe el campo y dispara el onchange del wizard
        await this.props.record.update({ [this.props.name]: value });
    }

    async selectCategory(node) {
        if (this.props.readonly) {
            return;
        }
        // Toggle: si ya está seleccionada, deseleccionar (volver a "Todos")
        if (this.isSelected(node.id)) {
            await this._updateField(false);
        } else {
            await this._updateField([node.id, node.name]);
        }
    }

    async selectAll() {
        if (this.props.readonly) {
            return;
        }
        await this._updateField(false);
    }
}

// ── Registrar como field widget ───────────────────────────────────────────────
registry.category("fields").add("category_tree_widget", {
    component: CategoryTreeWidget,
    supportedTypes: ["many2one"],
});
