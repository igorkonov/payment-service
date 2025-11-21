from typing import Any

import stripe
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from .models import Item, Order

stripe.api_key = settings.STRIPE_SECRET_KEY


def index(request: HttpRequest) -> HttpResponse:
    """Отображает главную страницу со списком товаров и заказов."""
    items = Item.objects.all()
    orders = Order.objects.all()
    context: dict[str, Any] = {
        "items": items,
        "orders": orders,
    }
    return render(request, "payments/index.html", context)


def item_detail(request: HttpRequest, id: int) -> HttpResponse:
    """Отображает страницу с деталями товара и кнопкой покупки."""
    item = get_object_or_404(Item, pk=id)
    context: dict[str, Any] = {
        "item": item,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, "payments/item_detail.html", context)


def order_detail(request: HttpRequest, id: int) -> HttpResponse:
    """Отображает страницу с деталями заказа и кнопкой покупки."""
    order = get_object_or_404(Order, pk=id)
    context: dict[str, Any] = {
        "order": order,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, "payments/order_detail.html", context)


@csrf_exempt
def create_checkout_session(request: HttpRequest, id: int) -> JsonResponse:
    """Создает Stripe checkout сессию для покупки товара."""
    item = get_object_or_404(Item, pk=id)

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": item.currency,
                        "product_data": {
                            "name": item.name,
                            "description": item.description,
                        },
                        "unit_amount": item.price,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=request.build_absolute_uri("/success/"),
            cancel_url=request.build_absolute_uri(
                f"/item/{id}/"
            ),
        )
        return JsonResponse({"sessionId": checkout_session.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def create_order_checkout_session(
    request: HttpRequest, id: int
) -> JsonResponse:
    """Создает Stripe checkout сессию для покупки заказа."""
    order = get_object_or_404(Order, pk=id)

    try:
        line_items = []
        for item in order.items.all():
            line_items.append(
                {
                    "price_data": {
                        "currency": item.currency,
                        "product_data": {
                            "name": item.name,
                            "description": item.description,
                        },
                        "unit_amount": item.price,
                    },
                    "quantity": 1,
                }
            )

        session_params = {
            "payment_method_types": ["card"],
            "line_items": line_items,
            "mode": "payment",
            "success_url": request.build_absolute_uri("/success/"),
            "cancel_url": request.build_absolute_uri(f"/order/{id}/"),
        }

        # Добавляем скидку если есть
        if order.discount:
            coupon_id = create_stripe_coupon(
                order.discount.name, order.discount.percent
            )
            session_params["discounts"] = [{"coupon": coupon_id}]

        checkout_session = stripe.checkout.Session.create(**session_params)
        return JsonResponse({"sessionId": checkout_session.id})
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
    return render(request, "payments/success.html")


# Payment Intent Views


def item_payment_intent_view(request: HttpRequest, id: int) -> HttpResponse:
    """Отображает страницу товара с Payment Intent формой."""
    item = get_object_or_404(Item, pk=id)
    context: dict[str, Any] = {
        "item": item,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, "payments/item_payment_intent.html", context)


@csrf_exempt
def create_payment_intent(request: HttpRequest, id: int) -> JsonResponse:
    """Создает Stripe Payment Intent для покупки товара."""
    item = get_object_or_404(Item, pk=id)

    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=item.price,
            currency=item.currency,
            metadata={
                "item_id": item.id,
                "item_name": item.name,
            },
            automatic_payment_methods={"enabled": True},
        )
        return JsonResponse({"clientSecret": payment_intent.client_secret})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def order_payment_intent_view(request: HttpRequest, id: int) -> HttpResponse:
    """Отображает страницу заказа с Payment Intent формой."""
    order = get_object_or_404(Order, pk=id)
    context: dict[str, Any] = {
        "order": order,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, "payments/order_payment_intent.html", context)


@csrf_exempt
def create_order_payment_intent(
    request: HttpRequest, id: int
) -> JsonResponse:
    """Создает Stripe Payment Intent для покупки заказа."""
    order = get_object_or_404(Order, pk=id)

    try:
        # Базовая сумма заказа
        total_amount = order.get_total_price()
        currency = order.get_currency()

        # Создаем Payment Intent
        payment_intent_params: dict[str, Any] = {
            "amount": total_amount,
            "currency": currency,
            "metadata": {
                "order_id": order.id,
                "items_count": order.items.count(),
            },
            "automatic_payment_methods": {"enabled": True},
        }

        # Добавляем описание с информацией о скидках и налогах
        description_parts = [f"Заказ #{order.id}"]
        if order.discount:
            description_parts.append(
                f"Скидка: {order.discount.name} ({order.discount.percent}%)"
            )
        if order.tax:
            description_parts.append(
                f"Налог: {order.tax.name} ({order.tax.percent}%)"
            )
        payment_intent_params["description"] = " | ".join(description_parts)

        payment_intent = stripe.PaymentIntent.create(**payment_intent_params)
        return JsonResponse({"clientSecret": payment_intent.client_secret})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
