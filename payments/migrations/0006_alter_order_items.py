# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0005_migrate_order_items"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="order",
            name="items",
        ),
        migrations.AddField(
            model_name="order",
            name="items",
            field=models.ManyToManyField(
                help_text="Товары в заказе",
                related_name="orders",
                through="payments.OrderItem",
                to="payments.item",
            ),
        ),
    ]
