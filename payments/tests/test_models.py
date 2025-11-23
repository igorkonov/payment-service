"""Тесты для моделей приложения payments."""

from decimal import Decimal

import pytest

from payments.models import Discount, Item, Order, OrderItem, Tax


@pytest.mark.django_db
@pytest.mark.models
class TestItemModel:
    """Тесты для модели Item."""

    def test_item_creation(self, item_usd):
        """Тест создания товара."""
        assert item_usd.name == "Test Product USD"
        assert item_usd.price == 5000
        assert item_usd.currency == "usd"

    def test_item_str(self, item_usd):
        """Тест строкового представления товара."""
        assert str(item_usd) == "Test Product USD - $50.00"

    def test_get_display_price_usd(self, item_usd):
        """Тест отображения цены в USD."""
        assert item_usd.get_display_price() == "$50.00"

    def test_get_display_price_eur(self, item_eur):
        """Тест отображения цены в EUR."""
        assert item_eur.get_display_price() == "€30.00"

    def test_item_currency_choices(self):
        """Тест доступных валют."""
        Item(name="Test", description="Test", price=1000)
        choices = dict(Item.CURRENCY_CHOICES)
        assert "usd" in choices
        assert "eur" in choices


@pytest.mark.django_db
@pytest.mark.models
class TestDiscountModel:
    """Тесты для модели Discount."""

    def test_discount_creation(self, discount_10):
        """Тест создания скидки."""
        assert discount_10.percent == Decimal("10.00")

    def test_discount_str(self, discount_10):
        """Тест строкового представления скидки."""
        assert str(discount_10) == "Скидка 10.00%"

    def test_discount_ordering(self, db):
        """Тест сортировки скидок по проценту."""
        d1 = Discount.objects.create(percent=Decimal("5.00"))
        d2 = Discount.objects.create(percent=Decimal("15.00"))
        d3 = Discount.objects.create(percent=Decimal("10.00"))

        discounts = list(Discount.objects.all())
        assert discounts[0] == d1
        assert discounts[1] == d3
        assert discounts[2] == d2


@pytest.mark.django_db
@pytest.mark.models
class TestTaxModel:
    """Тесты для модели Tax."""

    def test_tax_creation(self, tax_20):
        """Тест создания налога."""
        assert tax_20.percent == Decimal("20.00")

    def test_tax_str(self, tax_20):
        """Тест строкового представления налога."""
        assert str(tax_20) == "Налог 20.00%"

    def test_tax_ordering(self, db):
        """Тест сортировки налогов по проценту."""
        t1 = Tax.objects.create(percent=Decimal("5.00"))
        t2 = Tax.objects.create(percent=Decimal("25.00"))
        t3 = Tax.objects.create(percent=Decimal("15.00"))

        taxes = list(Tax.objects.all())
        assert taxes[0] == t1
        assert taxes[1] == t3
        assert taxes[2] == t2


@pytest.mark.django_db
@pytest.mark.models
class TestOrderItemModel:
    """Тесты для модели OrderItem."""

    def test_order_item_creation(self, order_empty, item_usd):
        """Тест создания товара в заказе."""
        order_item = OrderItem.objects.create(
            order=order_empty, item=item_usd, quantity=3
        )
        assert order_item.quantity == 3
        assert order_item.item == item_usd
        assert order_item.order == order_empty

    def test_order_item_default_quantity(self, order_empty, item_usd):
        """Тест значения quantity по умолчанию."""
        order_item = OrderItem.objects.create(order=order_empty, item=item_usd)
        assert order_item.quantity == 1


