from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("", views.index, name="index"),
    path("order/<int:id>/", views.order_detail, name="order_detail"),
    path(
        "buy-order/<int:id>/",
        views.create_order_checkout_session,
        name="create_order_checkout_session",
    ),
    path("cart/", views.view_cart, name="view_cart"),
    path("cart/add/<int:id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:id>/", views.remove_from_cart, name="remove_from_cart"),
    path(
        "cart/update/<int:id>/<str:action>/",
        views.update_cart_quantity,
        name="update_cart_quantity",
    ),
    path("buy-now/<int:id>/", views.buy_now, name="buy_now"),
    path(
        "cart/currency/<str:currency>/",
        views.change_currency,
        name="change_currency",
    ),
    path("cart/checkout/", views.create_order_from_cart, name="checkout_cart"),
    path("success/", views.success, name="success"),
]
