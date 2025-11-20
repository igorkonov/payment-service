from typing import Any

import stripe
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from .models import Item

stripe.api_key = settings.STRIPE_SECRET_KEY


def item_detail(request: HttpRequest, id: int) -> HttpResponse:
    """Отображает страницу с деталями товара и кнопкой покупки."""
    item = get_object_or_404(Item, pk=id)
    context: dict[str, Any] = {
        "item": item,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, "payments/item_detail.html", context)


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
                        "currency": "usd",
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
            cancel_url=request.build_absolute_uri(f"/item/{id}/"),
        )
        return JsonResponse({"sessionId": checkout_session.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def success(request: HttpRequest) -> HttpResponse:
    """Отображает страницу успешной оплаты."""
    return render(request, "payments/success.html")
