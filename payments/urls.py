from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    # Checkout Session URLs (старый подход)
    path("item/<int:id>/", views.item_detail, name="item_detail"),
    path(
        "buy/<int:id>/",
        views.create_checkout_session,
        name="create_checkout_session",
    ),
    path("order/<int:id>/", views.order_detail, name="order_detail"),
    path(
        "buy-order/<int:id>/",
        views.create_order_checkout_session,
        name="create_order_checkout_session",
    ),
    # Payment Intent URLs (новый подход)
    path(
        "item-pi/<int:id>/",
        views.item_payment_intent_view,
        name="item_payment_intent",
    ),
    path(
        "create-payment-intent/<int:id>/",
        views.create_payment_intent,
        name="create_payment_intent",
    ),
    path(
        "order-pi/<int:id>/",
        views.order_payment_intent_view,
        name="order_payment_intent",
    ),
    path(
        "create-order-payment-intent/<int:id>/",
        views.create_order_payment_intent,
        name="create_order_payment_intent",
    ),
    # Success page
    path("success/", views.success, name="success"),
]
