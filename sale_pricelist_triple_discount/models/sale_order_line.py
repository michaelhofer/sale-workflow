# Copyright 2019 Simone Rubino - Agile Business Group
# Copyright 2023 Simone Rubino - Aion Tech
# Copyright 2025 Ethan Hildick
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount2 = fields.Float(
        compute="_compute_discount1",
        readonly=False,
        store=True,
        compute_sudo=True,
        precompute=True,
    )
    discount3 = fields.Float(
        compute="_compute_discount1",
        readonly=False,
        store=True,
        compute_sudo=True,
        precompute=True,
    )

    def _compute_discount1(self):
        # super() puts the whole discount of the pricelist rule in discount1:
        # split it so that discount2 and discount3 come from the rule too.
        res = super()._compute_discount1()
        discount_enabled = self.env[
            "product.pricelist.item"
        ]._is_discount_feature_enabled()
        for line in self:
            if not (
                line.order_id.pricelist_id
                and discount_enabled
                and line.product_id
                and line.product_uom_id
                and not line.display_type
            ):
                # The pricelist does not drive the discounts of this line:
                # keep the values set by the user.
                line.discount2 = line.discount2
                line.discount3 = line.discount3
                continue
            rule = line.pricelist_item_id
            if line.combo_item_id or not (line.discount1 and rule._show_discount()):
                # The discounts of the rule, if any, are in the unit price,
                # or come from the combo line as a whole in discount1.
                line.discount2 = line.discount3 = 0.0
                continue
            line.discount2 = rule.discount2
            line.discount3 = rule.discount3
            remaining = (1 - rule.discount2 / 100) * (1 - rule.discount3 / 100)
            if remaining:
                line.discount1 = 100 * (1 - (1 - line.discount1 / 100) / remaining)
        return res
