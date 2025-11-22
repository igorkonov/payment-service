"""Тесты для утилит."""

import pytest

from payments.views import EUR_TO_USD_RATE, convert_to_base_currency


@pytest.mark.unit
class TestCurrencyConversion:
    """Тесты для конвертации валют."""

    def test_convert_usd_to_usd(self):
        """Тест конвертации USD в USD (без изменений)."""
        result = convert_to_base_currency(1000, "usd", "usd")
        assert result == 1000

    def test_convert_eur_to_eur(self):
        """Тест конвертации EUR в EUR (без изменений)."""
        result = convert_to_base_currency(1000, "eur", "eur")
        assert result == 1000

    def test_convert_eur_to_usd(self):
        """Тест конвертации EUR в USD."""
        result = convert_to_base_currency(1000, "eur", "usd")
        expected = int(1000 * EUR_TO_USD_RATE)
        assert result == expected

    def test_convert_usd_to_eur(self):
        """Тест конвертации USD в EUR."""
        result = convert_to_base_currency(1100, "usd", "eur")
        expected = int(1100 / EUR_TO_USD_RATE)
        assert result == expected

    def test_convert_zero_amount(self):
        """Тест конвертации нулевой суммы."""
        result = convert_to_base_currency(0, "eur", "usd")
        assert result == 0

    def test_convert_large_amount(self):
        """Тест конвертации большой суммы."""
        result = convert_to_base_currency(1000000, "eur", "usd")
        expected = int(1000000 * EUR_TO_USD_RATE)
        assert result == expected

    def test_eur_to_usd_rate_constant(self):
        """Тест что курс конвертации определен."""
        assert EUR_TO_USD_RATE == 1.1
