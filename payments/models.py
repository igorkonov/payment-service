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

    percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Процент скидки (например, 10.00)"
    )

    def __str__(self) -> str:
        """Строковое представление скидки."""
        return f"Скидка {self.percent}%"

    class Meta:
        verbose_name = "Скидка"
        verbose_name_plural = "Скидки"
        ordering = ["percent"]


class Tax(models.Model):
    """Модель налога для применения к заказам."""

    percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Процент налога (например, 20.00)"
    )

    def __str__(self) -> str:
        """Строковое представление налога."""
        return f"Налог {self.percent}%"

    class Meta:
        verbose_name = "Налог"
        verbose_name_plural = "Налоги"
        ordering = ["percent"]


class OrderItem(models.Model):
    """Промежуточная модель для связи Order и Item с количеством."""

    order = models.ForeignKey(
        "Order",
        on_delete=models.CASCADE,
        related_name="order_items",
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Товар в заказе"
        verbose_name_plural = "Товары в заказе"


class Order(models.Model):
    """Модель заказа, объединяющего несколько товаров."""

    items = models.ManyToManyField(
        Item,
        through="OrderItem",
        related_name="orders",
        help_text="Товары в заказе",
    )
    payment_currency = models.CharField(
        max_length=3,
        choices=[("usd", "USD"), ("eur", "EUR")],
        default="usd",
        help_text="Валюта оплаты",
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
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Дата создания заказа"
    )

    def __str__(self) -> str:
        """Строковое представление заказа."""
        return f"Заказ #{self.id} от {self.created_at.strftime('%d.%m.%Y')}"

    def get_subtotal(self) -> int:
        """Возвращает сумму товаров без скидок и налогов."""
        from payments.views import convert_to_base_currency

        subtotal = 0
        for order_item in self.order_items.all():
            converted_price = convert_to_base_currency(
                order_item.item.price,
                order_item.item.currency,
                self.payment_currency
            )
            subtotal += converted_price * order_item.quantity
        return int(subtotal)

    def get_discount_amount(self) -> int:
        """Возвращает сумму скидки в центах."""
        if not self.discount:
            return 0
        subtotal = self.get_subtotal()
        return int(subtotal * (self.discount.percent / 100))

    def get_tax_amount(self) -> int:
        """Возвращает сумму налога в центах."""
        if not self.tax:
            return 0
        subtotal_after_discount = (
            self.get_subtotal() - self.get_discount_amount()
        )
        return int(subtotal_after_discount * (self.tax.percent / 100))

    def get_total_price(self) -> int:
        """Возвращает общую стоимость заказа в центах."""
        subtotal = self.get_subtotal()
        discount = self.get_discount_amount()
        tax = self.get_tax_amount()
        return subtotal - discount + tax

    def get_currency(self) -> str:
        """Возвращает валюту оплаты заказа."""
        return self.payment_currency

    def get_display_subtotal(self) -> str:
        """Возвращает сумму товаров с валютой для отображения."""
        subtotal = self.get_subtotal()
        currency = self.get_currency()
        symbol = "$" if currency == "usd" else "€"
        return f"{symbol}{subtotal / 100:.2f}"

    def get_display_discount(self) -> str:
        """Возвращает сумму скидки с валютой для отображения."""
        discount = self.get_discount_amount()
        currency = self.get_currency()
        symbol = "$" if currency == "usd" else "€"
        return f"{symbol}{discount / 100:.2f}"

    def get_display_tax(self) -> str:
        """Возвращает сумму налога с валютой для отображения."""
        tax = self.get_tax_amount()
        currency = self.get_currency()
        symbol = "$" if currency == "usd" else "€"
        return f"{symbol}{tax / 100:.2f}"

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
