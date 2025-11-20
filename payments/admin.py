from django.contrib import admin

from .models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """Админ-панель для управления товарами."""

    list_display = ("name", "price_display", "description")
    search_fields = ("name", "description")
    list_filter = ("price",)

    def price_display(self, obj: Item) -> str:
        """Отображает цену в долларах."""
        return f"${obj.price / 100:.2f}"

    price_display.short_description = "Цена"
