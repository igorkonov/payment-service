from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from payments.models import Discount, Item, Order, OrderItem, Tax

User = get_user_model()


@pytest.fixture
def item_usd(db):  # noqa: ARG001
    """Создает тестовый товар в USD."""
    return Item.objects.create(
        name="Test Product USD",
        description="Test description",
        price=5000,  # $50.00
        currency="usd",
    )


@pytest.fixture
def item_eur(db):  # noqa: ARG001
    """Создает тестовый товар в EUR."""
    return Item.objects.create(
        name="Test Product EUR",
        description="Test description EUR",
        price=3000,  # €30.00
        currency="eur",
    )


@pytest.fixture
def discount_10(db):  # noqa: ARG001
    """Создает скидку 10%."""
    return Discount.objects.create(percent=Decimal("10.00"))


@pytest.fixture
def discount_20(db):  # noqa: ARG001
    """Создает скидку 20%."""
    return Discount.objects.create(percent=Decimal("20.00"))


@pytest.fixture
def tax_20(db):  # noqa: ARG001
    """Создает налог 20%."""
    return Tax.objects.create(percent=Decimal("20.00"))


@pytest.fixture
def tax_10(db):  # noqa: ARG001
    """Создает налог 10%."""
    return Tax.objects.create(percent=Decimal("10.00"))


@pytest.fixture
def order_empty(db):  # noqa: ARG001
    """Создает пустой заказ в USD."""
    return Order.objects.create(payment_currency="usd")


@pytest.fixture
def order_with_items(db, item_usd, item_eur):  # noqa: ARG001
    """Создает заказ с двумя товарами."""
    order = Order.objects.create(payment_currency="usd")
    OrderItem.objects.create(order=order, item=item_usd, quantity=2)
    OrderItem.objects.create(order=order, item=item_eur, quantity=1)
    return order


@pytest.fixture
def order_with_discount_tax(db, item_usd, discount_10, tax_20):  # noqa: ARG001
    """Создает заказ с товаром, скидкой и налогом."""
    order = Order.objects.create(
        payment_currency="usd", discount=discount_10, tax=tax_20
    )
    OrderItem.objects.create(order=order, item=item_usd, quantity=1)
    return order


@pytest.fixture
def admin_user(db):  # noqa: ARG001
    """Создает суперпользователя для тестов админки."""
    return User.objects.create_superuser(
        username="admin", email="admin@test.com", password="admin123"
    )


@pytest.fixture
def cart_session(client):
    """Создает сессию с корзиной."""
    session = client.session
    session["cart"] = {"1": {"quantity": 2}, "2": {"quantity": 1}}
    session.save()
    return session


@pytest.fixture
def mock_stripe_payment_intent(mocker):
    """Мокает Stripe PaymentIntent.create."""
    mock = mocker.patch("stripe.PaymentIntent.create")
    mock.return_value.client_secret = "pi_test_secret_123"
    mock.return_value.id = "pi_test_123"
    return mock


@pytest.fixture
def mock_stripe_coupon(mocker):
    """Мокает Stripe Coupon.create."""
    mock = mocker.patch("stripe.Coupon.create")
    mock.return_value.id = "coupon_test_123"
    return mock
