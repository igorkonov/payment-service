from django.db import models


class Item(models.Model):
    """Модель товара для продажи через Stripe."""

    name = models.CharField(max_length=255, help_text="Название товара")
    description = models.TextField(help_text="Описание товара")
    price = models.IntegerField(help_text="Цена в центах")

    def __str__(self) -> str:
        """Строковое представление товара."""
        return f"{self.name} - ${self.price / 100:.2f}"

    def get_display_price(self) -> str:
        """Возвращает цену в долларах для отображения."""
        return f"{self.price / 100:.2f}"

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["name"]
