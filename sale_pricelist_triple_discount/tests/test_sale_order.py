#  Copyright 2023 Simone Rubino - Aion Tech
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import Form, tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged("post_install", "-at_install")
class TestSalePrices(SaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.order = cls.empty_order
        cls.order.pricelist_id = cls.pricelist

    def _add_rule(self, compute_price, discount):
        discount_field = {
            "percentage": "percent_price",
            "formula": "price_discount",
        }[compute_price]
        pricelist_form = Form(self.pricelist)
        with pricelist_form.item_ids.new() as item:
            item.compute_price = compute_price
            setattr(item, discount_field, discount)
            item.discount2 = 20
            item.discount3 = 30
        return pricelist_form.save().item_ids

    def _add_line(self):
        order_form = Form(self.order)
        with order_form.order_line.new() as line:
            line.product_id = self.product
        return order_form.save().order_line

    def test_percentage_with_line_discounts(self):
        """A percentage rule propagates its discounts to the sale order line
        when discounts on lines are enabled.
        """
        self._enable_discounts()
        rule = self._add_rule("percentage", 10)
        self.assertEqual(self.product.lst_price, 20)
        self.assertIn("49.6 % discount", rule.price)

        line = self._add_line()

        self.assertEqual(line.pricelist_item_id, rule)
        self.assertEqual(line.discount1, 10)
        self.assertEqual(line.discount2, 20)
        self.assertEqual(line.discount3, 30)
        self.assertAlmostEqual(line.discount, 49.6)
        self.assertEqual(line.price_unit, 20)
        self.assertEqual(line.price_subtotal, 10.08)

    def test_percentage_without_line_discounts(self):
        """Without discounts on lines, all the discounts of a percentage rule
        are included in the unit price.
        """
        rule = self._add_rule("percentage", 10)

        line = self._add_line()

        self.assertEqual(line.pricelist_item_id, rule)
        self.assertFalse(line.discount1)
        self.assertFalse(line.discount2)
        self.assertFalse(line.discount3)
        self.assertEqual(line.price_unit, 10.08)
        self.assertEqual(line.price_subtotal, 10.08)

    def test_formula(self):
        """All the discounts of a formula rule are included in the unit price."""
        self._enable_discounts()
        rule = self._add_rule("formula", 10)
        self.assertIn("49.6 % discount", rule.price)
        self.assertIn("49.6 % discount", rule.rule_tip)

        line = self._add_line()

        self.assertEqual(line.pricelist_item_id, rule)
        self.assertFalse(line.discount1)
        self.assertFalse(line.discount2)
        self.assertFalse(line.discount3)
        self.assertEqual(line.price_unit, 10.08)
        self.assertEqual(line.price_subtotal, 10.08)

    def test_rule_form_labels(self):
        """The labels follow the values edited in the form, before saving."""
        rule = self._add_rule("percentage", 10)
        rule_form = Form(rule)
        rule_form.compute_price = "formula"
        rule_form.price_discount = 10
        self.assertIn("49.6 % discount", rule_form.rule_tip)
        rule_form.discount3 = 0
        self.assertIn("28 % discount", rule_form.rule_tip)

    def test_rule_without_extra_discounts(self):
        """A rule without the additional discounts behaves like in core."""
        self._enable_discounts()
        rule = self._add_rule("percentage", 10)
        rule.write({"discount2": 0, "discount3": 0})
        self.assertIn("10 % discount", rule.price)

        line = self._add_line()

        self.assertEqual(line.discount1, 10)
        self.assertFalse(line.discount2)
        self.assertFalse(line.discount3)
        self.assertEqual(line.price_subtotal, 18)

    def test_quantity_change_keeps_rule_discounts(self):
        self._enable_discounts()
        self._add_rule("percentage", 10)
        line = self._add_line()

        line.product_uom_qty = 3

        self.assertEqual(line.discount1, 10)
        self.assertEqual(line.discount2, 20)
        self.assertEqual(line.discount3, 30)
        self.assertAlmostEqual(line.price_subtotal, 30.24)

    def test_update_prices(self):
        """Updating the prices of the order applies the discounts of the new
        pricelist.
        """
        self._enable_discounts()
        line = self._add_line()
        self.assertFalse(line.discount1)
        self.assertFalse(line.discount2)
        self.assertFalse(line.discount3)

        self._add_rule("percentage", 10)
        self.order.action_update_prices()

        self.assertEqual(line.discount1, 10)
        self.assertEqual(line.discount2, 20)
        self.assertEqual(line.discount3, 30)
        self.assertEqual(line.price_subtotal, 10.08)

    def test_invoice(self):
        """The discounts of the rule reach the invoice line."""
        self._enable_discounts()
        self._add_rule("percentage", 10)
        self._add_line()
        self.order.action_confirm()

        invoice_line = self.order._create_invoices().invoice_line_ids

        self.assertEqual(invoice_line.discount1, 10)
        self.assertEqual(invoice_line.discount2, 20)
        self.assertEqual(invoice_line.discount3, 30)
        self.assertEqual(invoice_line.price_subtotal, 10.08)

    def test_pricelist_readonly(self):
        """A user with readonly access on pricelists can read them and their items."""
        self._add_rule("percentage", 10)
        readonly_pricelist = self.pricelist.with_user(self.sale_user)
        # pre-condition
        self.assertTrue(readonly_pricelist.has_access("read"))
        self.assertFalse(readonly_pricelist.has_access("write"))

        # Assert
        readonly_pricelist.read()
        readonly_pricelist.item_ids.read()
