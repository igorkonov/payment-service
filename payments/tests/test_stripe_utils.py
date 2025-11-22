"""Тесты для Stripe утилит."""

import pytest

from payments.views import create_stripe_coupon


@pytest.mark.unit
class TestStripeUtils:
    """Тесты для Stripe утилит."""

    def test_create_stripe_coupon_success(self, mock_stripe_coupon):
        """Тест успешного создания купона."""
        coupon_id = create_stripe_coupon("TEST10", 10.0)

        assert coupon_id == "coupon_test_123"
        mock_stripe_coupon.assert_called_once()
        call_kwargs = mock_stripe_coupon.call_args[1]
        assert call_kwargs["name"] == "TEST10"
        assert call_kwargs["percent_off"] == 10.0
        assert call_kwargs["duration"] == "once"

    def test_create_stripe_coupon_with_exception(self, mocker):
        """Тест создания купона при ошибке (создается с уникальным именем)."""
        mock_coupon = mocker.patch("stripe.Coupon.create")

        # Первый вызов выбрасывает исключение
        # Второй вызов успешен
        mock_coupon.side_effect = [
            Exception("Coupon already exists"),
            mocker.Mock(id="coupon_unique_123"),
        ]

        coupon_id = create_stripe_coupon("EXISTING", 15.0)

        assert coupon_id == "coupon_unique_123"
        assert mock_coupon.call_count == 2

        # Проверяем что второй вызов с уникальным именем
        second_call_kwargs = mock_coupon.call_args_list[1][1]
        assert "EXISTING_" in second_call_kwargs["name"]
        assert second_call_kwargs["percent_off"] == 15.0
