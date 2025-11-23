"""Тесты для views приложения payments."""

import pytest
from django.urls import reverse

from payments.models import Order


@pytest.mark.django_db
@pytest.mark.views
class TestIndexView:
    """Тесты для главной страницы."""

    def test_index_view_status_code(self, client):
        """Тест доступности главной страницы."""
        response = client.get(reverse("payments:index"))
        assert response.status_code == 200

    def test_index_view_template(self, client):
        """Тест использования правильного шаблона."""
        response = client.get(reverse("payments:index"))
        assert "payments/index.html" in [t.name for t in response.templates]

    def test_index_view_context(self, client, item_usd, item_eur):
        """Тест контекста главной страницы."""
        response = client.get(reverse("payments:index"))
        assert "items" in response.context
        items = list(response.context["items"])
        assert len(items) == 2
        assert item_usd in items
        assert item_eur in items


@pytest.mark.django_db
@pytest.mark.views
class TestOrderDetailView:
    """Тесты для страницы деталей заказа."""

    def test_order_detail_view_status_code(self, client, order_with_items):
        """Тест доступности страницы заказа."""
        url = reverse("payments:order_detail", args=[order_with_items.id])
        response = client.get(url)
        assert response.status_code == 200

    def test_order_detail_view_template(self, client, order_with_items):
        """Тест использования правильного шаблона."""
        url = reverse("payments:order_detail", args=[order_with_items.id])
        response = client.get(url)
        assert "payments/order_detail.html" in [t.name for t in response.templates]

    def test_order_detail_view_context(self, client, order_with_items):
        """Тест контекста страницы заказа."""
        url = reverse("payments:order_detail", args=[order_with_items.id])
        response = client.get(url)
        assert "order" in response.context
        assert response.context["order"] == order_with_items
        assert "stripe_public_key" in response.context

    def test_order_detail_view_404(self, client):
        """Тест 404 для несуществующего заказа."""
        url = reverse("payments:order_detail", args=[99999])
        response = client.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.views
class TestCreateOrderCheckoutSession:
    """Тесты для создания Payment Intent."""

    def test_create_payment_intent_success(
        self, client, order_with_items, mock_stripe_payment_intent
    ):
        """Тест успешного создания Payment Intent."""
        url = reverse(
            "payments:create_order_checkout_session", args=[order_with_items.id]
        )
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "clientSecret" in data
        assert data["clientSecret"] == "pi_test_secret_123"

        # Проверяем что Stripe API был вызван
        mock_stripe_payment_intent.assert_called_once()
        call_kwargs = mock_stripe_payment_intent.call_args[1]
        assert call_kwargs["amount"] == order_with_items.get_total_price()
        assert call_kwargs["currency"] == "usd"

    def test_create_payment_intent_with_metadata(
        self, client, order_with_discount_tax, mock_stripe_payment_intent
    ):
        """Тест что metadata содержит детальный breakdown."""
        url = reverse(
            "payments:create_order_checkout_session", args=[order_with_discount_tax.id]
        )
        response = client.get(url)

        assert response.status_code == 200

        call_kwargs = mock_stripe_payment_intent.call_args[1]
        metadata = call_kwargs["metadata"]

        assert "order_id" in metadata
        assert "subtotal" in metadata
        assert "discount_amount" in metadata
        assert "tax_amount" in metadata
        assert "total" in metadata
        assert metadata["discount_percent"] == 10.0
        assert metadata["tax_percent"] == 20.0

    def test_create_payment_intent_404(self, client):
        """Тест 404 для несуществующего заказа."""
        url = reverse("payments:create_order_checkout_session", args=[99999])
        response = client.get(url)
        assert response.status_code == 404

    def test_create_payment_intent_stripe_error(self, client, order_with_items, mocker):
        """Тест обработки ошибки Stripe API."""
        # Мокаем Stripe чтобы выбросить исключение
        mock_stripe = mocker.patch("stripe.PaymentIntent.create")
        mock_stripe.side_effect = Exception("Stripe API Error")

        url = reverse(
            "payments:create_order_checkout_session", args=[order_with_items.id]
        )
        response = client.get(url)

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Stripe API Error" in data["error"]


