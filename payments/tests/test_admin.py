"""Тесты для Django Admin."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestItemAdmin:
    """Тесты для админки Item."""

    def test_item_admin_list_view(self, admin_client, item_usd, item_eur):
        """Тест списка товаров в админке."""
        url = reverse("admin:payments_item_changelist")
        response = admin_client.get(url)

        assert response.status_code == 200
        assert item_usd.name in str(response.content)
        assert item_eur.name in str(response.content)

    def test_item_admin_add_view(self, admin_client):
        """Тест страницы добавления товара."""
        url = reverse("admin:payments_item_add")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_item_admin_change_view(self, admin_client, item_usd):
        """Тест страницы редактирования товара."""
        url = reverse("admin:payments_item_change", args=[item_usd.id])
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestOrderAdmin:
    """Тесты для админки Order."""

    def test_order_admin_list_view(self, admin_client, order_with_items):
        """Тест списка заказов в админке."""
        url = reverse("admin:payments_order_changelist")
        response = admin_client.get(url)

        assert response.status_code == 200
        # Проверяем что страница содержит заказы
        assert "order" in str(response.content).lower()

    def test_order_admin_change_view(self, admin_client, order_with_items):
        """Тест страницы редактирования заказа."""
        url = reverse("admin:payments_order_change", args=[order_with_items.id])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_order_admin_inline_items(self, admin_client, order_with_items):
        """Тест что OrderItem отображаются inline."""
        url = reverse("admin:payments_order_change", args=[order_with_items.id])
        response = admin_client.get(url)

        # Проверяем что inline формы присутствуют
        assert b"order_items" in response.content


@pytest.mark.django_db
class TestDiscountAdmin:
    """Тесты для админки Discount."""

    def test_discount_admin_list_view(self, admin_client, discount_10):
        """Тест списка скидок в админке."""
        url = reverse("admin:payments_discount_changelist")
        response = admin_client.get(url)

        assert response.status_code == 200
        assert "10.00" in str(response.content)


@pytest.mark.django_db
class TestTaxAdmin:
    """Тесты для админки Tax."""

    def test_tax_admin_list_view(self, admin_client, tax_20):
        """Тест списка налогов в админке."""
        url = reverse("admin:payments_tax_changelist")
        response = admin_client.get(url)

        assert response.status_code == 200
        assert "20.00" in str(response.content)
