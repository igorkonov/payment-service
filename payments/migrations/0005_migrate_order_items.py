# Generated manually - миграция данных

from django.db import migrations


def migrate_order_items(apps, schema_editor):
    """Переносим товары из Order.items в OrderItem."""
    Order = apps.get_model('payments', 'Order')
    OrderItem = apps.get_model('payments', 'OrderItem')

    for order in Order.objects.all():
        # Группируем товары по ID и считаем количество
        items_count = {}
        for item in order.items.all():
            if item.id in items_count:
                items_count[item.id]['quantity'] += 1
            else:
                items_count[item.id] = {'item': item, 'quantity': 1}

        # Создаем OrderItem для каждого уникального товара
        for item_data in items_count.values():
            OrderItem.objects.create(
                order=order,
                item=item_data['item'],
                quantity=item_data['quantity']
            )


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0004_orderitem'),
    ]

    operations = [
        migrations.RunPython(migrate_order_items, migrations.RunPython.noop),
    ]