@pytest.mark.django_db
@pytest.mark.views
class TestCartViews:
    """Тесты для функционала корзины."""

    def test_add_to_cart(self, client, item_usd):
        """Тест добавления товара в корзину."""
        url = reverse("payments:add_to_cart", args=[item_usd.id])
        response = client.get(url)

        assert response.status_code == 302  # Redirect
        assert response.url == reverse("payments:index")

        # Проверяем что товар добавлен в сессию
        session = client.session
        assert "cart" in session
        assert str(item_usd.id) in session["cart"]
        assert session["cart"][str(item_usd.id)]["quantity"] == 1

    def test_add_to_cart_increment_quantity(self, client, item_usd):
        """Тест увеличения количества при повторном добавлении."""
        url = reverse("payments:add_to_cart", args=[item_usd.id])

        # Добавляем первый раз
        client.get(url)
        # Добавляем второй раз
        client.get(url)

        session = client.session
        assert session["cart"][str(item_usd.id)]["quantity"] == 2

    def test_add_to_cart_404(self, client):
        """Тест 404 для несуществующего товара."""
        url = reverse("payments:add_to_cart", args=[99999])
        response = client.get(url)
        assert response.status_code == 404

    def test_view_cart_empty(self, client):
        """Тест просмотра пустой корзины."""
        url = reverse("payments:view_cart")
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["cart_items"] == []
        assert response.context["total"] == 0

    def test_view_cart_with_items(self, client, item_usd, item_eur):
        """Тест просмотра корзины с товарами."""
        # Добавляем товары
        client.get(reverse("payments:add_to_cart", args=[item_usd.id]))
        client.get(reverse("payments:add_to_cart", args=[item_eur.id]))

        url = reverse("payments:view_cart")
        response = client.get(url)

        assert response.status_code == 200
        assert len(response.context["cart_items"]) == 2
        assert response.context["total"] > 0

    def test_remove_from_cart(self, client, item_usd):
        """Тест удаления товара из корзины."""
        # Добавляем товар
        client.get(reverse("payments:add_to_cart", args=[item_usd.id]))

        # Удаляем товар
        url = reverse("payments:remove_from_cart", args=[item_usd.id])
        response = client.get(url)

        assert response.status_code == 302
        session = client.session
        assert str(item_usd.id) not in session.get("cart", {})

    def test_update_cart_quantity_increase(self, client, item_usd):
        """Тест увеличения количества товара."""
        # Добавляем товар
        client.get(reverse("payments:add_to_cart", args=[item_usd.id]))

        # Увеличиваем количество
        url = reverse("payments:update_cart_quantity", args=[item_usd.id, "increase"])
        response = client.get(url)

        assert response.status_code == 302
        session = client.session
        assert session["cart"][str(item_usd.id)]["quantity"] == 2

    def test_update_cart_quantity_decrease(self, client, item_usd):
        """Тест уменьшения количества товара."""
        # Добавляем товар дважды
        client.get(reverse("payments:add_to_cart", args=[item_usd.id]))
        client.get(reverse("payments:add_to_cart", args=[item_usd.id]))

        # Уменьшаем количество
        url = reverse("payments:update_cart_quantity", args=[item_usd.id, "decrease"])
        response = client.get(url)

        assert response.status_code == 302
        session = client.session
        assert session["cart"][str(item_usd.id)]["quantity"] == 1

    def test_update_cart_quantity_remove_on_zero(self, client, item_usd):
        """Тест удаления товара при уменьшении до 0."""
        # Добавляем товар
        client.get(reverse("payments:add_to_cart", args=[item_usd.id]))

        # Уменьшаем до 0
        url = reverse("payments:update_cart_quantity", args=[item_usd.id, "decrease"])
        response = client.get(url)

        assert response.status_code == 302
        session = client.session
        assert str(item_usd.id) not in session.get("cart", {})

    def test_buy_now(self, client, item_usd):
        """Тест быстрой покупки товара."""
        url = reverse("payments:buy_now", args=[item_usd.id])
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse("payments:view_cart")

        # Проверяем что корзина содержит только этот товар
        session = client.session
        assert len(session["cart"]) == 1
        assert str(item_usd.id) in session["cart"]

    def test_change_currency(self, client):
        """Тест смены валюты оплаты."""
        url = reverse("payments:change_currency", args=["eur"])
        response = client.get(url)

        assert response.status_code == 302
        session = client.session
        assert session["payment_currency"] == "eur"

    def test_change_currency_invalid(self, client):
        """Тест что невалидная валюта игнорируется."""
        url = reverse("payments:change_currency", args=["gbp"])
        response = client.get(url)

        assert response.status_code == 302
        session = client.session
        assert "payment_currency" not in session


