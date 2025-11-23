"""Интеграционные тесты для полного flow."""

import pytest
from django.urls import reverse

from payments.models import Order


@pytest.mark.django_db
@pytest.mark.integration
class TestFullPurchaseFlow:
    """Тесты для полного процесса покупки."""

    def test_full_purchase_flow(
        self, client, item_usd, item_eur, mock_stripe_payment_intent
    ):
        """Тест полного процесса от добавления в корзину до оплаты."""
        # 1. Просмотр главной страницы
        response = client.get(reverse("payments:index"))
        assert response.status_code == 200

        # 2. Добавление товаров в корзину
        client.get(reverse("payments:add_to_cart", args=[item_usd.id]))
        client.get(reverse("payments:add_to_cart", args=[item_eur.id]))

        # 3. Просмотр корзины
        response = client.get(reverse("payments:view_cart"))
        assert response.status_code == 200
        assert len(response.context["cart_items"]) == 2

        # 4. Создание заказа
        response = client.get(reverse("payments:checkout_cart"))
        assert response.status_code == 302

        order = Order.objects.latest("created_at")
        assert order.items.count() == 2

        # 5. Просмотр страницы заказа
        response = client.get(reverse("payments:order_detail", args=[order.id]))
        assert response.status_code == 200

        # 6. Создание Payment Intent
        response = client.get(
            reverse("payments:create_order_checkout_session", args=[order.id])
        )
        assert response.status_code == 200
        data = response.json()
        assert "clientSecret" in data

        # 7. Успешная оплата
        response = client.get(reverse("payments:success"))
        assert response.status_code == 200

    def test_purchase_with_discount_and_tax(
        self,
        client,
        item_usd,
        discount_10,
        tax_20,
        mock_stripe_payment_intent,
        admin_user,
    ):
        """Тест покупки со скидкой и налогом."""
        # 1. Добавляем товар в корзину
        client.get(reverse("payments:add_to_cart", args=[item_usd.id]))

        # 2. Создаем заказ
        client.get(reverse("payments:checkout_cart"))
        order = Order.objects.latest("created_at")

        # 3. Админ назначает скидку и налог
        order.discount = discount_10
        order.tax = tax_20
        order.save()

        # 4. Проверяем расчеты
        subtotal = order.get_subtotal()
        discount_amount = order.get_discount_amount()
        tax_amount = order.get_tax_amount()
        total = order.get_total_price()

        assert subtotal == 5000  # $50
        assert discount_amount == 500  # $5 (10%)
        assert tax_amount == 900  # $9 (20% of $45)
        assert total == 5400  # $54

        # 5. Создаем Payment Intent
        response = client.get(
            reverse("payments:create_order_checkout_session", args=[order.id])
        )
        assert response.status_code == 200

        # Проверяем что правильная сумма передана в Stripe
        call_kwargs = mock_stripe_payment_intent.call_args[1]
        assert call_kwargs["amount"] == 5400

    def test_multi_currency_purchase(
        self, client, item_usd, item_eur, mock_stripe_payment_intent
    ):
        """Тест покупки товаров в разных валютах."""
        # 1. Добавляем товары в USD и EUR
        client.get(reverse("payments:add_to_cart", args=[item_usd.id]))
        client.get(reverse("payments:add_to_cart", args=[item_eur.id]))

        # 2. Выбираем валюту оплаты EUR
        client.get(reverse("payments:change_currency", args=["eur"]))

        # 3. Создаем заказ
        client.get(reverse("payments:checkout_cart"))
        order = Order.objects.latest("created_at")

        # 4. Проверяем что заказ в EUR
        assert order.payment_currency == "eur"

        # 5. Проверяем конвертацию
        # item_usd: $50 → €45.45 (50 / 1.1)
        # item_eur: €30 → €30
        # Total: ~€75.45
        total = order.get_total_price()
        assert total > 7000  # Примерно €75

    def test_quantity_management_flow(self, client, item_usd):
        """Тест управления количеством товаров."""
        # 1. Добавляем товар
        client.get(reverse("payments:add_to_cart", args=[item_usd.id]))

        # 2. Увеличиваем количество
        client.get(
            reverse("payments:update_cart_quantity", args=[item_usd.id, "increase"])
        )
        client.get(
            reverse("payments:update_cart_quantity", args=[item_usd.id, "increase"])
        )

        # 3. Проверяем количество в корзине
        response = client.get(reverse("payments:view_cart"))
        cart_items = response.context["cart_items"]
        assert cart_items[0]["quantity"] == 3

        # 4. Создаем заказ
        client.get(reverse("payments:checkout_cart"))
        order = Order.objects.latest("created_at")

        # 5. Проверяем что количество сохранилось
        order_item = order.order_items.first()
        assert order_item.quantity == 3

        # 6. Проверяем расчет суммы
        assert order.get_total_price() == 15000  # $50 * 3

    def test_buy_now_flow(self, client, item_usd, item_eur, mock_stripe_payment_intent):
        """Тест быстрой покупки (Buy Now)."""
        # 1. Добавляем товар в корзину
        client.get(reverse("payments:add_to_cart", args=[item_eur.id]))

        # 2. Используем Buy Now для другого товара
        response = client.get(reverse("payments:buy_now", args=[item_usd.id]))
        assert response.status_code == 302

        # 3. Проверяем что корзина содержит только новый товар
        session = client.session
        assert len(session["cart"]) == 1
        assert str(item_usd.id) in session["cart"]
        assert str(item_eur.id) not in session["cart"]

    def test_empty_cart_handling(self, client):
        """Тест обработки пустой корзины."""
        # 1. Пытаемся создать заказ из пустой корзины
        response = client.get(reverse("payments:checkout_cart"))

        # 2. Должен редиректить на главную
        assert response.status_code == 302
        assert response.url == reverse("payments:index")

        # 3. Заказ не должен быть создан
        assert Order.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.integration
class TestAdminWorkflow:
    """Тесты для работы админа с заказами."""

    def test_admin_assign_discount_tax(
        self, admin_client, order_with_items, discount_10, tax_20
    ):
        """Тест назначения скидки и налога админом."""
        url = reverse("admin:payments_order_change", args=[order_with_items.id])

        # Получаем форму
        response = admin_client.get(url)
        assert response.status_code == 200

        # Назначаем скидку и налог
        data = {
            "payment_currency": "usd",
            "discount": discount_10.id,
            "tax": tax_20.id,
            "order_items-TOTAL_FORMS": "2",
            "order_items-INITIAL_FORMS": "2",
            "order_items-MIN_NUM_FORMS": "0",
            "order_items-MAX_NUM_FORMS": "1000",
            "order_items-0-id": order_with_items.order_items.all()[0].id,
            "order_items-0-item": order_with_items.order_items.all()[0].item.id,
            "order_items-0-quantity": "2",
            "order_items-1-id": order_with_items.order_items.all()[1].id,
            "order_items-1-item": order_with_items.order_items.all()[1].item.id,
            "order_items-1-quantity": "1",
        }

        response = admin_client.post(url, data)

        # Проверяем что изменения сохранены
        order_with_items.refresh_from_db()
        assert order_with_items.discount == discount_10
        assert order_with_items.tax == tax_20
