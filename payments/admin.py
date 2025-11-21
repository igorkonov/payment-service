from django.contrib import admin

from .models import Discount, Item, Order, Tax


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """Админ-панель для управления товарами."""

    list_display = ("name", "price_display", "currency", "description")
    search_fields = ("name", "description")
    list_filter = ("currency", "price")

    def price_display(self, obj: Item) -> str:
        """Отображает цену с валютой."""
        return obj.get_display_price()

    price_display.short_description = "Цена"


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    """Админ-панель для управления скидками."""

    list_display = ("name", "percent")
    search_fields = ("name",)


@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    """Админ-панель для управления налогами."""

    list_display = ("name", "percent")
    search_fields = ("name",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Админ-панель для управления заказами."""

    list_display = ("id", "created_at", "get_items_count", "total_price_display", "discount", "tax")
    list_filter = ("created_at", "discount", "tax")
    filter_horizontal = ("items",)
    readonly_fields = ("created_at",)

    def get_items_count(self, obj: Order) -> int:
        """Возвращает количество товаров в заказе."""
        return obj.items.count()

    get_items_count.short_description = "Товаров"

    def total_price_display(self, obj: Order) -> str:
        """Отображает общую стоимость заказа."""
        total = obj.get_total_price()
        currency = obj.get_currency()
        symbol = "$" if currency == "usd" else "€"
        return f"{symbol}{total / 100:.2f}"

    total_price_display.short_description = "Итого"
