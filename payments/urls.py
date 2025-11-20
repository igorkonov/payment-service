from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("item/<int:id>/", views.item_detail, name="item_detail"),
    path("buy/<int:id>/", views.create_checkout_session, name="create_checkout_session"),
    path("success/", views.success, name="success"),
]
