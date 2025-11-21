from django.db import models


class Item(models.Model):
    """Модель товара для продажи через Stripe."""

    CURRENCY_CHOICES = [
        ("usd", "USD"),
        ("eur", "EUR"),
    ]

    name = models.CharField(max_length=255, help_text="Название товара")
    description = models.TextField(help_text="Описание товара")
    price = models.IntegerField(help_text="Цена в центах")
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="usd",
        help_text="Валюта товара",
    )

    def __str__(self) -> str:
        """Строковое представление товара."""
        return f"{self.name} - {self.get_display_price()}"

    def get_display_price(self) -> str:
        """Возвращает цену с валютой для отображения."""
        symbol = "$" if self.currency == "usd" else "€"
        return f"{symbol}{self.price / 100:.2f}"

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["name"]


class Discount(models.Model):
    """Модель скидки для применения к заказам."""

    name = models.CharField(max_length=255, help_text="Название скидки")
    percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Процент скидки (например, 10.00)"
    )

    def __str__(self) -> str:
        """Строковое представление скидки."""
        return f"{self.name} - {self.percent}%"

    class Meta:
        verbose_name = "Скидка"
        verbose_name_plural = "Скидки"
        ordering = ["name"]


class Tax(models.Model):
    """Модель налога для применения к заказам."""

    name = models.CharField(max_length=255, help_text="Название налога")
    percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Процент налога (например, 20.00)"
    )

    def __str__(self) -> str:
        """Строковое представление налога."""
        return f"{self.name} - {self.percent}%"

    class Meta:
        verbose_name = "Налог"
        verbose_name_plural = "Налоги"
        ordering = ["name"]


class Order(models.Model):
    """Модель заказа, объединяющего несколько товаров."""

    items = models.ManyToManyField(
        Item,
        related_name="orders",
        help_text="Товары в заказе"
        )
    discount = models.ForeignKey(
        Discount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text="Скидка на заказ",
    )
    tax = models.ForeignKey(
        Tax,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text="Налог на заказ",
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Дата создания заказа")

    def __str__(self) -> str:
        """Строковое представление заказа."""
        return f"Заказ #{self.id} от {self.created_at.strftime('%d.%m.%Y')}"

    def get_total_price(self) -> int:
        """Возвращает общую стоимость заказа в центах с учетом скидок и налогов."""
        total = sum(item.price for item in self.items.all())

        if self.discount:
            discount_amount = total * (self.discount.percent / 100)
            total -= int(discount_amount)

        if self.tax:
            tax_amount = total * (self.tax.percent / 100)
            total += int(tax_amount)

        return int(total)

    def get_currency(self) -> str:
        """Возвращает валюту заказа (берется из первого товара)."""
        first_item = self.items.first()
        return first_item.currency if first_item else "usd"

    def get_display_total(self) -> str:
        """Возвращает общую стоимость с валютой для отображения."""
        total = self.get_total_price()
        currency = self.get_currency()
        symbol = "$" if currency == "usd" else "€"
        return f"{symbol}{total / 100:.2f}"

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]
