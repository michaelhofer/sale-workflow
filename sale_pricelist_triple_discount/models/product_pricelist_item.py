# Copyright 2019 Simone Rubino - Agile Business Group
# Copyright 2023 Simone Rubino - Aion Tech
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

# Map the rule's computation method to the name of the field used for the discount.
COMPUTE_PRICE_TO_DISCOUNT_FIELD = {
    "percentage": "percent_price",
    "formula": "price_discount",
}


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    discount2 = fields.Float(
        string="Discount 2 (%)",
        help="Second discount applied on a sale order line.",
        digits="Discount",
    )
    discount3 = fields.Float(
        string="Discount 3 (%)",
        help="Third discount applied on a sale order line.",
        digits="Discount",
    )

    @api.model
    def _get_extra_discount_field_names(self):
        return ["discount2", "discount3"]

    def _has_extra_discounts(self):
        self.ensure_one()
        return self.compute_price in COMPUTE_PRICE_TO_DISCOUNT_FIELD and any(
            self[field] for field in self._get_extra_discount_field_names()
        )

    def _get_main_discount(self):
        """Return the discount percentage the rule applies on its own."""
        self.ensure_one()
        if self.compute_price == "formula" and self.base == "standard_price":
            return -self.price_markup
        return self[COMPUTE_PRICE_TO_DISCOUNT_FIELD[self.compute_price]]

    def _get_triple_discount(self):
        """Return the discount percentage represented by all the discounts."""
        self.ensure_one()
        return self.env["triple.discount.mixin"]._get_aggregated_multiple_discounts(
            [self._get_main_discount()]
            + [self[field] for field in self._get_extra_discount_field_names()]
        )

    def _with_triple_discount(self):
        """Return an in-memory copy of the rule whose own discount is replaced
        by the aggregation of all its discounts, and without additional
        discounts, so that the core price computations can be reused unchanged."""
        self.ensure_one()
        # Copy the current values: the rule may be edited in a form and not saved
        values = {
            name: self[name]
            for name, field in self._fields.items()
            if field.store and not field.compute and name != "id"
        }
        discount = self._get_triple_discount()
        values.update(
            {
                "percent_price": discount,
                "price_discount": discount,
                "price_markup": -discount,
            }
        )
        values.update(dict.fromkeys(self._get_extra_discount_field_names(), 0.0))
        # No origin: new records with the same origin share their cache
        return self.new(values)

    def _compute_price(self, product, quantity, uom, date, currency=None, **kwargs):
        rule = self
        if rule and rule._has_extra_discounts():
            rule = rule._with_triple_discount()
        return super(ProductPricelistItem, rule)._compute_price(
            product, quantity, uom, date, currency=currency, **kwargs
        )

    @api.depends(lambda self: self._get_extra_discount_field_names())
    def _compute_price_label(self):
        res = super()._compute_price_label()
        for item in self.filtered(lambda item: item._has_extra_discounts()):
            virtual_item = item._with_triple_discount()
            super(ProductPricelistItem, virtual_item)._compute_price_label()
            item.price = virtual_item.price
        return res

    @api.depends(lambda self: self._get_extra_discount_field_names())
    def _compute_rule_tip(self):
        res = super()._compute_rule_tip()
        for item in self.filtered(lambda item: item._has_extra_discounts()):
            virtual_item = item._with_triple_discount()
            super(ProductPricelistItem, virtual_item)._compute_rule_tip()
            item.rule_tip = virtual_item.rule_tip
        return res
