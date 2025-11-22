"""Тесты для template tags."""

import pytest

from payments.templatetags.payment_filters import cents_to_currency


@pytest.mark.unit
class TestCentsToCurrencyFilter:
    """Тесты для фильтра cents_to_currency."""

    def test_cents_to_currency_basic(self):
        """Тест конвертации центов в валюту."""
        assert cents_to_currency(5000) == "50.00"

    def test_cents_to_currency_zero(self):
        """Тест конвертации нуля."""
        assert cents_to_currency(0) == "0.00"

    def test_cents_to_currency_large_amount(self):
        """Тест конвертации большой суммы."""
        assert cents_to_currency(123456) == "1234.56"

    def test_cents_to_currency_small_amount(self):
        """Тест конвертации малой суммы."""
        assert cents_to_currency(99) == "0.99"

    def test_cents_to_currency_formatting(self):
        """Тест форматирования с двумя знаками после запятой."""
        assert cents_to_currency(1000) == "10.00"
        assert cents_to_currency(1050) == "10.50"
        assert cents_to_currency(1005) == "10.05"
