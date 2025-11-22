from typing import Any

import stripe
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from .models import Item, Order

stripe.api_key = settings.STRIPE_SECRET_KEY


def index(request: HttpRequest) -> HttpResponse:
    """Отображает главную страницу со списком товаров."""
    items = Item.objects.all()
    context: dict[str, Any] = {
        "items": items,
    }
    return render(request, "payments/index.html", context)


def order_detail(request: HttpRequest, id: int) -> HttpResponse:
    """Отображает страницу заказа с Payment Intent формой."""
    order = get_object_or_404(Order, pk=id)
    context: dict[str, Any] = {
        "order": order,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, "payments/order_detail.html", context)


@csrf_exempt
def create_order_checkout_session(
    request: HttpRequest,
    id: int,  # noqa: ARG001
) -> JsonResponse:
    """Создает Stripe Payment Intent для покупки заказа."""
    order = get_object_or_404(Order, pk=id)

    try:
        # Получаем детальный breakdown из модели
        subtotal = order.get_subtotal()
        discount_amount = order.get_discount_amount()
        tax_amount = order.get_tax_amount()
        total_amount = order.get_total_price()
        currency = order.get_currency()

        # Детальный metadata для Stripe Dashboard
        metadata: dict[str, Any] = {
            "order_id": order.id,
            "items_count": order.items.count(),
            "subtotal": subtotal,
            "discount_percent": (
                float(order.discount.percent) if order.discount else 0
            ),
            "discount_amount": discount_amount,
            "tax_percent": float(order.tax.percent) if order.tax else 0,
            "tax_amount": tax_amount,
            "total": total_amount,
            "currency": currency,
        }

        payment_intent_params: dict[str, Any] = {
            "amount": total_amount,
            "currency": currency,
            "metadata": metadata,
            "automatic_payment_methods": {"enabled": True},
        }

        # Детальное описание
        description_parts = [f"Заказ #{order.id}"]
        if order.discount:
            discount_text = (
                f"Скидка: {order.discount.percent}% (-{order.get_display_discount()})"
            )
            description_parts.append(discount_text)
        if order.tax:
            tax_text = f"Налог: {order.tax.percent}% (+{order.get_display_tax()})"
            description_parts.append(tax_text)
        payment_intent_params["description"] = " | ".join(description_parts)

        payment_intent = stripe.PaymentIntent.create(**payment_intent_params)
        return JsonResponse({"clientSecret": payment_intent.client_secret})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def create_stripe_coupon(name: str, percent: float) -> str:
    """Создает купон в Stripe и возвращает его ID."""
    try:
        coupon = stripe.Coupon.create(
            name=name,
            percent_off=float(percent),
            duration="once",
        )
        return coupon.id
    except Exception:
        # Если купон уже существует, создаем с уникальным именем
        import time

        coupon = stripe.Coupon.create(
            name=f"{name}_{int(time.time())}",
            percent_off=float(percent),
            duration="once",
        )
        return coupon.id


def success(request: HttpRequest) -> HttpResponse:
    """Отображает страницу успешной оплаты."""
    # Очищаем корзину после успешной оплаты
    if "pending_order_id" in request.session:
        request.session["cart"] = {}
        del request.session["pending_order_id"]

    return render(request, "payments/success.html")


# Cart Views

# Фиксированный курс конвертации (EUR к USD)
EUR_TO_USD_RATE = 1.1


def convert_to_base_currency(price: int, currency: str, base_currency: str) -> int:
    """Конвертирует цену в базовую валюту."""
    if currency == base_currency:
        return price

    if base_currency == "usd" and currency == "eur":
        return int(price * EUR_TO_USD_RATE)
    elif base_currency == "eur" and currency == "usd":
        return int(price / EUR_TO_USD_RATE)

    return price