@pytest.mark.django_db
@pytest.mark.models
class TestOrderModel:
    """Тесты для модели Order."""

    def test_order_creation(self, order_empty):
        """Тест создания заказа."""
        assert order_empty.payment_currency == "usd"
        assert order_empty.discount is None
        assert order_empty.tax is None

    def test_order_str(self, order_empty):
        """Тест строкового представления заказа."""
        date_str = order_empty.created_at.strftime("%d.%m.%Y")
        assert str(order_empty) == f"Заказ #{order_empty.id} от {date_str}"

    def test_get_subtotal_single_item(self, order_empty, item_usd):
        """Тест расчета subtotal для одного товара."""
        OrderItem.objects.create(order=order_empty, item=item_usd, quantity=2)
        assert order_empty.get_subtotal() == 10000  # $50 * 2

    def test_get_subtotal_multiple_items(self, order_with_items):
        """Тест расчета subtotal для нескольких товаров."""
        # item_usd: $50 * 2 = $100
        # item_eur: €30 * 1 = $33 (converted at 1.1 rate)
        expected = 10000 + 3300
        assert order_with_items.get_subtotal() == expected

    def test_get_discount_amount_no_discount(self, order_empty, item_usd):
        """Тест расчета скидки когда её нет."""
        OrderItem.objects.create(order=order_empty, item=item_usd, quantity=1)
        assert order_empty.get_discount_amount() == 0

    def test_get_discount_amount_with_discount(
        self, order_empty, item_usd, discount_10
    ):
        """Тест расчета скидки 10%."""
        order_empty.discount = discount_10
        order_empty.save()
        OrderItem.objects.create(order=order_empty, item=item_usd, quantity=1)
        # $50 * 10% = $5
        assert order_empty.get_discount_amount() == 500

    def test_get_tax_amount_no_tax(self, order_empty, item_usd):
        """Тест расчета налога когда его нет."""
        OrderItem.objects.create(order=order_empty, item=item_usd, quantity=1)
        assert order_empty.get_tax_amount() == 0

    def test_get_tax_amount_with_tax(self, order_empty, item_usd, tax_20):
        """Тест расчета налога 20%."""
        order_empty.tax = tax_20
        order_empty.save()
        OrderItem.objects.create(order=order_empty, item=item_usd, quantity=1)
        # $50 * 20% = $10
        assert order_empty.get_tax_amount() == 1000

    def test_get_tax_amount_after_discount(
        self, order_empty, item_usd, discount_10, tax_20
    ):
        """Тест что налог применяется после скидки."""
        order_empty.discount = discount_10
        order_empty.tax = tax_20
        order_empty.save()
        OrderItem.objects.create(order=order_empty, item=item_usd, quantity=1)

        # Subtotal: $50
        # After discount (10%): $45
        # Tax (20% of $45): $9
        assert order_empty.get_tax_amount() == 900

    def test_get_total_price_no_discount_no_tax(self, order_empty, item_usd):
        """Тест итоговой цены без скидок и налогов."""
        OrderItem.objects.create(order=order_empty, item=item_usd, quantity=2)
        assert order_empty.get_total_price() == 10000  # $100

    def test_get_total_price_with_discount(self, order_empty, item_usd, discount_10):
        """Тест итоговой цены со скидкой."""
        order_empty.discount = discount_10
        order_empty.save()
        OrderItem.objects.create(order=order_empty, item=item_usd, quantity=2)
        # $100 - 10% = $90
        assert order_empty.get_total_price() == 9000

    def test_get_total_price_with_tax(self, order_empty, item_usd, tax_20):
        """Тест итоговой цены с налогом."""
        order_empty.tax = tax_20
        order_empty.save()
        OrderItem.objects.create(order=order_empty, item=item_usd, quantity=2)
        # $100 + 20% = $120
        assert order_empty.get_total_price() == 12000

    def test_get_total_price_with_discount_and_tax(self, order_with_discount_tax):
        """Тест итоговой цены со скидкой и налогом."""
        # Subtotal: $50
        # After discount (10%): $45
        # After tax (20%): $54
        assert order_with_discount_tax.get_total_price() == 5400

    def test_get_currency(self, order_empty):
        """Тест получения валюты заказа."""
        assert order_empty.get_currency() == "usd"

    def test_get_display_subtotal(self, order_empty, item_usd):
        """Тест отображения subtotal."""
        OrderItem.objects.create(order=order_empty, item=item_usd, quantity=1)
        assert order_empty.get_display_subtotal() == "$50.00"

    def test_get_display_discount(self, order_empty, item_usd, discount_10):
        """Тест отображения скидки."""
        order_empty.discount = discount_10
        order_empty.save()
        OrderItem.objects.create(order=order_empty, item=item_usd, quantity=1)
        assert order_empty.get_display_discount() == "$5.00"

    def test_get_display_tax(self, order_empty, item_usd, tax_20):
        """Тест отображения налога."""
        order_empty.tax = tax_20
        order_empty.save()
        OrderItem.objects.create(order=order_empty, item=item_usd, quantity=1)
        assert order_empty.get_display_tax() == "$10.00"

    def test_get_display_total(self, order_empty, item_usd):
        """Тест отображения итоговой суммы."""
        OrderItem.objects.create(order=order_empty, item=item_usd, quantity=1)
        assert order_empty.get_display_total() == "$50.00"

    def test_currency_conversion_eur_to_usd(self, order_empty, item_eur):
        """Тест конвертации EUR в USD."""
        OrderItem.objects.create(order=order_empty, item=item_eur, quantity=1)
        # €30 * 1.1 = $33
        assert order_empty.get_subtotal() == 3300

    def test_order_with_eur_currency(self, db, item_eur):
        """Тест заказа в EUR."""
        order = Order.objects.create(payment_currency="eur")
        OrderItem.objects.create(order=order, item=item_eur, quantity=1)
        assert order.get_display_total() == "€30.00"