@pytest.mark.django_db
@pytest.mark.views
class TestCreateOrderFromCart:
    """Тесты для создания заказа из корзины."""

    def test_checkout_cart_success(self, client, item_usd, item_eur):
        """Тест успешного создания заказа из корзины."""
        # Добавляем товары в корзину
        client.get(reverse("payments:add_to_cart", args=[item_usd.id]))
        client.get(reverse("payments:add_to_cart", args=[item_eur.id]))

        url = reverse("payments:checkout_cart")
        response = client.get(url)

        # Проверяем редирект на страницу заказа
        assert response.status_code == 302

        # Проверяем что заказ создан
        order = Order.objects.latest("created_at")
        assert order.items.count() == 2
        assert order.payment_currency == "usd"

    def test_checkout_cart_with_currency(self, client, item_usd):
        """Тест создания заказа с выбранной валютой."""
        # Устанавливаем валюту
        client.get(reverse("payments:change_currency", args=["eur"]))

        # Добавляем товар
        client.get(reverse("payments:add_to_cart", args=[item_usd.id]))

        # Создаем заказ
        url = reverse("payments:checkout_cart")
        client.get(url)

        order = Order.objects.latest("created_at")
        assert order.payment_currency == "eur"

    def test_checkout_cart_empty(self, client):
        """Тест создания заказа из пустой корзины."""
        url = reverse("payments:checkout_cart")
        response = client.get(url)

        # Должен редиректить на главную
        assert response.status_code == 302
        assert response.url == reverse("payments:index")

    def test_create_order_preserves_quantity(self, client, item_usd):
        """Тест что количество товаров сохраняется."""
        # Добавляем товар 3 раза
        for _ in range(3):
            client.get(reverse("payments:add_to_cart", args=[item_usd.id]))

        # Создаем заказ
        client.get(reverse("payments:checkout_cart"))

        order = Order.objects.latest("created_at")
        order_item = order.order_items.first()
        assert order_item.quantity == 3


@pytest.mark.django_db
@pytest.mark.views
class TestSuccessView:
    """Тесты для страницы успешной оплаты."""

    def test_success_view_status_code(self, client):
        """Тест доступности страницы успеха."""
        response = client.get(reverse("payments:success"))
        assert response.status_code == 200

    def test_success_view_clears_cart(self, client, item_usd):
        """Тест что корзина очищается после успешной оплаты."""
        # Добавляем товар и создаем заказ
        client.get(reverse("payments:add_to_cart", args=[item_usd.id]))
        response = client.get(reverse("payments:checkout_cart"))

        # Проверяем что pending_order_id установлен
        session = client.session
        assert "pending_order_id" in session
        assert "cart" in session

        # Переходим на страницу успеха
        response = client.get(reverse("payments:success"))

        assert response.status_code == 200
        session = client.session
        assert session.get("cart", {}) == {}
        assert "pending_order_id" not in session