def add_to_cart(request: HttpRequest, id: int) -> HttpResponse:
    """Добавляет товар в корзину."""
    get_object_or_404(Item, pk=id)  # Проверяем существование товара

    cart = request.session.get("cart", {})
    item_id = str(id)

    if item_id in cart:
        cart[item_id]["quantity"] += 1
    else:
        cart[item_id] = {"quantity": 1}

    request.session["cart"] = cart
    return redirect("payments:index")


def view_cart(request: HttpRequest) -> HttpResponse:
    """Отображает содержимое корзины."""
    cart = request.session.get("cart", {})
    cart_items = []
    total = 0

    # Получаем выбранную валюту из сессии
    selected_currency = request.session.get("payment_currency")

    # Определяем базовую валюту (первый товар)
    base_currency = None
    for item_id in cart:
        item = Item.objects.get(pk=int(item_id))
        base_currency = item.currency
        break

    # Используем выбранную валюту или базовую
    display_currency = selected_currency if selected_currency else base_currency

    for item_id, data in cart.items():
        item = Item.objects.get(pk=int(item_id))
        quantity = data["quantity"]

        # Конвертируем цену в выбранную валюту
        converted_price = convert_to_base_currency(
            item.price, item.currency, display_currency or "usd"
        )
        subtotal = converted_price * quantity

        cart_items.append(
            {
                "item": item,
                "quantity": quantity,
                "subtotal": subtotal,
                "original_currency": item.currency,
                "converted": item.currency != display_currency,
            }
        )
        total += subtotal

    context: dict[str, Any] = {
        "cart_items": cart_items,
        "total": total,
        "currency": display_currency or "usd",
        "cart_count": sum(data["quantity"] for data in cart.values()),
    }
    return render(request, "payments/cart.html", context)


def change_currency(request: HttpRequest, currency: str) -> HttpResponse:
    """Меняет валюту оплаты."""
    if currency in ["usd", "eur"]:
        request.session["payment_currency"] = currency
    return redirect("payments:view_cart")


def remove_from_cart(request: HttpRequest, id: int) -> HttpResponse:
    """Удаляет товар из корзины."""
    cart = request.session.get("cart", {})
    item_id = str(id)

    if item_id in cart:
        del cart[item_id]

    request.session["cart"] = cart
    return redirect("payments:view_cart")


def buy_now(request: HttpRequest, id: int) -> HttpResponse:
    """Добавляет товар в корзину и сразу переходит к оформлению."""
    get_object_or_404(Item, pk=id)

    # Очищаем корзину и добавляем только этот товар
    request.session["cart"] = {str(id): {"quantity": 1}}

    return redirect("payments:view_cart")


def update_cart_quantity(request: HttpRequest, id: int, action: str) -> HttpResponse:
    """Изменяет количество товара в корзине."""
    cart = request.session.get("cart", {})
    item_id = str(id)

    if item_id in cart:
        if action == "increase":
            cart[item_id]["quantity"] += 1
        elif action == "decrease":
            cart[item_id]["quantity"] -= 1
            if cart[item_id]["quantity"] <= 0:
                del cart[item_id]

    request.session["cart"] = cart
    return redirect("payments:view_cart")


def create_order_from_cart(request: HttpRequest) -> HttpResponse:
    """Создает заказ из корзины и редиректит на оплату."""
    cart = request.session.get("cart", {})

    if not cart:
        return redirect("payments:index")

    # Получаем выбранную валюту оплаты
    payment_currency = request.session.get("payment_currency", "usd")

    # Создаем заказ с выбранной валютой
    order = Order.objects.create(payment_currency=payment_currency)

    # Добавляем товары с учетом количества через OrderItem
    from payments.models import OrderItem

    for item_id, data in cart.items():
        item = Item.objects.get(pk=int(item_id))
        quantity = data["quantity"]

        OrderItem.objects.create(order=order, item=item, quantity=quantity)

    # Сохраняем ID заказа в сессии для очистки корзины после оплаты
    request.session["pending_order_id"] = order.id

    return redirect("payments:order_detail", id=order.id)
