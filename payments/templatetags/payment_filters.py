"""Кастомные фильтры для шаблонов."""
from django import template

register = template.Library()


@register.filter
def cents_to_currency(value: int) -> str:
    """Конвертирует центы в валюту с двумя знаками после запятой."""
    return f"{value / 100:.2f}"
